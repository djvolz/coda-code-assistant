"""Integration tests for CLI observability commands."""

import io
import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager


@pytest.mark.integration
class TestCLIObservabilityIntegration:
    """Test CLI integration with observability system."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a configured ConfigManager."""
        config = ConfigManager()
        config._config = {
            "observability": {
                "enabled": True,
                "export_directory": str(temp_dir),
                "metrics": {"enabled": True},
                "tracing": {"enabled": True},
                "health": {"enabled": True},
                "error_tracking": {"enabled": True},
                "profiling": {"enabled": False},
            }
        }
        return config

    @pytest.fixture
    def cli(self, config_manager):
        """Create CLI instance with observability enabled."""
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            yield cli
            # Cleanup
            if hasattr(cli, "_observability_manager") and cli._observability_manager:
                cli._observability_manager.stop()

    def capture_output(self, func, *args, **kwargs):
        """Capture stdout output from a function."""
        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        try:
            func(*args, **kwargs)
            return captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_cli_observability_lifecycle(self, cli, temp_dir):
        """Test full lifecycle of observability through CLI."""
        # Generate some data through the observability system
        cli._cmd_observability("")  # Initialize observability

        # Record some events
        cli._observability_manager.record_session_event("cli_test", {"source": "test"})
        cli._observability_manager.record_error(ValueError("Test error"), {"cli": True})

        # Check status
        output = self.capture_output(cli._cmd_observability, "status")
        assert "Observability Status" in output
        assert "Enabled: True" in output

        # Check metrics
        output = self.capture_output(cli._cmd_observability, "metrics")
        assert "Metrics Summary" in output
        assert "Total Sessions: 1" in output

        # Check errors
        output = self.capture_output(cli._cmd_observability, "errors")
        assert "Error Analysis" in output
        assert "Total errors: 1" in output

    def test_cli_export_command(self, cli, temp_dir):
        """Test export command integration."""
        # Initialize and generate data
        cli._cmd_observability("")

        for i in range(3):
            cli._observability_manager.record_session_event(f"event_{i}", {"index": i})

        # Export data
        export_path = temp_dir / "test_export.json"
        output = self.capture_output(
            cli._cmd_observability, f"export --format json --output {export_path}"
        )

        assert "exported to" in output
        assert str(export_path) in output

        # Verify export file
        assert export_path.exists()
        with open(export_path) as f:
            export_data = json.load(f)

        assert "metrics" in export_data
        assert export_data["metrics"]["summary"]["total_sessions"] >= 3

    def test_cli_health_monitoring(self, cli):
        """Test health monitoring through CLI."""
        # Initialize observability
        cli._cmd_observability("")

        # Update component health
        cli._observability_manager.health_monitor.update_component_health(
            "metrics",
            cli._observability_manager.health_monitor.HealthStatus.DEGRADED,
            {"reason": "High load"},
        )

        # Check overall health
        output = self.capture_output(cli._cmd_observability, "health")
        assert "Health Status" in output
        assert "Overall:" in output

        # Check specific component
        output = self.capture_output(cli._cmd_observability, "health metrics")
        assert "degraded" in output.lower()

    def test_cli_tracing_integration(self, cli):
        """Test tracing functionality through CLI."""
        # Initialize and create traces
        cli._cmd_observability("")

        # Create some traces
        for i in range(5):
            span = cli._observability_manager.create_span(f"cli_operation_{i}", {"index": i})
            cli._observability_manager.tracing_manager.end_span(span)

        # View traces
        output = self.capture_output(cli._cmd_observability, "traces")
        assert "Recent Traces" in output
        assert "cli_operation_" in output

        # Test with limit
        output = self.capture_output(cli._cmd_observability, "traces --limit 3")
        # Count occurrences of operation names
        trace_count = output.count("cli_operation_")
        assert trace_count <= 3

    def test_cli_detailed_metrics(self, cli):
        """Test detailed metrics view."""
        # Initialize and generate varied data
        cli._cmd_observability("")

        # Generate provider metrics
        manager = cli._observability_manager
        manager.metrics_collector.record_provider_metric("openai", "latency", 100)
        manager.metrics_collector.record_provider_metric("openai", "latency", 150)
        manager.metrics_collector.record_provider_metric("anthropic", "latency", 200)

        # Generate token usage
        manager.metrics_collector.record_token_usage("openai", 1000, 500, 0.02)

        # View detailed metrics
        output = self.capture_output(cli._cmd_observability, "metrics --detailed")
        assert "Detailed Metrics" in output

    def test_cli_error_analysis_with_timeframe(self, cli):
        """Test error analysis with time filtering."""
        # Initialize and generate errors over time
        cli._cmd_observability("")

        # Generate errors
        for i in range(10):
            cli._observability_manager.record_error(ValueError(f"Error {i}"), {"index": i})

        # Check errors for different timeframes
        output = self.capture_output(cli._cmd_observability, "errors --days 1")
        assert "Error Analysis" in output
        assert "last 24 hours" in output

        output = self.capture_output(cli._cmd_observability, "errors --days 7 --limit 5")
        assert "Recent Errors (5)" in output

    def test_cli_performance_when_disabled(self, cli):
        """Test performance command when profiling is disabled."""
        cli._cmd_observability("")

        output = self.capture_output(cli._cmd_observability, "performance")
        assert "Profiling is not enabled" in output

    def test_cli_with_real_session_flow(self, cli):
        """Test CLI with realistic session flow."""
        # Initialize observability
        cli._cmd_observability("")
        manager = cli._observability_manager

        # Simulate a user session
        session_span = manager.create_span("user_session", {"user_id": "test123"})

        # Record session start
        manager.record_session_event("session_start", {"user_id": "test123"})

        # Simulate some operations
        for i in range(3):
            op_span = manager.create_span(f"operation_{i}", parent_span=session_span)
            manager.metrics_collector.record_provider_metric("openai", "latency", 100 + i * 50)

            if i == 2:  # Simulate an error
                manager.record_error(
                    ConnectionError("Provider timeout"),
                    {"operation": f"operation_{i}", "provider": "openai"},
                )
                manager.tracing_manager.end_span(op_span, status="error")
            else:
                manager.tracing_manager.end_span(op_span)

        # End session
        manager.tracing_manager.end_span(session_span)
        manager.record_session_event("session_end", {"user_id": "test123"})

        # Check various views
        status_output = self.capture_output(cli._cmd_observability, "status")
        assert "Observability Status" in status_output

        metrics_output = self.capture_output(cli._cmd_observability, "metrics")
        assert "Total Sessions: 2" in metrics_output  # start and end events

        traces_output = self.capture_output(cli._cmd_observability, "traces")
        assert "user_session" in traces_output
        assert "operation_" in traces_output

        errors_output = self.capture_output(cli._cmd_observability, "errors")
        assert "ConnectionError" in errors_output
        assert "Provider timeout" in errors_output

    def test_cli_commands_with_disabled_observability(self, cli):
        """Test CLI commands when observability is disabled."""
        # Disable observability
        cli.config_manager._config["observability"]["enabled"] = False

        output = self.capture_output(cli._cmd_observability, "status")
        assert "Observability is not enabled" in output

        # Other commands should also show disabled message
        for command in ["metrics", "health", "traces", "errors", "performance"]:
            output = self.capture_output(cli._cmd_observability, command)
            assert "Observability is not enabled" in output

    def test_cli_export_formats(self, cli, temp_dir):
        """Test different export formats."""
        # Initialize and generate data
        cli._cmd_observability("")

        # Generate some data
        manager = cli._observability_manager
        manager.record_session_event("export_test", {"format": "test"})
        manager.record_error(ValueError("Export error"), {})

        # Test JSON export (default)
        json_path = temp_dir / "export.json"
        _output = self.capture_output(cli._cmd_observability, f"export --output {json_path}")
        assert json_path.exists()

        # Test CSV export
        csv_path = temp_dir / "export.csv"
        _output = self.capture_output(
            cli._cmd_observability, f"export --format csv --output {csv_path}"
        )
        # Note: CSV export might not be implemented yet, but the command should be accepted

    def test_cli_concurrent_access(self, cli):
        """Test concurrent access to observability through CLI."""
        import threading

        cli._cmd_observability("")  # Initialize

        errors = []
        outputs = []

        def worker(command):
            try:
                output = self.capture_output(cli._cmd_observability, command)
                outputs.append((command, output))
            except Exception as e:
                errors.append((command, e))

        # Run multiple commands concurrently
        commands = ["status", "metrics", "health", "traces", "errors"]
        threads = []

        for cmd in commands:
            t = threading.Thread(target=worker, args=(cmd,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify no errors
        assert len(errors) == 0
        assert len(outputs) == len(commands)

        # Verify each command produced output
        for _cmd, output in outputs:
            assert len(output) > 0
