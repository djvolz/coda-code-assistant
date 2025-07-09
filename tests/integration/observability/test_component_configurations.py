"""Integration tests for individual observability component configurations."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


class TestIndividualComponentConfigurations:
    """Test each observability component in isolation and various combinations."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def create_config_with_components(self, temp_dir, **components):
        """Create config with specific components enabled/disabled."""
        config_path = Path(temp_dir) / "config.toml"

        # Default all components to false
        defaults = {
            "metrics": False,
            "tracing": False,
            "health": False,
            "error_tracking": False,
            "profiling": False,
        }
        defaults.update(components)

        config_content = f"""
[observability]
enabled = true
storage_path = "{os.path.join(temp_dir, "observability")}"
metrics.enabled = {str(defaults["metrics"]).lower()}
tracing.enabled = {str(defaults["tracing"]).lower()}
health.enabled = {str(defaults["health"]).lower()}
error_tracking.enabled = {str(defaults["error_tracking"]).lower()}
profiling.enabled = {str(defaults["profiling"]).lower()}

[provider.mock]
type = "mock"
model_name = "mock-smart"
"""
        config_path.write_text(config_content)

        manager = ConfigManager()
        manager.load_config(str(config_path))
        return manager

    def capture_output(self, func, *args, **kwargs):
        """Capture stdout output from a function."""
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        try:
            func(*args, **kwargs)
            return captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_metrics_only_configuration(self, temp_dir):
        """Test with only metrics component enabled."""
        config = self.create_config_with_components(temp_dir, metrics=True)
        obs_manager = ObservabilityManager(config)

        # Verify only metrics is enabled
        assert obs_manager.metrics_collector is not None
        assert obs_manager.tracing_manager is None
        assert obs_manager.health_monitor is None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is None

        # Test metrics operations work
        obs_manager.track_event("session_start", {"user": "test"})
        obs_manager.track_token_usage("mock", 100, 50, 0.01)
        obs_manager.track_provider_request("mock", 0.1, True, {})

        # Test metrics command works
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "metrics")
            assert "Metrics Summary" in output

            # Other commands should indicate component is disabled
            output = self.capture_output(cli._cmd_observability, "traces")
            assert "not enabled" in output.lower() or "disabled" in output.lower()

    def test_tracing_only_configuration(self, temp_dir):
        """Test with only tracing component enabled."""
        config = self.create_config_with_components(temp_dir, tracing=True)
        obs_manager = ObservabilityManager(config)

        # Verify only tracing is enabled
        assert obs_manager.metrics_collector is None
        assert obs_manager.tracing_manager is not None
        assert obs_manager.health_monitor is None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is None

        # Test tracing operations work
        with obs_manager.trace("test_operation") as span:
            span.set_attribute("component", "test")
            span.set_attribute("duration", 0.1)

        # Test nested traces
        with obs_manager.trace("parent_operation") as parent:
            parent.set_attribute("level", "parent")
            with obs_manager.trace("child_operation") as child:
                child.set_attribute("level", "child")

        # Test traces command works
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "traces")
            assert "test_operation" in output or "Traces" in output

    def test_health_only_configuration(self, temp_dir):
        """Test with only health component enabled."""
        config = self.create_config_with_components(temp_dir, health=True)
        obs_manager = ObservabilityManager(config)

        # Verify only health is enabled
        assert obs_manager.metrics_collector is None
        assert obs_manager.tracing_manager is None
        assert obs_manager.health_monitor is not None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is None

        # Test health operations
        health_status = obs_manager.get_health_status()
        assert health_status is not None
        assert "overall_status" in health_status

        # Test health command works
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "health")
            assert "Health Status" in output

            # Test component-specific health
            output = self.capture_output(cli._cmd_observability, "health system")
            assert "health" in output.lower()

    def test_error_tracking_only_configuration(self, temp_dir):
        """Test with only error tracking component enabled."""
        config = self.create_config_with_components(temp_dir, error_tracking=True)
        obs_manager = ObservabilityManager(config)

        # Verify only error tracking is enabled
        assert obs_manager.metrics_collector is None
        assert obs_manager.tracing_manager is None
        assert obs_manager.health_monitor is None
        assert obs_manager.error_tracker is not None
        assert obs_manager.profiler is None

        # Test error tracking operations
        obs_manager.track_error(ValueError("Test validation error"), {"field": "username"})
        obs_manager.track_error(ConnectionError("Network timeout"), {"retry_count": 3})
        obs_manager.track_error(RuntimeError("Critical error"), {"severity": "high"})

        # Test errors command works
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "errors")
            assert "Error" in output
            assert "ValueError" in output or "Test validation error" in output

    def test_profiling_only_configuration(self, temp_dir):
        """Test with only profiling component enabled."""
        config = self.create_config_with_components(temp_dir, profiling=True)
        obs_manager = ObservabilityManager(config)

        # Verify only profiling is enabled
        assert obs_manager.metrics_collector is None
        assert obs_manager.tracing_manager is None
        assert obs_manager.health_monitor is None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is not None

        # Test performance command
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "performance")
            assert "Performance" in output or "Profile" in output

    def test_metrics_and_tracing_combination(self, temp_dir):
        """Test with metrics and tracing enabled together."""
        config = self.create_config_with_components(temp_dir, metrics=True, tracing=True)
        obs_manager = ObservabilityManager(config)

        # Verify both components are enabled
        assert obs_manager.metrics_collector is not None
        assert obs_manager.tracing_manager is not None
        assert obs_manager.health_monitor is None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is None

        # Test combined operations
        with obs_manager.trace("api_request") as span:
            span.set_attribute("endpoint", "/chat")
            obs_manager.track_provider_request("mock", 0.15, True, {"tokens": 100})
            obs_manager.track_token_usage("mock", 100, 50, 0.01)

        # Both commands should work
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "metrics")
            assert "Metrics" in output

            output = self.capture_output(cli._cmd_observability, "traces")
            assert "api_request" in output or "Traces" in output

    def test_health_and_error_tracking_combination(self, temp_dir):
        """Test with health and error tracking enabled together."""
        config = self.create_config_with_components(temp_dir, health=True, error_tracking=True)
        obs_manager = ObservabilityManager(config)

        # Test error impact on health
        obs_manager.track_error(
            Exception("Service unavailable"), {"service": "database", "severity": "high"}
        )
        obs_manager.track_error(Exception("Minor warning"), {"severity": "low"})

        health_status = obs_manager.get_health_status()
        assert health_status is not None

        # Both commands should work
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "health")
            assert "Health" in output

            output = self.capture_output(cli._cmd_observability, "errors")
            assert "Service unavailable" in output or "Error" in output

    def test_all_except_profiling_configuration(self, temp_dir):
        """Test with all components except profiling enabled."""
        config = self.create_config_with_components(
            temp_dir, metrics=True, tracing=True, health=True, error_tracking=True, profiling=False
        )
        obs_manager = ObservabilityManager(config)

        # Verify profiling is disabled
        assert obs_manager.profiler is None

        # All other components should work
        obs_manager.track_event("test", {})
        with obs_manager.trace("operation"):
            pass
        obs_manager.track_error(Exception("Test"), {})
        health = obs_manager.get_health_status()
        assert health is not None

        # Performance command should indicate profiling is disabled
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "performance")
            assert "not enabled" in output.lower() or "disabled" in output.lower()

    def test_minimal_configuration(self, temp_dir):
        """Test with minimal configuration (only health for basic monitoring)."""
        config = self.create_config_with_components(temp_dir, health=True)
        obs_manager = ObservabilityManager(config)

        # Should provide basic monitoring capability
        health = obs_manager.get_health_status()
        assert health["overall_status"] in ["healthy", "degraded", "unhealthy"]

        # Test export with minimal data
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "export --format summary")
            assert "export" in output.lower()

    def test_component_initialization_failures(self, temp_dir):
        """Test graceful handling of component initialization failures."""
        config = self.create_config_with_components(
            temp_dir, metrics=True, tracing=True, health=True
        )

        # Mock a component to fail initialization
        with patch(
            "coda.observability.tracing.TracingManager.__init__",
            side_effect=Exception("Init failed"),
        ):
            obs_manager = ObservabilityManager(config)

            # Other components should still initialize
            assert obs_manager.metrics_collector is not None
            assert obs_manager.tracing_manager is None  # Failed to initialize
            assert obs_manager.health_monitor is not None

            # Operations should still work for initialized components
            obs_manager.track_event("test", {})
            health = obs_manager.get_health_status()
            assert health is not None

    def test_dynamic_component_states(self, temp_dir):
        """Test component behavior with dynamic state changes."""
        # Start with all enabled
        config = self.create_config_with_components(
            temp_dir, metrics=True, tracing=True, health=True, error_tracking=True, profiling=True
        )
        obs_manager = ObservabilityManager(config)

        # Track initial state
        initial_status = obs_manager.get_status()
        assert all(initial_status["components"].values())

        # Components should maintain their state throughout lifecycle
        for _ in range(10):
            obs_manager.track_event("event", {})
            with obs_manager.trace("op"):
                pass

        # Status should remain consistent
        final_status = obs_manager.get_status()
        assert final_status == initial_status
