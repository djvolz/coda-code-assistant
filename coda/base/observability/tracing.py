"""Distributed tracing implementation for Coda.

This module provides OpenTelemetry-compatible tracing for request flows,
provider interactions, and session management operations.
"""

import json
import threading
import time
from collections import defaultdict
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import ConfigManager
from .base import ObservabilityComponent
from .collections import BoundedCache
from .constants import ENV_PREFIX


@dataclass
class Span:
    """A single trace span."""

    span_id: str
    trace_id: str
    parent_span_id: str | None
    operation_name: str
    start_time: datetime
    end_time: datetime | None = None
    tags: dict[str, Any] = None
    logs: list[dict[str, Any]] = None
    status: str = "ok"  # ok, error, timeout

    def __post_init__(self):
        if self.tags is None:
            self.tags = {}
        if self.logs is None:
            self.logs = []

    @property
    def duration_ms(self) -> float:
        """Calculate duration in milliseconds."""
        if not self.end_time:
            return 0.0
        delta = self.end_time - self.start_time
        return delta.total_seconds() * 1000

    def add_tag(self, key: str, value: Any):
        """Add a tag to the span."""
        self.tags[key] = value

    def add_log(self, message: str, level: str = "info", **kwargs):
        """Add a log entry to the span."""
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": level,
            "message": message,
            **kwargs,
        }
        self.logs.append(log_entry)

    def set_status(self, status: str, message: str | None = None):
        """Set the span status."""
        self.status = status
        if message:
            self.add_log(message, level="error" if status == "error" else "info")

    def finish(self):
        """Finish the span."""
        if not self.end_time:
            self.end_time = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["start_time"] = self.start_time.isoformat()
        if self.end_time:
            data["end_time"] = self.end_time.isoformat()
        data["duration_ms"] = self.duration_ms
        return data


class SpanContext:
    """Context manager for spans."""

    def __init__(self, span: Span, tracing_manager: "TracingManager"):
        self.span = span
        self.tracing_manager = tracing_manager

    def __enter__(self) -> Span:
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            self.span.set_status("error", f"{exc_type.__name__}: {exc_val}")
        self.span.finish()
        self.tracing_manager._finish_span(self.span)


class NoopSpan:
    """No-op span for when tracing is disabled."""

    def add_tag(self, key: str, value: Any):
        pass

    def add_log(self, message: str, level: str = "info", **kwargs):
        pass

    def set_status(self, status: str, message: str | None = None):
        pass

    def finish(self):
        pass


