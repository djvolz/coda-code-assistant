"""Performance profiling utilities for Coda debug mode.

This module provides lightweight performance profiling tools for
debugging performance issues and bottlenecks in the application.
"""

import functools
import json
import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import ConfigManager
from .base import ObservabilityComponent
from .constants import ENV_PREFIX


@dataclass
class ProfileEntry:
    """Represents a single profiling measurement."""

    function_name: str
    module_name: str
    start_time: datetime
    end_time: datetime
    duration_ms: float
    args_hash: str
    memory_usage: int | None = None
    thread_id: int = 0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "function_name": self.function_name,
            "module_name": self.module_name,
            "start_time": self.start_time.isoformat(),
            "end_time": self.end_time.isoformat(),
            "duration_ms": self.duration_ms,
            "args_hash": self.args_hash,
            "memory_usage": self.memory_usage,
            "thread_id": self.thread_id,
        }


@dataclass
class FunctionStats:
    """Statistics for a specific function."""

    function_name: str
    call_count: int = 0
    total_time_ms: float = 0.0
    min_time_ms: float = float("inf")
    max_time_ms: float = 0.0
    avg_time_ms: float = 0.0

    def update(self, duration_ms: float):
        """Update statistics with a new measurement."""
        self.call_count += 1
        self.total_time_ms += duration_ms
        self.min_time_ms = min(self.min_time_ms, duration_ms)
        self.max_time_ms = max(self.max_time_ms, duration_ms)
        self.avg_time_ms = self.total_time_ms / self.call_count

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return asdict(self)


