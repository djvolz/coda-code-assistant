"""Unit tests for observability manager."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityManager:
    """Test the ObservabilityManager class."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager with observability enabled."""
        config = Mock(spec=ConfigManager)
        config.get_bool.side_effect = lambda key, default=False: {
            "observability.enabled": True,
            "observability.metrics.enabled": True,
            "observability.tracing.enabled": True,
            "observability.health.enabled": True,
            "observability.error_tracking.enabled": True,
            "observability.profiling.enabled": False,
        }.get(key, default)

        config.get_string.side_effect = lambda key, default="": {
            "observability.export_directory": "/tmp/observability"
        }.get(key, default)

        config.get_int.side_effect = lambda key, default=0: {
            "observability.scheduler.max_workers": 2
        }.get(key, default)

        return config

    @pytest.fixture
    def disabled_config_manager(self):
        """Create a mock config manager with observability disabled."""
        config = Mock(spec=ConfigManager)
        config.get_bool.return_value = False
        config.get_string.return_value = ""
        config.get_int.return_value = 0
        return config

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @patch("coda.observability.manager.Path")
    @patch("coda.observability.manager.MetricsCollector")
    @patch("coda.observability.manager.TracingManager")
    @patch("coda.observability.manager.HealthMonitor")
    @patch("coda.observability.manager.ErrorTracker")
    @patch("coda.observability.manager.PeriodicTaskScheduler")
    def test_initialization_enabled(
        self,
        mock_scheduler,
        mock_error_tracker,
        mock_health,
        mock_tracing,
        mock_metrics,
        mock_path,
        config_manager,
    ):
        """Test initialization with observability enabled."""
        mock_path.return_value.expanduser.return_value = Path("/tmp/observability")
        mock_path.return_value.expanduser.return_value.exists.return_value = True

        manager = ObservabilityManager(config_manager)

        assert manager.enabled
        assert manager.metrics_collector is not None
        assert manager.tracing_manager is not None
        assert manager.health_monitor is not None
        assert manager.error_tracker is not None
        assert manager.scheduler is not None
        assert manager.profiler is None  # Profiling disabled in config

    def test_initialization_disabled(self, disabled_config_manager):
        """Test initialization with observability disabled."""
        manager = ObservabilityManager(disabled_config_manager)

        assert not manager.enabled
        assert manager.metrics_collector is None
        assert manager.tracing_manager is None
        assert manager.health_monitor is None
        assert manager.error_tracker is None
        assert manager.scheduler is None

    @patch("coda.observability.manager.Path")
    def test_initialization_creates_directory(self, mock_path, config_manager):
        """Test that initialization creates export directory if missing."""
        mock_dir = MagicMock()
        mock_dir.exists.return_value = False
        mock_path.return_value.expanduser.return_value = mock_dir

        _manager = ObservabilityManager(config_manager)

        mock_dir.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    @patch("coda.observability.manager.MetricsCollector")
    @patch("coda.observability.manager.PeriodicTaskScheduler")
    def test_start_enabled(
        self, mock_scheduler_class, mock_metrics_class, config_manager, temp_dir
    ):
        """Test starting observability when enabled."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        mock_metrics = Mock()
        mock_metrics_class.return_value = mock_metrics

        manager = ObservabilityManager(config_manager)
        manager.start()

        assert manager._running
        mock_scheduler.start.assert_called_once()
        # Verify scheduler tasks were registered
        assert mock_scheduler.schedule.call_count > 0

    def test_start_disabled(self, disabled_config_manager):
        """Test starting observability when disabled."""
        manager = ObservabilityManager(disabled_config_manager)
        manager.start()

        assert not manager._running

    @patch("coda.observability.manager.MetricsCollector")
    @patch("coda.observability.manager.PeriodicTaskScheduler")
    def test_stop(self, mock_scheduler_class, mock_metrics_class, config_manager, temp_dir):
        """Test stopping observability."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_scheduler = Mock()
        mock_scheduler_class.return_value = mock_scheduler

        mock_metrics = Mock()
        mock_metrics_class.return_value = mock_metrics

        manager = ObservabilityManager(config_manager)
        manager.start()
        manager.stop()

        assert not manager._running
        mock_scheduler.stop.assert_called_once_with(wait=True)
        mock_metrics.flush.assert_called_once()

    def test_stop_when_not_running(self, config_manager, temp_dir):
        """Test stopping when not running."""
        config_manager.get_string.return_value = str(temp_dir)

        manager = ObservabilityManager(config_manager)
        # Should not raise
        manager.stop()

    @patch("coda.observability.manager.MetricsCollector")
    def test_record_session_event_enabled(self, mock_metrics_class, config_manager, temp_dir):
        """Test recording session event when enabled."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_metrics = Mock()
        mock_metrics_class.return_value = mock_metrics

        manager = ObservabilityManager(config_manager)
        manager.record_session_event("test_event", {"key": "value"})

        mock_metrics.record_session_event.assert_called_once_with("test_event", {"key": "value"})

    def test_record_session_event_disabled(self, disabled_config_manager):
        """Test recording session event when disabled."""
        manager = ObservabilityManager(disabled_config_manager)
        # Should not raise
        manager.record_session_event("test_event", {"key": "value"})

    @patch("coda.observability.manager.ErrorTracker")
    def test_record_error_enabled(self, mock_error_class, config_manager, temp_dir):
        """Test recording error when enabled."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_error_tracker = Mock()
        mock_error_class.return_value = mock_error_tracker

        manager = ObservabilityManager(config_manager)

        error = ValueError("Test error")
        manager.record_error(error, {"context": "test"})

        mock_error_tracker.record_error.assert_called_once()
        call_args = mock_error_tracker.record_error.call_args[0]
        assert call_args[0] == error
        assert call_args[1] == {"context": "test"}

    def test_record_error_disabled(self, disabled_config_manager):
        """Test recording error when disabled."""
        manager = ObservabilityManager(disabled_config_manager)
        # Should not raise
        manager.record_error(ValueError("Test"), {})

    @patch("coda.observability.manager.TracingManager")
    def test_create_span_enabled(self, mock_tracing_class, config_manager, temp_dir):
        """Test creating span when enabled."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_tracing = Mock()
        mock_span = Mock()
        mock_tracing.create_span.return_value = mock_span
        mock_tracing_class.return_value = mock_tracing

        manager = ObservabilityManager(config_manager)

        span = manager.create_span("test_span", {"attr": "value"})

        assert span == mock_span
        mock_tracing.create_span.assert_called_once_with("test_span", {"attr": "value"})

    def test_create_span_disabled(self, disabled_config_manager):
        """Test creating span when disabled returns None."""
        manager = ObservabilityManager(disabled_config_manager)

        span = manager.create_span("test_span")
        assert span is None

    @patch("coda.observability.manager.HealthMonitor")
    def test_get_health_status_enabled(self, mock_health_class, config_manager, temp_dir):
        """Test getting health status when enabled."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_health = Mock()
        mock_health.get_status.return_value = {"status": "healthy"}
        mock_health_class.return_value = mock_health

        manager = ObservabilityManager(config_manager)

        status = manager.get_health_status()

        assert status == {"status": "healthy"}
        mock_health.get_status.assert_called_once()

    def test_get_health_status_disabled(self, disabled_config_manager):
        """Test getting health status when disabled."""
        manager = ObservabilityManager(disabled_config_manager)

        status = manager.get_health_status()
        assert status == {"enabled": False}

    def test_get_status_enabled(self, config_manager, temp_dir):
        """Test getting overall status when enabled."""
        config_manager.get_string.return_value = str(temp_dir)

        manager = ObservabilityManager(config_manager)

        status = manager.get_status()

        assert status["enabled"] is True
        assert "components" in status
        assert status["components"]["metrics"] is True
        assert status["components"]["tracing"] is True
        assert status["components"]["health"] is True
        assert status["components"]["error_tracking"] is True
        assert status["components"]["profiling"] is False

    def test_get_status_disabled(self, disabled_config_manager):
        """Test getting overall status when disabled."""
        manager = ObservabilityManager(disabled_config_manager)

        status = manager.get_status()

        assert status == {"enabled": False}

    @patch("coda.observability.manager.MetricsCollector")
    def test_export_data(self, mock_metrics_class, config_manager, temp_dir):
        """Test exporting data."""
        config_manager.get_string.return_value = str(temp_dir)

        mock_metrics = Mock()
        mock_metrics.get_summary.return_value = {"sessions": 10}
        mock_metrics_class.return_value = mock_metrics

        manager = ObservabilityManager(config_manager)

        # Mock the commands module
        with patch("coda.observability.manager.ObservabilityCommands") as mock_commands:
            mock_export = Mock(return_value="/tmp/export.json")
            mock_commands.return_value.export = mock_export

            result = manager.export_data("json", "/tmp/export.json")

            assert result == "/tmp/export.json"
            mock_export.assert_called_once()

    def test_selective_component_initialization(self, config_manager, temp_dir):
        """Test that only enabled components are initialized."""
        config_manager.get_string.return_value = str(temp_dir)

        # Modify config to disable some components
        def get_bool_side_effect(key, default=False):
            return {
                "observability.enabled": True,
                "observability.metrics.enabled": True,
                "observability.tracing.enabled": False,  # Disabled
                "observability.health.enabled": True,
                "observability.error_tracking.enabled": False,  # Disabled
                "observability.profiling.enabled": False,
            }.get(key, default)

        config_manager.get_bool.side_effect = get_bool_side_effect

        with patch("coda.observability.manager.MetricsCollector") as mock_metrics:
            with patch("coda.observability.manager.TracingManager") as mock_tracing:
                with patch("coda.observability.manager.HealthMonitor") as mock_health:
                    with patch("coda.observability.manager.ErrorTracker") as mock_error:
                        _manager = ObservabilityManager(config_manager)

                        # Enabled components should be created
                        assert mock_metrics.called
                        assert mock_health.called

                        # Disabled components should not be created
                        assert not mock_tracing.called
                        assert not mock_error.called

    def test_error_handling_in_operations(self, config_manager, temp_dir):
        """Test error handling in various operations."""
        config_manager.get_string.return_value = str(temp_dir)

        with patch("coda.observability.manager.MetricsCollector") as mock_metrics_class:
            mock_metrics = Mock()
            mock_metrics.record_session_event.side_effect = Exception("Metrics error")
            mock_metrics_class.return_value = mock_metrics

            manager = ObservabilityManager(config_manager)

            # Should not raise even if component raises
            manager.record_session_event("test", {})
