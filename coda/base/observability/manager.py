"""Central observability manager for Coda.

This module provides a unified interface for all observability features,
including metrics collection, tracing, health monitoring, and error tracking.
"""

import logging
from pathlib import Path
from typing import Any

from ..config import ConfigManager
from .constants import ENV_PREFIX
from .error_tracker import ErrorCategory, ErrorSeverity, ErrorTracker
from .health import HealthMonitor
from .metrics import MetricsCollector
from .profiler import PerformanceProfiler
from .scheduler import PeriodicTaskScheduler
from .tracing import TracingManager


class ObservabilityManager:
    """Central manager for all observability features."""

    def __init__(self, config_manager: ConfigManager):
        """Initialize the observability manager.

        Args:
            config_manager: Configuration manager instance
        """
        self.config_manager = config_manager
        self.enabled = self._is_enabled()
        self.export_directory = self._get_export_directory()

        # Initialize scheduler
        self.scheduler: PeriodicTaskScheduler | None = None

        # Initialize components
        self.metrics_collector: MetricsCollector | None = None
        self.tracing_manager: TracingManager | None = None
        self.health_monitor: HealthMonitor | None = None
        self.error_tracker: ErrorTracker | None = None
        self.profiler: PerformanceProfiler | None = None

        # Logger for observability events
        self.logger = logging.getLogger(__name__)

        if self.enabled:
            self._initialize_components()

    def _is_enabled(self) -> bool:
        """Check if observability is enabled via configuration."""
        # Check environment variable first
        import os

        env_value = os.environ.get(f"{ENV_PREFIX}OBSERVABILITY_ENABLED")
        if env_value is not None:
            return env_value.lower() in ("true", "1", "yes", "on")

        # Fall back to config file
        return self.config_manager.get_bool("observability.enabled", default=False)

    def _get_export_directory(self) -> Path:
        """Get the directory for exporting observability data."""
        # Check environment variable first
        import os

        env_value = os.environ.get(f"{ENV_PREFIX}OBSERVABILITY_EXPORT_DIR")
        if env_value:
            export_dir = Path(env_value)
        else:
            # Fall back to config file, then cache dir
            default_dir = self.config_manager.get_cache_dir() / "observability"
            export_dir = self.config_manager.get_string(
                "observability.export_directory", default=str(default_dir)
            )
        path = Path(export_dir)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _initialize_components(self):
        """Initialize observability components."""
        try:
            # Initialize shared scheduler
            self.scheduler = PeriodicTaskScheduler(max_workers=2)
            # Initialize metrics collector
            if self.config_manager.get_bool("observability.metrics.enabled", default=True):
                self.metrics_collector = MetricsCollector(
                    export_directory=self.export_directory,
                    config_manager=self.config_manager,
                    scheduler=self.scheduler,
                )

            # Initialize tracing manager
            if self.config_manager.get_bool("observability.tracing.enabled", default=True):
                self.tracing_manager = TracingManager(
                    export_directory=self.export_directory,
                    config_manager=self.config_manager,
                    scheduler=self.scheduler,
                )

            # Initialize health monitor
            if self.config_manager.get_bool("observability.health.enabled", default=True):
                self.health_monitor = HealthMonitor(
                    export_directory=self.export_directory,
                    config_manager=self.config_manager,
                    scheduler=self.scheduler,
                )

            # Initialize error tracker
            if self.config_manager.get_bool("observability.error_tracking.enabled", default=True):
                self.error_tracker = ErrorTracker(
                    export_directory=self.export_directory,
                    config_manager=self.config_manager,
                    scheduler=self.scheduler,
                )

            # Initialize performance profiler
            if self.config_manager.get_bool("observability.profiling.enabled", default=False):
                self.profiler = PerformanceProfiler(
                    export_directory=self.export_directory,
                    config_manager=self.config_manager,
                    scheduler=self.scheduler,
                )

            self.logger.info("Observability components initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize observability components: {e}")
            self.enabled = False

    def start(self):
        """Start all observability components."""
        if not self.enabled:
            return

        try:
            # Start scheduler first
            if self.scheduler:
                self.scheduler.start()

            if self.metrics_collector:
                self.metrics_collector.start()

            if self.tracing_manager:
                self.tracing_manager.start()

            if self.health_monitor:
                self.health_monitor.start()

            if self.error_tracker:
                self.error_tracker.start()

            if self.profiler:
                self.profiler.start()

            self.logger.info("Observability monitoring started")

        except Exception as e:
            self.logger.error(f"Failed to start observability monitoring: {e}")

    def stop(self):
        """Stop all observability components and flush data."""
        if not self.enabled:
            return

        try:
            if self.profiler:
                self.profiler.stop()

            if self.error_tracker:
                self.error_tracker.stop()

            if self.health_monitor:
                self.health_monitor.stop()

            if self.tracing_manager:
                self.tracing_manager.stop()

            if self.metrics_collector:
                self.metrics_collector.stop()

            # Stop scheduler last
            if self.scheduler:
                self.scheduler.stop(wait=True, timeout=5.0)

            self.logger.info("Observability monitoring stopped")

        except Exception as e:
            self.logger.error(f"Error stopping observability monitoring: {e}")

    def get_health_status(self) -> dict[str, Any]:
        """Get current health status of all components."""
        if not self.enabled:
            return {"observability": {"enabled": False}}

        status = {
            "observability": {
                "enabled": True,
                "export_directory": str(self.export_directory),
                "components": {},
            }
        }

        if self.metrics_collector:
            status["observability"]["components"]["metrics"] = self.metrics_collector.get_status()

        if self.tracing_manager:
            status["observability"]["components"]["tracing"] = self.tracing_manager.get_status()

        if self.health_monitor:
            status["observability"]["components"]["health"] = self.health_monitor.get_status()

        if self.error_tracker:
            status["observability"]["components"]["error_tracking"] = (
                self.error_tracker.get_status()
            )

        if self.profiler:
            status["observability"]["components"]["profiling"] = self.profiler.get_status()

        return status

    def record_session_event(self, event_type: str, metadata: dict[str, Any]):
        """Record a session-related event."""
        if not self.enabled or not self.metrics_collector:
            return

        try:
            self.metrics_collector.record_session_event(event_type, metadata)
        except Exception as e:
            self.logger.error(f"Failed to record session event: {e}")

    def record_provider_event(self, provider_name: str, event_type: str, metadata: dict[str, Any]):
        """Record a provider-related event."""
        if not self.enabled or not self.metrics_collector:
            return

        try:
            self.metrics_collector.record_provider_event(provider_name, event_type, metadata)
        except Exception as e:
            self.logger.error(f"Failed to record provider event: {e}")

    def record_error(
        self,
        error: Exception,
        context: dict[str, Any],
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ):
        """Record an error with context."""
        if not self.enabled:
            return

        try:
            # Record in metrics collector for basic stats
            if self.metrics_collector:
                self.metrics_collector.record_error(error, context)

            # Record in error tracker for detailed analysis
            if self.error_tracker:
                self.error_tracker.track_error(
                    error=error,
                    category=category,
                    severity=severity,
                    context=context,
                    session_id=context.get("session_id"),
                    provider=context.get("provider"),
                )
        except Exception as e:
            self.logger.error(f"Failed to record error: {e}")

    def create_span(self, name: str, **kwargs):
        """Create a new tracing span."""
        if not self.enabled or not self.tracing_manager:
            return self.tracing_manager.create_noop_span()

        try:
            return self.tracing_manager.create_span(name, **kwargs)
        except Exception as e:
            self.logger.error(f"Failed to create span: {e}")
            return self.tracing_manager.create_noop_span()

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()

    def register_provider_health_check(self, provider_name: str, provider_instance):
        """Register a provider for health monitoring.

        Args:
            provider_name: Name of the provider
            provider_instance: Provider instance to monitor
        """
        if self.enabled and self.health_monitor:
            try:
                self.health_monitor.register_provider_health_check(provider_name, provider_instance)
            except Exception as e:
                self.logger.error(f"Failed to register provider health check: {e}")

    def register_error_alert_callback(self, callback):
        """Register a callback for error alerts.

        Args:
            callback: Function to call when error alerts are triggered
        """
        if self.enabled and self.error_tracker:
            try:
                self.error_tracker.register_alert_callback(callback)
            except Exception as e:
                self.logger.error(f"Failed to register error alert callback: {e}")

    def get_error_summary(self, days: int = 7):
        """Get error summary for the last N days."""
        if not self.enabled or not self.error_tracker:
            return {"error": "Error tracking not enabled"}

        try:
            return self.error_tracker.get_error_summary(days)
        except Exception as e:
            self.logger.error(f"Failed to get error summary: {e}")
            return {"error": str(e)}

    def get_recent_errors(self, limit: int = 50):
        """Get recent error events."""
        if not self.enabled or not self.error_tracker:
            return []

        try:
            return self.error_tracker.get_recent_errors(limit)
        except Exception as e:
            self.logger.error(f"Failed to get recent errors: {e}")
            return []

    def get_performance_summary(self):
        """Get performance profiling summary."""
        if not self.enabled or not self.profiler:
            return {"error": "Performance profiling not enabled"}

        try:
            return self.profiler.get_summary()
        except Exception as e:
            self.logger.error(f"Failed to get performance summary: {e}")
            return {"error": str(e)}

    def get_function_stats(self, limit: int = 50):
        """Get function performance statistics."""
        if not self.enabled or not self.profiler:
            return []

        try:
            return self.profiler.get_function_stats(limit)
        except Exception as e:
            self.logger.error(f"Failed to get function stats: {e}")
            return []

    def get_performance_hotspots(self, time_window_minutes: int = 10):
        """Get recent performance hotspots."""
        if not self.enabled or not self.profiler:
            return []

        try:
            return self.profiler.get_hotspots(time_window_minutes)
        except Exception as e:
            self.logger.error(f"Failed to get performance hotspots: {e}")
            return []