class PerformanceProfiler(ObservabilityComponent):
    """Lightweight performance profiler for debug mode."""

    def __init__(
        self,
        export_directory: Path,
        config_manager: ConfigManager,
        storage_backend=None,
        scheduler=None,
    ):
        """Initialize the performance profiler.

        Args:
            export_directory: Directory to export profiling data
            config_manager: Configuration manager instance
            storage_backend: Optional storage backend
            scheduler: Optional shared scheduler
        """
        super().__init__(export_directory, config_manager, storage_backend, scheduler)
        self.profile_file = self.export_directory / "performance_profiles.json"

        # Profiling storage
        self.profile_entries: deque = deque(maxlen=10000)  # Keep last 10k entries
        self.function_stats: dict[str, FunctionStats] = {}

        # Configuration
        self.enabled = config_manager.get_bool(
            "observability.profiling.enabled",
            default=False,  # Disabled by default
            env_var=f"{ENV_PREFIX}PROFILING_ENABLED",
        )

        self.debug_mode_only = config_manager.get_bool(
            "observability.profiling.debug_mode_only",
            default=True,
            env_var=f"{ENV_PREFIX}PROFILING_DEBUG_MODE_ONLY",
        )

        self.min_duration_ms = config_manager.get_float(
            "observability.profiling.min_duration_ms",
            default=1.0,  # Only profile functions taking >= 1ms
            env_var=f"{ENV_PREFIX}PROFILING_MIN_DURATION_MS",
        )

        self.track_memory = config_manager.get_bool(
            "observability.profiling.track_memory",
            default=False,  # Memory tracking can be expensive
            env_var=f"{ENV_PREFIX}PROFILING_TRACK_MEMORY",
        )

        # Memory tracking
        self._memory_tracker = None
        if self.track_memory:
            try:
                import psutil

                self._memory_tracker = psutil.Process()
            except ImportError:
                self.track_memory = False

        # Load existing data
        self._load_profile_data()

    def get_component_name(self) -> str:
        """Return the component name for logging."""
        return "PerformanceProfiler"

    def get_flush_interval(self) -> int:
        """Return the flush interval in seconds."""
        return self.config_manager.get_int(
            "observability.profiling.flush_interval",
            default=600,  # 10 minutes
            env_var=f"{ENV_PREFIX}PROFILING_FLUSH_INTERVAL",
        )

    def start(self):
        """Start the profiler."""
        if not self.enabled:
            return

        super().start()

    def is_profiling_enabled(self, debug_mode: bool = False) -> bool:
        """Check if profiling should be enabled.

        Args:
            debug_mode: Whether debug mode is currently active

        Returns:
            True if profiling should be enabled
        """
        if not self.enabled:
            return False

        if self.debug_mode_only and not debug_mode:
            return False

        return True

    def _get_memory_usage(self) -> int | None:
        """Get current memory usage in bytes."""
        if not self.track_memory or not self._memory_tracker:
            return None

        try:
            return self._memory_tracker.memory_info().rss
        except Exception:
            return None

    def record_function_call(
        self, function_name: str, module_name: str, duration_ms: float, args_hash: str = ""
    ):
        """Record a function call for profiling.

        Args:
            function_name: Name of the function
            module_name: Module containing the function
            duration_ms: Duration in milliseconds
            args_hash: Hash of function arguments (optional)
        """
        if not self.enabled or duration_ms < self.min_duration_ms:
            return

        with self._lock:
            now = datetime.now(UTC)
            start_time = now.replace(microsecond=now.microsecond - int(duration_ms * 1000))

            # Create profile entry
            entry = ProfileEntry(
                function_name=function_name,
                module_name=module_name,
                start_time=start_time,
                end_time=now,
                duration_ms=duration_ms,
                args_hash=args_hash,
                memory_usage=self._get_memory_usage(),
                thread_id=threading.get_ident(),
            )

            self.profile_entries.append(entry)

            # Update function statistics
            full_name = f"{module_name}.{function_name}"
            if full_name not in self.function_stats:
                self.function_stats[full_name] = FunctionStats(function_name=full_name)

            self.function_stats[full_name].update(duration_ms)

    def get_function_stats(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get function statistics sorted by total time.

        Args:
            limit: Maximum number of functions to return

        Returns:
            List of function statistics
        """
        with self._lock:
            # Sort by total time descending
            sorted_stats = sorted(
                self.function_stats.values(), key=lambda x: x.total_time_ms, reverse=True
            )

            return [stats.to_dict() for stats in sorted_stats[:limit]]

    def get_slow_functions(self, min_avg_time_ms: float = 10.0) -> list[dict[str, Any]]:
        """Get functions with high average execution times.

        Args:
            min_avg_time_ms: Minimum average time to include

        Returns:
            List of slow functions
        """
        with self._lock:
            slow_functions = [
                stats.to_dict()
                for stats in self.function_stats.values()
                if stats.avg_time_ms >= min_avg_time_ms
            ]

            # Sort by average time descending
            return sorted(slow_functions, key=lambda x: x["avg_time_ms"], reverse=True)

    def get_recent_calls(self, limit: int = 100) -> list[dict[str, Any]]:
        """Get recent function calls.

        Args:
            limit: Maximum number of calls to return

        Returns:
            List of recent function calls
        """
        with self._lock:
            recent = list(self.profile_entries)[-limit:]
            return [entry.to_dict() for entry in reversed(recent)]

    def get_hotspots(self, time_window_minutes: int = 10) -> list[dict[str, Any]]:
        """Get performance hotspots in a recent time window.

        Args:
            time_window_minutes: Time window in minutes

        Returns:
            List of performance hotspots
        """
        with self._lock:
            from datetime import timedelta

            now = datetime.now(UTC)
            cutoff_time = now - timedelta(minutes=time_window_minutes)

            # Filter recent entries
            recent_entries = [
                entry for entry in self.profile_entries if entry.start_time >= cutoff_time
            ]

            # Aggregate by function
            hotspots = defaultdict(lambda: {"count": 0, "total_time": 0.0})

            for entry in recent_entries:
                key = f"{entry.module_name}.{entry.function_name}"
                hotspots[key]["count"] += 1
                hotspots[key]["total_time"] += entry.duration_ms

            # Convert to list and sort by total time
            hotspot_list = []
            for func_name, data in hotspots.items():
                hotspot_list.append(
                    {
                        "function": func_name,
                        "call_count": data["count"],
                        "total_time_ms": data["total_time"],
                        "avg_time_ms": data["total_time"] / data["count"],
                    }
                )

            return sorted(hotspot_list, key=lambda x: x["total_time_ms"], reverse=True)

    def get_summary(self) -> dict[str, Any]:
        """Get profiling summary statistics."""
        with self._lock:
            if not self.profile_entries:
                return {
                    "enabled": self.enabled,
                    "total_calls": 0,
                    "unique_functions": 0,
                    "total_time_ms": 0.0,
                    "avg_call_time_ms": 0.0,
                }

            total_calls = len(self.profile_entries)
            unique_functions = len(self.function_stats)
            total_time = sum(entry.duration_ms for entry in self.profile_entries)
            avg_time = total_time / total_calls if total_calls > 0 else 0.0

            return {
                "enabled": self.enabled,
                "total_calls": total_calls,
                "unique_functions": unique_functions,
                "total_time_ms": total_time,
                "avg_call_time_ms": avg_time,
                "min_duration_threshold_ms": self.min_duration_ms,
                "memory_tracking": self.track_memory,
            }

    def get_status(self) -> dict[str, Any]:
        """Get current profiler status."""
        with self._lock:
            return {
                "enabled": self.enabled,
                "running": self._running,
                "debug_mode_only": self.debug_mode_only,
                "min_duration_ms": self.min_duration_ms,
                "track_memory": self.track_memory,
                "flush_interval": self.get_flush_interval(),
                "profile_file": str(self.profile_file),
                "total_entries": len(self.profile_entries),
                "function_count": len(self.function_stats),
            }

    def clear_data(self):
        """Clear all profiling data."""
        with self._lock:
            self.profile_entries.clear()
            self.function_stats.clear()

    def _load_profile_data(self):
        """Load existing profiling data from file."""
        if not self.profile_file.exists():
            return

        try:
            with open(self.profile_file) as f:
                data = json.load(f)

            # Load function stats
            if "function_stats" in data:
                for stats_data in data["function_stats"]:
                    stats = FunctionStats(**stats_data)
                    self.function_stats[stats.function_name] = stats

        except Exception as e:
            print(f"Warning: Failed to load profiling data: {e}")

    def _flush_data(self):
        """Flush profiling data to file."""
        try:
            data = {
                "function_stats": [stats.to_dict() for stats in self.function_stats.values()],
                "summary": self.get_summary(),
                "last_updated": datetime.now(UTC).isoformat(),
            }

            # Write to temp file first, then atomic rename
            temp_file = self.profile_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(data, f, indent=2)

            temp_file.replace(self.profile_file)

        except Exception as e:
            print(f"Warning: Failed to flush profiling data: {e}")


def profile(profiler: PerformanceProfiler | None = None, debug_mode: bool = False):
    """Decorator to profile function execution times.

    Args:
        profiler: Performance profiler instance (optional)
        debug_mode: Whether debug mode is active
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not profiler or not profiler.is_profiling_enabled(debug_mode):
                return func(*args, **kwargs)

            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration_ms = (time.time() - start_time) * 1000

                # Create a simple hash of arguments for grouping
                args_hash = str(hash(str(args)[:100] + str(kwargs)[:100]))[-8:]

                profiler.record_function_call(
                    function_name=func.__name__,
                    module_name=func.__module__ or "unknown",
                    duration_ms=duration_ms,
                    args_hash=args_hash,
                )

        return wrapper

    return decorator
