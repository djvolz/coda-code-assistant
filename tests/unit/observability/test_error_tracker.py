"""Unit tests for error tracker."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.configuration import ConfigManager
from coda.observability.error_tracker import ErrorCategory, ErrorSeverity, ErrorTracker


class TestErrorCategory:
    """Test the ErrorCategory enum."""

    def test_error_category_values(self):
        """Test error category enum values."""
        assert ErrorCategory.PROVIDER.value == "provider"
        assert ErrorCategory.SESSION.value == "session"
        assert ErrorCategory.CONFIGURATION.value == "configuration"
        assert ErrorCategory.NETWORK.value == "network"
        assert ErrorCategory.AUTHENTICATION.value == "authentication"
        assert ErrorCategory.SYSTEM.value == "system"
        assert ErrorCategory.UNKNOWN.value == "unknown"


class TestErrorSeverity:
    """Test the ErrorSeverity enum."""

    def test_error_severity_values(self):
        """Test error severity enum values."""
        assert ErrorSeverity.LOW.value == "low"
        assert ErrorSeverity.MEDIUM.value == "medium"
        assert ErrorSeverity.HIGH.value == "high"
        assert ErrorSeverity.CRITICAL.value == "critical"


class TestErrorTracker:
    """Test the ErrorTracker class."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager."""
        config = Mock(spec=ConfigManager)
        config.get_int.side_effect = lambda key, default=0: {
            "observability.error_tracking.max_errors": 1000,
            "observability.error_tracking.max_memory_mb": 10,
            "observability.error_tracking.alert_threshold": 5,
        }.get(key, default)
        return config

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, temp_dir, config_manager):
        """Test ErrorTracker initialization."""
        tracker = ErrorTracker(temp_dir, config_manager)

        assert tracker.base_dir == temp_dir
        assert tracker.config_manager == config_manager
        assert hasattr(tracker, "_errors")
        assert hasattr(tracker, "_error_patterns")
        assert hasattr(tracker, "_alert_counts")

    def test_record_error_basic(self, temp_dir, config_manager):
        """Test recording a basic error."""
        tracker = ErrorTracker(temp_dir, config_manager)

        error = ValueError("Test error")
        context = {"operation": "test_op", "user": "test_user"}

        tracker.record_error(error, context)

        errors = list(tracker._errors)
        assert len(errors) == 1

        recorded = errors[0]
        assert recorded["error_type"] == "ValueError"
        assert recorded["error_message"] == "Test error"
        assert recorded["context"] == context
        assert recorded["category"] == ErrorCategory.UNKNOWN.value
        assert recorded["severity"] == ErrorSeverity.MEDIUM.value
        assert "timestamp" in recorded
        assert "stack_trace" in recorded

    def test_record_error_with_category_and_severity(self, temp_dir, config_manager):
        """Test recording error with explicit category and severity."""
        tracker = ErrorTracker(temp_dir, config_manager)

        error = ConnectionError("Network timeout")
        context = {"provider": "openai"}

        tracker.record_error(
            error, context, category=ErrorCategory.NETWORK, severity=ErrorSeverity.HIGH
        )

        errors = list(tracker._errors)
        assert errors[0]["category"] == ErrorCategory.NETWORK.value
        assert errors[0]["severity"] == ErrorSeverity.HIGH.value

    def test_categorize_error(self, temp_dir, config_manager):
        """Test automatic error categorization."""
        tracker = ErrorTracker(temp_dir, config_manager)

        test_cases = [
            (ConnectionError("timeout"), ErrorCategory.NETWORK),
            (TimeoutError("timeout"), ErrorCategory.NETWORK),
            (PermissionError("denied"), ErrorCategory.AUTHENTICATION),
            (FileNotFoundError("not found"), ErrorCategory.CONFIGURATION),
            (KeyError("missing"), ErrorCategory.CONFIGURATION),
            (ValueError("invalid"), ErrorCategory.UNKNOWN),
        ]

        for error, expected_category in test_cases:
            category = tracker._categorize_error(error)
            assert category == expected_category

    def test_determine_severity(self, temp_dir, config_manager):
        """Test automatic severity determination."""
        tracker = ErrorTracker(temp_dir, config_manager)

        test_cases = [
            (PermissionError("denied"), ErrorSeverity.HIGH),
            (ConnectionError("refused"), ErrorSeverity.HIGH),
            (TimeoutError("timeout"), ErrorSeverity.MEDIUM),
            (ValueError("invalid"), ErrorSeverity.MEDIUM),
            (KeyError("missing"), ErrorSeverity.LOW),
        ]

        for error, expected_severity in test_cases:
            severity = tracker._determine_severity(error)
            assert severity == expected_severity

    def test_pattern_detection(self, temp_dir, config_manager):
        """Test error pattern detection."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record similar errors
        for i in range(10):
            error = ConnectionError("Connection failed to provider")
            tracker.record_error(error, {"provider": "openai", "attempt": i})

        patterns = tracker.get_error_patterns()

        assert len(patterns) > 0
        # Should detect the repeated connection errors
        pattern_found = False
        for pattern in patterns:
            if pattern["error_type"] == "ConnectionError" and pattern["count"] >= 10:
                pattern_found = True
                break
        assert pattern_found

    def test_alert_triggering(self, temp_dir, config_manager):
        """Test alert triggering based on threshold."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record critical errors
        for i in range(6):  # Threshold is 5
            error = PermissionError("Access denied")
            should_alert = tracker.record_error(
                error, {"attempt": i}, severity=ErrorSeverity.CRITICAL
            )

            if i < 5:
                assert not should_alert
            else:
                assert should_alert  # Should trigger alert after 5th error

    def test_get_recent_errors(self, temp_dir, config_manager):
        """Test getting recent errors."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record various errors
        for i in range(10):
            error = ValueError(f"Error {i}")
            tracker.record_error(error, {"index": i})

        recent = tracker.get_recent_errors(limit=5)

        assert len(recent) == 5
        # Should be most recent first
        assert recent[0]["context"]["index"] == 9
        assert recent[4]["context"]["index"] == 5

    def test_get_recent_errors_by_category(self, temp_dir, config_manager):
        """Test getting recent errors filtered by category."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record different categories
        tracker.record_error(ConnectionError("Network error"), {}, category=ErrorCategory.NETWORK)
        tracker.record_error(ValueError("Config error"), {}, category=ErrorCategory.CONFIGURATION)
        tracker.record_error(
            TimeoutError("Another network error"), {}, category=ErrorCategory.NETWORK
        )

        network_errors = tracker.get_recent_errors(category=ErrorCategory.NETWORK)
        assert len(network_errors) == 2
        assert all(e["category"] == ErrorCategory.NETWORK.value for e in network_errors)

    def test_get_recent_errors_by_severity(self, temp_dir, config_manager):
        """Test getting recent errors filtered by severity."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record different severities
        tracker.record_error(ValueError("Low"), {}, severity=ErrorSeverity.LOW)
        tracker.record_error(ValueError("High"), {}, severity=ErrorSeverity.HIGH)
        tracker.record_error(ValueError("Critical"), {}, severity=ErrorSeverity.CRITICAL)
        tracker.record_error(ValueError("High2"), {}, severity=ErrorSeverity.HIGH)

        high_severity = tracker.get_recent_errors(severity=ErrorSeverity.HIGH)
        assert len(high_severity) == 2
        assert all(e["severity"] == ErrorSeverity.HIGH.value for e in high_severity)

    def test_get_error_summary(self, temp_dir, config_manager):
        """Test getting error summary."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record various errors
        tracker.record_error(ValueError("1"), {}, category=ErrorCategory.CONFIGURATION)
        tracker.record_error(ValueError("2"), {}, category=ErrorCategory.CONFIGURATION)
        tracker.record_error(ConnectionError("3"), {}, category=ErrorCategory.NETWORK)
        tracker.record_error(PermissionError("4"), {}, severity=ErrorSeverity.HIGH)

        summary = tracker.get_error_summary()

        assert summary["total_errors"] == 4
        assert summary["by_category"]["configuration"] == 2
        assert summary["by_category"]["network"] == 1
        assert summary["by_severity"]["high"] == 1
        assert "by_type" in summary
        assert "recent_patterns" in summary

    def test_get_error_analysis(self, temp_dir, config_manager):
        """Test getting error analysis."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record errors over time
        base_time = time.time()
        for i in range(20):
            error = ValueError(f"Error {i}")
            # Mock timestamp
            with patch("time.time", return_value=base_time + i * 60):
                tracker.record_error(error, {"index": i})

        analysis = tracker.get_error_analysis(hours=1)

        assert "total_errors" in analysis
        assert "errors_per_hour" in analysis
        assert "top_errors" in analysis
        assert "severity_distribution" in analysis
        assert "category_distribution" in analysis

    def test_memory_limit_enforcement(self, temp_dir, config_manager):
        """Test memory limit enforcement."""
        # Set very low memory limit
        config_manager.get_int.side_effect = lambda key, default=0: {
            "observability.error_tracking.max_errors": 10000,
            "observability.error_tracking.max_memory_mb": 0.001,  # 1KB
            "observability.error_tracking.alert_threshold": 5,
        }.get(key, default)

        tracker = ErrorTracker(temp_dir, config_manager)

        # Record errors with large stack traces
        for i in range(20):
            error = ValueError(f"Error with large context {i}")
            large_context = {"data": "x" * 500}
            tracker.record_error(error, large_context)

        # Should have evicted some errors
        stats = tracker._errors.get_memory_stats()
        assert stats.items_evicted > 0

    def test_flush_data(self, temp_dir, config_manager):
        """Test flushing error data."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record some errors
        for i in range(5):
            tracker.record_error(ValueError(f"Error {i}"), {"index": i})

        tracker._flush_data()

        # Check data was saved
        errors_file = temp_dir / "errors.json"
        assert errors_file.exists()

    def test_thread_safety(self, temp_dir, config_manager):
        """Test thread safety of error tracking."""
        import threading

        tracker = ErrorTracker(temp_dir, config_manager)
        errors_recorded = []
        thread_errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    error = ValueError(f"Error from thread {thread_id}, iteration {i}")
                    tracker.record_error(error, {"thread": thread_id, "iteration": i})
                    errors_recorded.append(1)
            except Exception as e:
                thread_errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(thread_errors) == 0
        assert len(errors_recorded) == 250

        # Verify all errors were recorded
        summary = tracker.get_error_summary()
        assert summary["total_errors"] == 250

    def test_export_format(self, temp_dir, config_manager):
        """Test export data format."""
        tracker = ErrorTracker(temp_dir, config_manager)

        # Record various errors
        tracker.record_error(
            ValueError("Test error"),
            {"operation": "test"},
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.HIGH,
        )

        export_data = tracker.get_export_data()

        assert "errors" in export_data
        assert "error_patterns" in export_data
        assert "summary" in export_data
        assert "analysis" in export_data

    def test_stack_trace_sanitization(self, temp_dir, config_manager):
        """Test that stack traces are properly captured and sanitized."""
        tracker = ErrorTracker(temp_dir, config_manager)

        def cause_error():
            def inner_function():
                raise ValueError("Test error with sensitive data: password=secret123")

            inner_function()

        try:
            cause_error()
        except ValueError as e:
            tracker.record_error(e, {})

        errors = list(tracker._errors)
        assert len(errors) == 1

        # Stack trace should be captured
        assert "stack_trace" in errors[0]
        assert len(errors[0]["stack_trace"]) > 0

        # Sensitive data should be sanitized
        stack_trace = errors[0]["stack_trace"]
        assert "secret123" not in stack_trace
        assert "***REDACTED***" in stack_trace