class NoopSpanContext:
    """No-op span context for when tracing is disabled."""

    def __enter__(self) -> NoopSpan:
        return NoopSpan()

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TracingManager(ObservabilityComponent):
    """Manages distributed tracing for Coda."""

    def __init__(
        self,
        export_directory: Path,
        config_manager: ConfigManager,
        storage_backend=None,
        scheduler=None,
    ):
        """Initialize the tracing manager.

        Args:
            export_directory: Directory to export trace data
            config_manager: Configuration manager instance
            storage_backend: Optional storage backend
            scheduler: Optional shared scheduler
        """
        super().__init__(export_directory, config_manager, storage_backend, scheduler)
        self.traces_file = self.export_directory / "traces.json"

        # Tracing storage
        self.active_spans: dict[str, Span] = {}

        # Use bounded cache for completed traces
        max_memory_mb = config_manager.get_float(
            "observability.tracing.max_memory_mb",
            default=100.0,
            env_var=f"{ENV_PREFIX}TRACING_MAX_MEMORY_MB",
        )
        self.completed_traces_cache = BoundedCache(
            max_size=1000,  # Max 1000 traces
            max_memory_mb=max_memory_mb,
            ttl_seconds=3600,  # Keep traces for 1 hour
        )
        self.completed_traces: dict[str, list[Span]] = {}

        # Configuration
        self.sample_rate = config_manager.get_float(
            "observability.tracing.sample_rate",
            default=1.0,  # Sample 100% by default
            env_var=f"{ENV_PREFIX}TRACING_SAMPLE_RATE",
        )

        self.max_spans_per_trace = config_manager.get_int(
            "observability.tracing.max_spans_per_trace",
            default=1000,
            env_var=f"{ENV_PREFIX}TRACING_MAX_SPANS",
        )

        # Span ID generation
        self._span_counter = 0

        # Load existing traces if available
        self._load_traces()

    def get_component_name(self) -> str:
        """Return the component name for logging."""
        return "TracingManager"

    def get_flush_interval(self) -> int:
        """Return the flush interval in seconds."""
        return self.config_manager.get_int(
            "observability.tracing.flush_interval",
            default=60,  # 1 minute
            env_var=f"{ENV_PREFIX}TRACING_FLUSH_INTERVAL",
        )

    def stop(self):
        """Stop the tracing manager and flush data."""
        # Finish all active spans before calling parent stop
        with self._lock:
            for span in list(self.active_spans.values()):
                span.finish()
                self._finish_span(span)

        # Call parent stop which handles flush
        super().stop()

    def _generate_span_id(self) -> str:
        """Generate a unique span ID."""
        with self._lock:
            self._span_counter += 1
            return f"span_{self._span_counter}_{int(time.time() * 1000)}"

    def _generate_trace_id(self) -> str:
        """Generate a unique trace ID."""
        return f"trace_{int(time.time() * 1000)}_{threading.get_ident()}"

    def create_span(
        self,
        operation_name: str,
        parent_span_id: str | None = None,
        trace_id: str | None = None,
        **tags,
    ) -> SpanContext:
        """Create a new span.

        Args:
            operation_name: Name of the operation being traced
            parent_span_id: ID of parent span (if any)
            trace_id: Trace ID (generates new if not provided)
            **tags: Additional tags to add to the span

        Returns:
            SpanContext for the new span
        """
        # Check sampling rate
        if self.sample_rate < 1.0:
            import random

            if random.random() > self.sample_rate:
                return self.create_noop_span()

        with self._lock:
            span_id = self._generate_span_id()

            if not trace_id:
                trace_id = self._generate_trace_id()

            span = Span(
                span_id=span_id,
                trace_id=trace_id,
                parent_span_id=parent_span_id,
                operation_name=operation_name,
                start_time=datetime.now(UTC),
                tags=tags,
            )

            self.active_spans[span_id] = span

            return SpanContext(span, self)

    def create_noop_span(self) -> NoopSpanContext:
        """Create a no-op span context."""
        return NoopSpanContext()

    def _finish_span(self, span: Span):
        """Finish a span and move it to completed traces."""
        with self._lock:
            # Remove from active spans
            self.active_spans.pop(span.span_id, None)

            # Add to completed traces
            if span.trace_id not in self.completed_traces:
                self.completed_traces[span.trace_id] = []

            self.completed_traces[span.trace_id].append(span)

            # Limit spans per trace
            if len(self.completed_traces[span.trace_id]) > self.max_spans_per_trace:
                # Remove oldest spans
                spans = self.completed_traces[span.trace_id]
                spans.sort(key=lambda s: s.start_time)
                self.completed_traces[span.trace_id] = spans[-self.max_spans_per_trace :]

    def get_trace_summary(self) -> dict[str, Any]:
        """Get summary of all traces."""
        with self._lock:
            total_traces = len(self.completed_traces)
            total_spans = sum(len(spans) for spans in self.completed_traces.values())
            active_spans = len(self.active_spans)

            # Calculate average trace duration
            avg_duration = 0.0
            if total_traces > 0:
                total_duration = 0.0
                trace_count = 0
                for spans in self.completed_traces.values():
                    if spans:
                        root_spans = [s for s in spans if not s.parent_span_id]
                        if root_spans:
                            root_span = min(root_spans, key=lambda s: s.start_time)
                            if root_span.end_time:
                                total_duration += root_span.duration_ms
                                trace_count += 1
                if trace_count > 0:
                    avg_duration = total_duration / trace_count

            # Operation breakdown
            operation_stats = defaultdict(int)
            for spans in self.completed_traces.values():
                for span in spans:
                    operation_stats[span.operation_name] += 1

            return {
                "total_traces": total_traces,
                "total_spans": total_spans,
                "active_spans": active_spans,
                "average_duration_ms": avg_duration,
                "operations": dict(operation_stats),
            }

    def get_recent_traces(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent traces with their spans."""
        with self._lock:
            # Sort traces by most recent activity
            sorted_traces = []
            for trace_id, spans in self.completed_traces.items():
                if spans:
                    latest_time = max(s.start_time for s in spans)
                    sorted_traces.append((trace_id, spans, latest_time))

            sorted_traces.sort(key=lambda x: x[2], reverse=True)

            # Return top N traces
            result = []
            for trace_id, spans, _ in sorted_traces[:limit]:
                trace_data = {
                    "trace_id": trace_id,
                    "span_count": len(spans),
                    "spans": [span.to_dict() for span in spans],
                }

                # Calculate trace duration
                if spans:
                    start_time = min(s.start_time for s in spans)
                    end_time = max(s.end_time for s in spans if s.end_time)
                    if end_time:
                        duration = (end_time - start_time).total_seconds() * 1000
                        trace_data["duration_ms"] = duration

                result.append(trace_data)

            return result

    def get_status(self) -> dict[str, Any]:
        """Get current status of the tracing manager."""
        with self._lock:
            return {
                "running": self._running,
                "sample_rate": self.sample_rate,
                "flush_interval": self.get_flush_interval(),
                "traces_file": str(self.traces_file),
                "active_spans": len(self.active_spans),
                "completed_traces": len(self.completed_traces),
                "max_spans_per_trace": self.max_spans_per_trace,
            }

    def _load_traces(self):
        """Load existing traces from file."""
        if not self.traces_file.exists():
            return

        try:
            with open(self.traces_file) as f:
                data = json.load(f)

            if "traces" in data:
                for trace_data in data["traces"]:
                    trace_id = trace_data["trace_id"]
                    spans = []

                    for span_data in trace_data["spans"]:
                        span_data["start_time"] = datetime.fromisoformat(span_data["start_time"])
                        if span_data.get("end_time"):
                            span_data["end_time"] = datetime.fromisoformat(span_data["end_time"])
                        # Remove computed fields
                        span_data.pop("duration_ms", None)
                        spans.append(Span(**span_data))

                    self.completed_traces[trace_id] = spans

        except Exception as e:
            # Log error but don't fail initialization
            print(f"Warning: Failed to load existing traces: {e}")

    def _flush_data(self) -> None:
        """Flush trace data to storage."""
        self._flush_traces()

    def _flush_traces(self):
        """Flush traces to file."""
        try:
            # Only flush completed traces (not active spans)
            traces_data = []
            for trace_id, spans in self.completed_traces.items():
                if spans:
                    trace_data = {"trace_id": trace_id, "spans": [span.to_dict() for span in spans]}
                    traces_data.append(trace_data)

            data = {"traces": traces_data, "last_updated": datetime.now(UTC).isoformat()}

            # Write to temp file first, then atomic rename
            temp_file = self.traces_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.traces_file)

        except Exception as e:
            print(f"Warning: Failed to flush traces: {e}")

    @contextmanager
    def trace(self, operation_name: str, **tags):
        """Context manager for tracing an operation."""
        with self.create_span(operation_name, **tags) as span:
            yield span
