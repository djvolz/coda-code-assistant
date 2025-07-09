"""Integration tests for observability commands with mock provider."""

import os
import tempfile
import time

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import CodaConfig, ConfigManager
from coda.observability.manager import ObservabilityManager
from coda.providers.mock_provider import MockProvider


class TestObservabilityCommandsWithMockProvider:
    """Test all observability commands with mock provider integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a config manager with observability enabled."""
        # Create a CodaConfig with observability settings
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "metrics": {"enabled": True},
            "tracing": {"enabled": True},
            "health": {"enabled": True},
            "error_tracking": {"enabled": True},
            "profiling": {"enabled": True},
        }
        config.providers["mock"] = {"type": "mock", "model_name": "mock-smart"}
        config.default_provider = "mock"

        # Create ConfigManager with our config
        manager = ConfigManager()
        manager.config = config
        return manager

    @pytest.fixture
    def cli(self, config_manager):
        """Create an interactive CLI instance with mock provider."""
        cli = InteractiveCLI()
        # Manually set the config_manager attribute
        cli.config_manager = config_manager
        # Initialize provider
        cli.provider = MockProvider(model="mock-smart")
        return cli

    @pytest.fixture
    def observability_manager(self, config_manager):
        """Create an observability manager instance."""
        return ObservabilityManager(config_manager)

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

    def test_observability_status_command(self, cli, observability_manager):
        """Test observability status command with mock provider."""
        # Initialize the observability manager in CLI
        cli._observability_manager = observability_manager

        # Run status command
        output = self.capture_output(cli._cmd_observability, "status")

        # Verify output
        assert "Observability Status" in output
        assert "Enabled: True" in output
        assert "metrics: ✓" in output
        assert "tracing: ✓" in output
        assert "health: ✓" in output
        assert "error_tracking: ✓" in output
        assert "profiling: ✓" in output

    def test_observability_metrics_simple(self, cli, observability_manager):
        """Test observability metrics command without detailed flag."""
        cli._observability_manager = observability_manager

        # Generate some metrics by simulating activity
        with observability_manager.trace("test_operation"):
            observability_manager.track_event("test_event", {"key": "value"})
            observability_manager.track_token_usage("mock", 100, 50, 0.001)

        # Run metrics command
        output = self.capture_output(cli._cmd_observability, "metrics")

        # Verify output
        assert "Metrics Summary" in output
        assert "Total Sessions:" in output
        assert "Total Errors:" in output
        assert "Token Usage:" in output

    def test_observability_metrics_detailed(self, cli, observability_manager):
        """Test observability metrics command with detailed flag."""
        cli._observability_manager = observability_manager

        # Generate some metrics
        observability_manager.track_event("session_start", {"provider": "mock"})
        observability_manager.track_event("session_end", {"provider": "mock"})
        observability_manager.track_provider_request("mock", 0.123, True, {"model": "mock-smart"})

        # Run metrics command with detailed flag
        output = self.capture_output(cli._cmd_observability, "metrics --detailed")

        # Verify output
        assert "Detailed Metrics" in output or "Session Events" in output

    def test_observability_health_all_components(self, cli, observability_manager):
        """Test observability health command for all components."""
        cli._observability_manager = observability_manager

        # Run health command
        output = self.capture_output(cli._cmd_observability, "health")

        # Verify output
        assert "Health Status" in output
        assert "Overall:" in output
        assert "Components:" in output

    def test_observability_health_specific_component(self, cli, observability_manager):
        """Test observability health command for specific component."""
        cli._observability_manager = observability_manager

        # Test health for metrics component
        output = self.capture_output(cli._cmd_observability, "health metrics")

        # Verify component-specific health check was performed
        assert "metrics" in output.lower() or "healthy" in output.lower()

    def test_observability_traces_default(self, cli, observability_manager):
        """Test observability traces command with default limit."""
        cli._observability_manager = observability_manager

        # Create some traces
        for i in range(15):
            with observability_manager.trace(f"operation_{i}"):
                time.sleep(0.001)  # Small delay to create measurable duration

        # Run traces command
        output = self.capture_output(cli._cmd_observability, "traces")

        # Verify output
        assert "Recent Traces" in output or "Traces" in output
        # Should show at most 10 traces by default
        assert "operation_" in output

    def test_observability_traces_with_limit(self, cli, observability_manager):
        """Test observability traces command with custom limit."""
        cli._observability_manager = observability_manager

        # Create some traces
        for i in range(30):
            with observability_manager.trace(f"trace_{i}"):
                pass

        # Run traces command with limit
        output = self.capture_output(cli._cmd_observability, "traces --limit 25")

        # Verify output contains traces
        assert "trace_" in output

    def test_observability_export_json_default(self, cli, observability_manager, temp_dir):
        """Test observability export command with default JSON format."""
        cli._observability_manager = observability_manager

        # Generate some data
        observability_manager.track_event("export_test", {"data": "test"})

        # Run export command
        output = self.capture_output(cli._cmd_observability, "export")

        # Verify export was successful
        assert "exported to" in output.lower() or "export" in output.lower()

    def test_observability_export_custom_format_and_path(
        self, cli, observability_manager, temp_dir
    ):
        """Test observability export with custom format and output path."""
        cli._observability_manager = observability_manager

        # Generate some data
        observability_manager.track_event("export_test", {"format": "custom"})

        # Define custom output path
        output_path = os.path.join(temp_dir, "custom_export.json")

        # Run export command with custom options
        output = self.capture_output(
            cli._cmd_observability, f"export --format summary --output {output_path}"
        )

        # Verify export
        assert "export" in output.lower()

    def test_observability_errors_default(self, cli, observability_manager):
        """Test observability errors command with default options."""
        cli._observability_manager = observability_manager

        # Track some errors
        observability_manager.track_error(
            ValueError("Test error 1"), {"context": "test", "severity": "medium"}
        )
        observability_manager.track_error(
            ConnectionError("Test connection error"), {"context": "network", "severity": "high"}
        )

        # Run errors command
        output = self.capture_output(cli._cmd_observability, "errors")

        # Verify output
        assert "Error Analysis" in output or "Errors" in output
        assert "ValueError" in output or "Test error" in output

    def test_observability_errors_with_options(self, cli, observability_manager):
        """Test observability errors command with limit and days options."""
        cli._observability_manager = observability_manager

        # Track multiple errors
        for i in range(20):
            observability_manager.track_error(
                Exception(f"Error {i}"), {"index": i, "severity": "low" if i % 2 == 0 else "medium"}
            )

        # Run errors command with options
        output = self.capture_output(cli._cmd_observability, "errors --limit 15 --days 7")

        # Verify output contains error information
        assert "Error" in output

    def test_observability_performance_enabled(self, cli, observability_manager):
        """Test observability performance command when profiling is enabled."""
        cli._observability_manager = observability_manager

        # Simulate some function calls to profile
        if observability_manager.profiler:
            # Run some operations that would be profiled
            for _ in range(10):
                with observability_manager.trace("profiled_operation"):
                    time.sleep(0.001)

        # Run performance command
        output = self.capture_output(cli._cmd_observability, "performance")

        # Verify output
        assert "Performance" in output or "Profile" in output or "Profiling" in output

    def test_observability_performance_with_limit(self, cli, observability_manager):
        """Test observability performance command with custom limit."""
        cli._observability_manager = observability_manager

        # Run performance command with limit
        output = self.capture_output(cli._cmd_observability, "performance --limit 20")

        # Verify output (might show message if profiling disabled)
        assert "Performance" in output or "Profiling" in output

    def test_observability_commands_with_disabled_components(self, temp_dir):
        """Test observability commands when specific components are disabled."""
        # Create config with some components disabled
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "metrics": {"enabled": True},
            "tracing": {"enabled": False},
            "health": {"enabled": True},
            "error_tracking": {"enabled": False},
            "profiling": {"enabled": False},
        }

        # Create ConfigManager with partial config
        partial_config = ConfigManager()
        partial_config.config = config

        # Create CLI with partial config
        cli = InteractiveCLI()
        cli.config_manager = partial_config
        cli._observability_manager = ObservabilityManager(partial_config)

        # Test status shows disabled components
        output = self.capture_output(cli._cmd_observability, "status")
        assert "tracing: ✗" in output or "tracing: False" in output
        assert "error_tracking: ✗" in output or "error_tracking: False" in output
        assert "profiling: ✗" in output or "profiling: False" in output

    def test_observability_invalid_export_path(self, cli, observability_manager):
        """Test observability export with invalid output path."""
        cli._observability_manager = observability_manager

        # Try to export to an invalid path
        invalid_path = "/invalid/path/that/does/not/exist/export.json"
        output = self.capture_output(cli._cmd_observability, f"export --output {invalid_path}")

        # Should handle error gracefully
        assert (
            "error" in output.lower() or "failed" in output.lower() or "invalid" in output.lower()
        )

    def test_observability_edge_cases(self, cli, observability_manager):
        """Test edge cases and error conditions."""
        cli._observability_manager = observability_manager

        # Test with no data
        output = self.capture_output(cli._cmd_observability, "traces")
        assert "No traces" in output or "Recent Traces" in output

        # Test with malformed arguments
        output = self.capture_output(cli._cmd_observability, "metrics --invalid-flag")
        # Should either ignore invalid flag or show error
        assert "Metrics" in output or "error" in output.lower()

        # Test unknown subcommand
        output = self.capture_output(cli._cmd_observability, "unknown-command")
        assert "Unknown" in output or "Invalid" in output

    def test_observability_concurrent_operations(self, cli, observability_manager):
        """Test observability commands during concurrent operations."""
        cli._observability_manager = observability_manager

        # Simulate concurrent operations
        import threading

        def track_events():
            for i in range(10):
                observability_manager.track_event(f"concurrent_event_{i}", {"thread": "worker"})
                time.sleep(0.001)

        # Start background thread
        thread = threading.Thread(target=track_events)
        thread.start()

        # Run commands while background operations are happening
        output1 = self.capture_output(cli._cmd_observability, "status")
        output2 = self.capture_output(cli._cmd_observability, "metrics")

        # Wait for thread to complete
        thread.join()

        # Verify commands executed successfully
        assert "Observability Status" in output1
        assert "Metrics" in output2
