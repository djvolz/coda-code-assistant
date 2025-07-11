"""Metrics collection and reporting for Coda.

This module provides comprehensive metrics collection including:
- Session statistics and lifecycle events
- Provider performance metrics
- Token usage and cost tracking
- Error rates and patterns
"""

import json
import logging
from collections import defaultdict
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import ConfigManager
from .base import ObservabilityComponent
from .collections import MemoryAwareDeque
from .constants import ENV_PREFIX

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Metrics for a single session."""

    session_id: str
    created_at: datetime
    provider: str
    model: str
    mode: str
    message_count: int = 0
    total_tokens_used: int = 0
    total_response_time: float = 0.0
    errors: int = 0
    last_activity: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with ISO format dates."""
        data = asdict(self)
        data["created_at"] = self.created_at.isoformat()
        if self.last_activity:
            data["last_activity"] = self.last_activity.isoformat()
        return data


@dataclass
class ProviderMetrics:
    """Metrics for a provider."""

    provider_name: str
    total_requests: int = 0
    total_errors: int = 0
    total_response_time: float = 0.0
    total_tokens: int = 0
    models_used: set = None
    last_request: datetime | None = None

    def __post_init__(self):
        if self.models_used is None:
            self.models_used = set()

    @property
    def average_response_time(self) -> float:
        """Calculate average response time."""
        if self.total_requests == 0:
            return 0.0
        return self.total_response_time / self.total_requests

    @property
    def error_rate(self) -> float:
        """Calculate error rate as percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.total_errors / self.total_requests) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with computed metrics."""
        data = asdict(self)
        data["models_used"] = list(self.models_used)
        data["average_response_time"] = self.average_response_time
        data["error_rate"] = self.error_rate
        if self.last_request:
            data["last_request"] = self.last_request.isoformat()
        return data


