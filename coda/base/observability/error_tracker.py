"""Error tracking and alerting system for Coda.

This module provides comprehensive error tracking, categorization,
and alerting capabilities for monitoring system health and reliability.
"""

import json
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any

from ..config import ConfigManager
from .base import ObservabilityComponent
from .constants import ENV_PREFIX
from .sanitizer import DataSanitizer


class ErrorSeverity(str, Enum):
    """Error severity levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ErrorCategory(str, Enum):
    """Error categories for classification."""

    PROVIDER = "provider"
    SESSION = "session"
    CONFIGURATION = "configuration"
    NETWORK = "network"
    AUTHENTICATION = "authentication"
    VALIDATION = "validation"
    INTERNAL = "internal"
    USER = "user"


@dataclass
class ErrorEvent:
    """Represents a single error event."""

    id: str
    timestamp: datetime
    error_type: str
    error_message: str
    category: ErrorCategory
    severity: ErrorSeverity
    context: dict[str, Any]
    stack_trace: str | None = None
    user_id: str | None = None
    session_id: str | None = None
    provider: str | None = None
    resolved: bool = False
    resolution_notes: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        data["category"] = self.category.value
        data["severity"] = self.severity.value
        return data


@dataclass
class ErrorPattern:
    """Represents a pattern of errors for alerting."""

    pattern_id: str
    error_type: str
    category: ErrorCategory
    threshold_count: int
    time_window_minutes: int
    severity: ErrorSeverity
    description: str
    alert_enabled: bool = True
    last_alert: datetime | None = None
    alert_cooldown_minutes: int = 60  # Don't alert more than once per hour

    def should_alert(self, error_count: int, current_time: datetime) -> bool:
        """Check if this pattern should trigger an alert."""
        if not self.alert_enabled:
            return False

        if error_count < self.threshold_count:
            return False

        if self.last_alert:
            time_since_last = current_time - self.last_alert
            if time_since_last.total_seconds() < (self.alert_cooldown_minutes * 60):
                return False

        return True


class ErrorTracker(ObservabilityComponent):
    """Tracks and analyzes errors for alerting and monitoring."""

    def __init__(
        self,
        export_directory: Path,
        config_manager: ConfigManager,
        storage_backend=None,
        scheduler=None,
    ):
        """Initialize the error tracker.

        Args:
            export_directory: Directory to export error data
            config_manager: Configuration manager instance
            storage_backend: Optional storage backend
            scheduler: Optional shared scheduler
        """
        super().__init__(export_directory, config_manager, storage_backend, scheduler)
        self.errors_file = self.export_directory / "errors.json"
        self.patterns_file = self.export_directory / "error_patterns.json"

        # Error storage
        self.error_events: deque = deque(maxlen=10000)  # Keep last 10k errors
        self.error_counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        self.error_patterns: dict[str, ErrorPattern] = {}

        # Configuration
        self.enabled = config_manager.get_bool(
            "observability.error_tracking.enabled",
            default=True,
            env_var=f"{ENV_PREFIX}ERROR_TRACKING_ENABLED",
        )

        self.max_stack_trace_length = config_manager.get_int(
            "observability.error_tracking.max_stack_trace_length",
            default=5000,
            env_var=f"{ENV_PREFIX}ERROR_TRACKING_MAX_STACK_LENGTH",
        )

        # Alert callbacks
        self.alert_callbacks: list[Callable[[ErrorEvent, ErrorPattern], None]] = []

        # Error ID counter
        self._error_counter = 0

        # Data sanitizer
        self.sanitizer = DataSanitizer()

        # Load existing data
        self._load_error_data()
        self._load_error_patterns()

        # Register default error patterns
        self._register_default_patterns()

    def get_component_name(self) -> str:
        """Return the component name for logging."""
        return "ErrorTracker"

    def get_flush_interval(self) -> int:
        """Return the flush interval in seconds."""
        return self.config_manager.get_int(
            "observability.error_tracking.flush_interval",
            default=300,  # 5 minutes
            env_var=f"{ENV_PREFIX}ERROR_TRACKING_FLUSH_INTERVAL",
        )

    def start(self):
        """Start the error tracker."""
        if not self.enabled:
            return

        super().start()

    def _generate_error_id(self) -> str:
        """Generate a unique error ID."""
        with self._lock:
            self._error_counter += 1
            return f"err_{self._error_counter}_{int(time.time() * 1000)}"

    def track_error(
        self,
        error: Exception,
        category: ErrorCategory = ErrorCategory.INTERNAL,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
        context: dict[str, Any] | None = None,
        session_id: str | None = None,
        provider: str | None = None,
    ) -> str:
        """Track an error event.

        Args:
            error: The exception that occurred
            category: Error category for classification
            severity: Error severity level
            context: Additional context information
            session_id: Associated session ID (if any)
            provider: Associated provider (if any)

        Returns:
            Generated error ID
        """
        if not self.enabled:
            return ""

        with self._lock:
            error_id = self._generate_error_id()
            now = datetime.now(UTC)

            # Extract stack trace
            import traceback

            stack_trace = traceback.format_exc()

            # Sanitize stack trace
            stack_trace = self.sanitizer.sanitize_stack_trace(stack_trace)

            if len(stack_trace) > self.max_stack_trace_length:
                stack_trace = stack_trace[: self.max_stack_trace_length] + "... (truncated)"

            # Sanitize context
            sanitized_context = self.sanitizer.sanitize_dict(context or {})

            # Create error event
            error_event = ErrorEvent(
                id=error_id,
                timestamp=now,
                error_type=type(error).__name__,
                error_message=self.sanitizer.sanitize_string(str(error)),
                category=category,
                severity=severity,
                context=sanitized_context,
                stack_trace=stack_trace,
                session_id=session_id,
                provider=provider,
            )

            # Store the error
            self.error_events.append(error_event)

            # Update error counts
            date_key = now.strftime("%Y-%m-%d")
            hour_key = now.strftime("%Y-%m-%d-%H")

            self.error_counts[date_key][error_event.error_type] += 1
            self.error_counts[hour_key][error_event.error_type] += 1

            # Check for alert patterns
            self._check_alert_patterns(error_event)

            return error_id

    def _check_alert_patterns(self, error_event: ErrorEvent):
        """Check if the error triggers any alert patterns."""
        now = datetime.now(UTC)

        for pattern in self.error_patterns.values():
            if (
                pattern.error_type == error_event.error_type
                and pattern.category == error_event.category
            ):
                # Count recent errors of this type
                cutoff_time = now - timedelta(minutes=pattern.time_window_minutes)
                recent_count = sum(
                    1
                    for event in self.error_events
                    if (
                        event.error_type == pattern.error_type
                        and event.category == pattern.category
                        and event.timestamp >= cutoff_time
                    )
                )

                if pattern.should_alert(recent_count, now):
                    self._trigger_alert(error_event, pattern)
                    pattern.last_alert = now

    def _trigger_alert(self, error_event: ErrorEvent, pattern: ErrorPattern):
        """Trigger an alert for an error pattern."""
        for callback in self.alert_callbacks:
            try:
                callback(error_event, pattern)
            except Exception as e:
                # Don't let alert callbacks crash the error tracker
                print(f"Warning: Alert callback failed: {e}")

    def register_alert_callback(self, callback: Callable[[ErrorEvent, ErrorPattern], None]):
        """Register a callback for error alerts.

        Args:
            callback: Function to call when an alert is triggered
        """
        self.alert_callbacks.append(callback)

    def add_error_pattern(self, pattern: ErrorPattern):
        """Add a custom error pattern for monitoring.

        Args:
            pattern: Error pattern to monitor
        """
        with self._lock:
            self.error_patterns[pattern.pattern_id] = pattern

    def _register_default_patterns(self):
        """Register default error patterns for common issues."""
        # Provider connection failures
        self.add_error_pattern(
            ErrorPattern(
                pattern_id="provider_connection_failures",
                error_type="ConnectionError",
                category=ErrorCategory.PROVIDER,
                threshold_count=3,
                time_window_minutes=15,
                severity=ErrorSeverity.HIGH,
                description="Multiple provider connection failures in short time",
            )
        )

        # Authentication errors
        self.add_error_pattern(
            ErrorPattern(
                pattern_id="auth_failures",
                error_type="AuthenticationError",
                category=ErrorCategory.AUTHENTICATION,
                threshold_count=5,
                time_window_minutes=10,
                severity=ErrorSeverity.CRITICAL,
                description="Multiple authentication failures",
            )
        )

        # Configuration errors
        self.add_error_pattern(
            ErrorPattern(
                pattern_id="config_errors",
                error_type="ConfigurationError",
                category=ErrorCategory.CONFIGURATION,
                threshold_count=2,
                time_window_minutes=5,
                severity=ErrorSeverity.HIGH,
                description="Configuration errors indicating setup issues",
            )
        )

        # Session errors
        self.add_error_pattern(
            ErrorPattern(
                pattern_id="session_failures",
                error_type="SessionError",
                category=ErrorCategory.SESSION,
                threshold_count=5,
                time_window_minutes=20,
                severity=ErrorSeverity.MEDIUM,
                description="Multiple session management failures",
            )
        )

    def get_error_summary(self, days: int = 7) -> dict[str, Any]:
        """Get error summary for the last N days.

        Args:
            days: Number of days to include in summary

        Returns:
            Error summary statistics
        """
        with self._lock:
            now = datetime.now(UTC)
            cutoff_time = now - timedelta(days=days)

            # Filter recent errors
            recent_errors = [event for event in self.error_events if event.timestamp >= cutoff_time]

            # Count by type
            error_type_counts = defaultdict(int)
            category_counts = defaultdict(int)
            severity_counts = defaultdict(int)

            for event in recent_errors:
                error_type_counts[event.error_type] += 1
                category_counts[event.category.value] += 1
                severity_counts[event.severity.value] += 1

            # Get top errors
            top_errors = sorted(error_type_counts.items(), key=lambda x: x[1], reverse=True)[:10]

            return {
                "total_errors": len(recent_errors),
                "error_types": dict(error_type_counts),
                "categories": dict(category_counts),
                "severities": dict(severity_counts),
                "top_errors": top_errors,
                "time_window_days": days,
            }

    def get_recent_errors(self, limit: int = 50) -> list[dict[str, Any]]:
        """Get recent error events.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of recent error events
        """
        with self._lock:
            recent = list(self.error_events)[-limit:]
            return [event.to_dict() for event in reversed(recent)]

    def get_error_patterns(self) -> dict[str, dict[str, Any]]:
        """Get all error patterns.

        Returns:
            Dictionary of error patterns
        """
        with self._lock:
            return {
                pattern_id: {
                    "pattern_id": pattern.pattern_id,
                    "error_type": pattern.error_type,
                    "category": pattern.category.value,
                    "threshold_count": pattern.threshold_count,
                    "time_window_minutes": pattern.time_window_minutes,
                    "severity": pattern.severity.value,
                    "description": pattern.description,
                    "alert_enabled": pattern.alert_enabled,
                    "last_alert": pattern.last_alert.isoformat() if pattern.last_alert else None,
                    "alert_cooldown_minutes": pattern.alert_cooldown_minutes,
                }
                for pattern_id, pattern in self.error_patterns.items()
            }

    def resolve_error(self, error_id: str, resolution_notes: str):
        """Mark an error as resolved.

        Args:
            error_id: ID of the error to resolve
            resolution_notes: Notes about the resolution
        """
        with self._lock:
            for event in self.error_events:
                if event.id == error_id:
                    event.resolved = True
                    event.resolution_notes = resolution_notes
                    break

    def get_status(self) -> dict[str, Any]:
        """Get current status of the error tracker."""
        with self._lock:
            return {
                "enabled": self.enabled,
                "running": self._running,
                "flush_interval": self.get_flush_interval(),
                "errors_file": str(self.errors_file),
                "total_errors": len(self.error_events),
                "error_patterns_count": len(self.error_patterns),
                "alert_callbacks": len(self.alert_callbacks),
                "max_stack_trace_length": self.max_stack_trace_length,
            }

    def _load_error_data(self):
        """Load existing error data from file."""
        if not self.errors_file.exists():
            return

        try:
            with open(self.errors_file) as f:
                data = json.load(f)

            if "errors" in data:
                for error_data in data["errors"]:
                    # Convert back to ErrorEvent
                    error_data["timestamp"] = datetime.fromisoformat(error_data["timestamp"])
                    error_data["category"] = ErrorCategory(error_data["category"])
                    error_data["severity"] = ErrorSeverity(error_data["severity"])

                    event = ErrorEvent(**error_data)
                    self.error_events.append(event)

        except Exception as e:
            print(f"Warning: Failed to load error data: {e}")

    def _load_error_patterns(self):
        """Load error patterns from file."""
        if not self.patterns_file.exists():
            return

        try:
            with open(self.patterns_file) as f:
                data = json.load(f)

            if "patterns" in data:
                for pattern_data in data["patterns"]:
                    pattern_data["category"] = ErrorCategory(pattern_data["category"])
                    pattern_data["severity"] = ErrorSeverity(pattern_data["severity"])
                    if pattern_data.get("last_alert"):
                        pattern_data["last_alert"] = datetime.fromisoformat(
                            pattern_data["last_alert"]
                        )

                    pattern = ErrorPattern(**pattern_data)
                    self.error_patterns[pattern.pattern_id] = pattern

        except Exception as e:
            print(f"Warning: Failed to load error patterns: {e}")

    def _flush_data(self):
        """Flush error data to files."""
        try:
            # Save error events
            error_data = {
                "errors": [event.to_dict() for event in self.error_events],
                "last_updated": datetime.now(UTC).isoformat(),
            }

            temp_file = self.errors_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(error_data, f, indent=2)
            temp_file.replace(self.errors_file)

            # Save error patterns
            pattern_data = {
                "patterns": list(self.get_error_patterns().values()),
                "last_updated": datetime.now(UTC).isoformat(),
            }

            temp_file = self.patterns_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(pattern_data, f, indent=2)
            temp_file.replace(self.patterns_file)

        except Exception as e:
            print(f"Warning: Failed to flush error data: {e}")
