"""Integration tests for observability system with enabled/disabled states."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager
from coda.providers.mock_provider import MockProvider


class TestObservabilityEnabledDisabledStates:
    """Test observability system behavior in enabled and disabled states."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    def create_config(self, temp_dir, observability_enabled=True, component_config=None):
        """Create a configuration with specified observability settings."""
        config_path = Path(temp_dir) / "config.toml"

        if component_config is None:
            component_config = {
                "metrics.enabled": "true",
                "tracing.enabled": "true",
                "health.enabled": "true",
                "error_tracking.enabled": "true",
                "profiling.enabled": "true",
            }

        config_lines = [
            "[observability]",
            f"enabled = {str(observability_enabled).lower()}",
            f'storage_path = "{os.path.join(temp_dir, "observability")}"',
        ]

        for key, value in component_config.items():
            config_lines.append(f"{key} = {value}")

        config_lines.extend(["", "[provider.mock]", 'type = "mock"', 'model_name = "mock-smart"'])

        config_path.write_text("\n".join(config_lines))

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

    def test_all_components_enabled(self, temp_dir):
        """Test system behavior with all observability components enabled."""
        # Create config with everything enabled
        config = self.create_config(temp_dir, observability_enabled=True)

        # Initialize manager
        obs_manager = ObservabilityManager(config)

        # Verify all components are initialized
        assert obs_manager.is_enabled() is True
        assert obs_manager.metrics_collector is not None
        assert obs_manager.tracing_manager is not None
        assert obs_manager.health_monitor is not None
        assert obs_manager.error_tracker is not None
        assert obs_manager.profiler is not None

        # Test that all tracking methods work
        # 1. Events
        obs_manager.track_event("test_event", {"data": "value"})

        # 2. Traces
        with obs_manager.trace("test_operation") as span:
            span.set_attribute("test", "value")
            time.sleep(0.001)

        # 3. Errors
        obs_manager.track_error(ValueError("Test error"), {"context": "test"})

        # 4. Provider requests
        obs_manager.track_provider_request("mock", 0.1, True, {"model": "test"})

        # 5. Token usage
        obs_manager.track_token_usage("mock", 100, 50, 0.01)

        # Verify data was collected
        status = obs_manager.get_status()
        assert status["enabled"] is True
        assert all(status["components"].values())

        # Test with CLI
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            # All commands should work
            output = self.capture_output(cli._cmd_observability, "status")
            assert "Enabled: True" in output
            assert "✓" in output  # Check marks for enabled components

    def test_all_components_disabled(self, temp_dir):
        """Test system behavior with observability completely disabled."""
        # Create config with observability disabled
        config = self.create_config(temp_dir, observability_enabled=False)

        # Initialize manager
        obs_manager = ObservabilityManager(config)

        # Verify observability is disabled
        assert obs_manager.is_enabled() is False
        assert obs_manager.metrics_collector is None
        assert obs_manager.tracing_manager is None
        assert obs_manager.health_monitor is None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is None

        # Test that tracking methods do nothing (no errors)
        obs_manager.track_event("test_event", {"data": "value"})

        with obs_manager.trace("test_operation") as span:
            if span:  # Span might be None when disabled
                span.set_attribute("test", "value")

        obs_manager.track_error(ValueError("Test error"), {"context": "test"})
        obs_manager.track_provider_request("mock", 0.1, True, {"model": "test"})
        obs_manager.track_token_usage("mock", 100, 50, 0.01)

        # Test with CLI
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config

            # Commands should show disabled message
            output = self.capture_output(cli._cmd_observability, "status")
            assert "Observability is not enabled" in output

    def test_selective_component_enabling(self, temp_dir):
        """Test with only specific components enabled."""
        # Enable only metrics and health
        component_config = {
            "metrics.enabled": "true",
            "tracing.enabled": "false",
            "health.enabled": "true",
            "error_tracking.enabled": "false",
            "profiling.enabled": "false",
        }

        config = self.create_config(
            temp_dir, observability_enabled=True, component_config=component_config
        )
        obs_manager = ObservabilityManager(config)

        # Verify only specified components are enabled
        assert obs_manager.is_enabled() is True
        assert obs_manager.metrics_collector is not None
        assert obs_manager.tracing_manager is None
        assert obs_manager.health_monitor is not None
        assert obs_manager.error_tracker is None
        assert obs_manager.profiler is None

        # Test that enabled components work
        obs_manager.track_event("metrics_test", {"type": "test"})
        health_status = obs_manager.get_health_status()
        assert health_status is not None

        # Test that disabled components don't cause errors
        with obs_manager.trace("should_not_trace"):
            pass  # Should not create a trace

        obs_manager.track_error(Exception("Should not track"), {})

        # Test CLI behavior
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            # Status should show mixed state
            output = self.capture_output(cli._cmd_observability, "status")
            assert "metrics: ✓" in output
            assert "health: ✓" in output
            assert "tracing: ✗" in output
            assert "error_tracking: ✗" in output
            assert "profiling: ✗" in output

    def test_performance_impact_when_disabled(self, temp_dir):
        """Verify minimal performance impact when observability is disabled."""
        import timeit

        # Create two configs - enabled and disabled
        config_enabled = self.create_config(temp_dir, observability_enabled=True)
        config_disabled = self.create_config(temp_dir, observability_enabled=False)

        obs_enabled = ObservabilityManager(config_enabled)
        obs_disabled = ObservabilityManager(config_disabled)

        # Define test operations
        def run_operations_enabled():
            for i in range(100):
                obs_enabled.track_event(f"event_{i}", {"index": i})
                with obs_enabled.trace(f"operation_{i}"):
                    obs_enabled.track_token_usage("test", 10, 5, 0.001)

        def run_operations_disabled():
            for i in range(100):
                obs_disabled.track_event(f"event_{i}", {"index": i})
                with obs_disabled.trace(f"operation_{i}"):
                    obs_disabled.track_token_usage("test", 10, 5, 0.001)

        # Measure execution time
        time_enabled = timeit.timeit(run_operations_enabled, number=10)
        time_disabled = timeit.timeit(run_operations_disabled, number=10)

        # When disabled, operations should be significantly faster (near zero overhead)
        # Allow some variance but disabled should be at least 50% faster
        assert time_disabled < time_enabled * 0.5, (
            f"Disabled time {time_disabled} not significantly faster than enabled {time_enabled}"
        )

    def test_dynamic_component_toggling(self, temp_dir):
        """Test behavior when components are toggled during runtime."""
        config = self.create_config(temp_dir, observability_enabled=True)

        # Start with all enabled
        obs_manager = ObservabilityManager(config)

        # Track some initial data
        obs_manager.track_event("before_toggle", {"phase": "initial"})

        # Simulate config change (in reality would require restart)
        # This tests that existing manager continues to work
        config._config["observability"]["metrics"]["enabled"] = False

        # Existing manager should continue with original config
        obs_manager.track_event("after_toggle", {"phase": "post"})

        # Verify original components still work
        assert obs_manager.metrics_collector is not None

    def test_error_handling_with_partial_components(self, temp_dir):
        """Test error handling when some components are disabled."""
        # Enable only error tracking
        component_config = {
            "metrics.enabled": "false",
            "tracing.enabled": "false",
            "health.enabled": "false",
            "error_tracking.enabled": "true",
            "profiling.enabled": "false",
        }

        config = self.create_config(
            temp_dir, observability_enabled=True, component_config=component_config
        )
        obs_manager = ObservabilityManager(config)

        # Error tracking should work
        obs_manager.track_error(RuntimeError("Test error"), {"severity": "high"})

        # Other operations should not cause errors
        obs_manager.track_event("event", {})  # Metrics disabled
        with obs_manager.trace("trace"):  # Tracing disabled
            pass

        # CLI should handle gracefully
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli._observability_manager = obs_manager

            # Metrics command should indicate it's disabled
            output = self.capture_output(cli._cmd_observability, "metrics")
            assert "not enabled" in output.lower() or "disabled" in output.lower()

            # Errors command should work
            output = self.capture_output(cli._cmd_observability, "errors")
            assert "Error" in output

    def test_storage_behavior_when_disabled(self, temp_dir):
        """Test that no storage operations occur when disabled."""
        storage_path = os.path.join(temp_dir, "observability")

        # Create config with observability disabled
        config = self.create_config(temp_dir, observability_enabled=False)
        obs_manager = ObservabilityManager(config)

        # Perform operations that would normally create storage
        for i in range(10):
            obs_manager.track_event(f"event_{i}", {"data": i})
            obs_manager.track_error(Exception(f"Error {i}"), {})

        # Storage directory should not be created
        assert not os.path.exists(storage_path) or len(os.listdir(storage_path)) == 0

    def test_mixed_provider_scenarios(self, temp_dir):
        """Test observability with different provider configurations."""
        # Test with enabled observability but various provider states
        config = self.create_config(temp_dir, observability_enabled=True)

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config):
            cli = InteractiveCLI()
            cli.config_manager = config
            cli.provider = MockProvider({"model": "mock-smart"})
            cli._observability_manager = ObservabilityManager(config)

            # Simulate provider operations
            cli._observability_manager.track_provider_request(
                "mock", 0.05, True, {"model": "mock-smart"}
            )
            cli._observability_manager.track_provider_request(
                "mock", 0.08, False, {"error": "timeout"}
            )

            # Check health should reflect provider status
            output = self.capture_output(cli._cmd_observability, "health")
            assert "Health" in output

    def test_graceful_degradation(self, temp_dir):
        """Test system continues to function when observability components fail."""
        config = self.create_config(temp_dir, observability_enabled=True)

        # Create manager with mocked component that fails
        with patch(
            "coda.observability.metrics.MetricsCollector.__init__",
            side_effect=Exception("Init failed"),
        ):
            obs_manager = ObservabilityManager(config)

            # Manager should initialize but metrics should be None
            assert obs_manager.metrics_collector is None

            # Other components should still work
            if obs_manager.health_monitor:
                health = obs_manager.get_health_status()
                assert health is not None

            # Operations should not crash
            obs_manager.track_event("test", {})  # Should handle gracefully