class MetricsCollector(ObservabilityComponent):
    """Collects and manages metrics for Coda."""

    def __init__(
        self,
        export_directory: Path,
        config_manager: ConfigManager,
        storage_backend=None,
        scheduler=None,
    ):
        """Initialize the metrics collector.

        Args:
            export_directory: Directory to export metrics data
            config_manager: Configuration manager instance
            storage_backend: Optional storage backend
            scheduler: Optional shared scheduler
        """
        super().__init__(export_directory, config_manager, storage_backend, scheduler)
        self.metrics_file = self.export_directory / "metrics.json"

        # Metrics storage
        self.session_metrics: dict[str, SessionMetrics] = {}
        self.provider_metrics: dict[str, ProviderMetrics] = {}

        # Use memory-aware deque for error log
        max_memory_mb = config_manager.get_float(
            "observability.metrics.max_memory_mb",
            default=50.0,
            env_var=f"{ENV_PREFIX}METRICS_MAX_MEMORY_MB",
        )
        self.error_log = MemoryAwareDeque(
            maxlen=10000,  # Keep last 10k errors max
            max_memory_mb=max_memory_mb,
            eviction_callback=self._on_error_evicted,
        )

        self.daily_stats: dict[str, dict[str, Any]] = defaultdict(dict)

        # Load existing metrics if available
        self._load_metrics()

    def get_component_name(self) -> str:
        """Return the component name for logging."""
        return "MetricsCollector"

    def get_flush_interval(self) -> int:
        """Return the flush interval in seconds."""
        return self.config_manager.get_int(
            "observability.metrics.flush_interval",
            default=300,  # 5 minutes
            env_var=f"{ENV_PREFIX}METRICS_FLUSH_INTERVAL",
        )

    def record_session_event(self, event_type: str, metadata: dict[str, Any]):
        """Record a session-related event."""
        with self._lock:
            session_id = metadata.get("session_id")
            if not session_id:
                return

            now = datetime.now(UTC)

            if event_type == "session_created":
                self.session_metrics[session_id] = SessionMetrics(
                    session_id=session_id,
                    created_at=now,
                    provider=metadata.get("provider", "unknown"),
                    model=metadata.get("model", "unknown"),
                    mode=metadata.get("mode", "general"),
                )

            elif event_type == "message_sent":
                if session_id in self.session_metrics:
                    metrics = self.session_metrics[session_id]
                    metrics.message_count += 1
                    metrics.total_tokens_used += metadata.get("tokens_used", 0)
                    metrics.total_response_time += metadata.get("response_time", 0.0)
                    metrics.last_activity = now

            elif event_type == "session_error":
                if session_id in self.session_metrics:
                    self.session_metrics[session_id].errors += 1

            # Update daily stats
            date_key = now.strftime("%Y-%m-%d")
            if date_key not in self.daily_stats:
                self.daily_stats[date_key] = {
                    "sessions_created": 0,
                    "messages_sent": 0,
                    "errors": 0,
                    "total_tokens": 0,
                }

            if event_type == "session_created":
                self.daily_stats[date_key]["sessions_created"] += 1
            elif event_type == "message_sent":
                self.daily_stats[date_key]["messages_sent"] += 1
                self.daily_stats[date_key]["total_tokens"] += metadata.get("tokens_used", 0)
            elif event_type == "session_error":
                self.daily_stats[date_key]["errors"] += 1

    def record_provider_event(self, provider_name: str, event_type: str, metadata: dict[str, Any]):
        """Record a provider-related event."""
        with self._lock:
            if provider_name not in self.provider_metrics:
                self.provider_metrics[provider_name] = ProviderMetrics(provider_name=provider_name)

            metrics = self.provider_metrics[provider_name]
            now = datetime.now(UTC)

            if event_type == "request_started":
                metrics.total_requests += 1
                metrics.last_request = now
                if "model" in metadata:
                    metrics.models_used.add(metadata["model"])

            elif event_type == "request_completed":
                metrics.total_response_time += metadata.get("response_time", 0.0)
                metrics.total_tokens += metadata.get("tokens_used", 0)

            elif event_type == "request_error":
                metrics.total_errors += 1

    def record_error(self, error: Exception, context: dict[str, Any]):
        """Record an error with context."""
        with self._lock:
            error_data = {
                "timestamp": datetime.now(UTC).isoformat(),
                "error_type": type(error).__name__,
                "error_message": str(error),
                "context": context,
            }
            self.error_log.append(error_data)

    def get_session_summary(self) -> dict[str, Any]:
        """Get summary statistics for all sessions."""
        with self._lock:
            if not self.session_metrics:
                return {
                    "total_sessions": 0,
                    "total_messages": 0,
                    "total_tokens": 0,
                    "total_errors": 0,
                    "providers": {},
                    "modes": {},
                }

            total_sessions = len(self.session_metrics)
            total_messages = sum(m.message_count for m in self.session_metrics.values())
            total_tokens = sum(m.total_tokens_used for m in self.session_metrics.values())
            total_errors = sum(m.errors for m in self.session_metrics.values())

            # Provider breakdown
            provider_stats = defaultdict(int)
            for metrics in self.session_metrics.values():
                provider_stats[metrics.provider] += 1

            # Mode breakdown
            mode_stats = defaultdict(int)
            for metrics in self.session_metrics.values():
                mode_stats[metrics.mode] += 1

            return {
                "total_sessions": total_sessions,
                "total_messages": total_messages,
                "total_tokens": total_tokens,
                "total_errors": total_errors,
                "providers": dict(provider_stats),
                "modes": dict(mode_stats),
            }

    def get_provider_summary(self) -> dict[str, Any]:
        """Get summary statistics for all providers."""
        with self._lock:
            return {
                provider: metrics.to_dict() for provider, metrics in self.provider_metrics.items()
            }

    def get_daily_stats(self, days: int = 30) -> dict[str, Any]:
        """Get daily statistics for the last N days."""
        with self._lock:
            # Sort by date descending and take last N days
            sorted_dates = sorted(self.daily_stats.keys(), reverse=True)
            recent_dates = sorted_dates[:days]

            return {date: self.daily_stats[date] for date in recent_dates}

    def get_error_summary(self) -> dict[str, Any]:
        """Get error summary statistics."""
        with self._lock:
            if not self.error_log:
                return {"total_errors": 0, "error_types": {}, "recent_errors": []}

            # Count error types
            error_types = defaultdict(int)
            for error in self.error_log:
                error_types[error["error_type"]] += 1

            # Get recent errors (last 10)
            recent_errors = list(self.error_log)[-10:]

            return {
                "total_errors": len(self.error_log),
                "error_types": dict(error_types),
                "recent_errors": recent_errors,
            }

    def get_status(self) -> dict[str, Any]:
        """Get current status of the metrics collector."""
        with self._lock:
            return {
                "running": self._running,
                "flush_interval": self.get_flush_interval(),
                "metrics_file": str(self.metrics_file),
                "session_count": len(self.session_metrics),
                "provider_count": len(self.provider_metrics),
                "error_count": len(self.error_log),
                "daily_stats_days": len(self.daily_stats),
            }

    def _load_metrics(self):
        """Load existing metrics from file."""
        if not self.metrics_file.exists():
            return

        try:
            with open(self.metrics_file) as f:
                data = json.load(f)

            # Load session metrics
            if "sessions" in data:
                for session_data in data["sessions"]:
                    session_id = session_data["session_id"]
                    session_data["created_at"] = datetime.fromisoformat(session_data["created_at"])
                    if session_data.get("last_activity"):
                        session_data["last_activity"] = datetime.fromisoformat(
                            session_data["last_activity"]
                        )
                    self.session_metrics[session_id] = SessionMetrics(**session_data)

            # Load provider metrics
            if "providers" in data:
                for provider_data in data["providers"]:
                    provider_name = provider_data["provider_name"]
                    provider_data["models_used"] = set(provider_data.get("models_used", []))
                    if provider_data.get("last_request"):
                        provider_data["last_request"] = datetime.fromisoformat(
                            provider_data["last_request"]
                        )
                    # Remove computed fields
                    provider_data.pop("average_response_time", None)
                    provider_data.pop("error_rate", None)
                    self.provider_metrics[provider_name] = ProviderMetrics(**provider_data)

            # Load error log
            if "errors" in data:
                for error in data["errors"]:
                    self.error_log.append(error)

            # Load daily stats
            if "daily_stats" in data:
                self.daily_stats.update(data["daily_stats"])

        except Exception as e:
            # Log error but don't fail initialization
            print(f"Warning: Failed to load existing metrics: {e}")

    def _flush_data(self) -> None:
        """Flush metrics data to storage."""
        self._flush_metrics()

    def _flush_metrics(self):
        """Flush metrics to file."""
        try:
            data = {
                "sessions": [m.to_dict() for m in self.session_metrics.values()],
                "providers": [m.to_dict() for m in self.provider_metrics.values()],
                "errors": list(self.error_log),
                "daily_stats": dict(self.daily_stats),
                "last_updated": datetime.now(UTC).isoformat(),
            }

            # Write to temp file first, then atomic rename
            temp_file = self.metrics_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.metrics_file)

        except Exception as e:
            print(f"Warning: Failed to flush metrics: {e}")

    def _on_error_evicted(self, error_data: dict[str, Any]) -> None:
        """Handle evicted error data."""
        # Log that we're evicting old errors due to memory pressure
        logger.debug(f"Evicting old error from {error_data.get('timestamp', 'unknown')}")
