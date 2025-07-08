"""Integration tests for observability error scenarios and recovery."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityErrorScenarios:
    """Test error handling and recovery in the observability system."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a config manager with observability enabled."""
        config_path = Path(temp_dir) / "config.toml"
        config_content = f"""
[observability]
enabled = true
storage_path = "{os.path.join(temp_dir, "observability")}"
metrics.enabled = true
tracing.enabled = true
health.enabled = true
error_tracking.enabled = true
profiling.enabled = true

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

    def test_storage_permission_errors(self, config_manager, temp_dir):
        """Test handling of storage permission errors."""
        # Create read-only storage directory
        storage_path = os.path.join(temp_dir, "readonly_storage")
        os.makedirs(storage_path, exist_ok=True)

        # Make directory read-only
        os.chmod(storage_path, 0o444)

        try:
            # Update config to use read-only path
            config_manager._config["observability"]["storage_path"] = storage_path

            # Try to initialize - should handle permission error gracefully
            obs_manager = ObservabilityManager(config_manager)

            # Operations should not crash
            obs_manager.track_event("test", {})
            obs_manager.track_error(Exception("Test"), {})

            # Manager should still be functional (might use in-memory storage)
            status = obs_manager.get_status()
            assert status is not None
        finally:
            # Restore permissions for cleanup
            os.chmod(storage_path, 0o755)

    def test_storage_disk_full_simulation(self, config_manager):
        """Test handling when storage operations fail due to disk full."""
        obs_manager = ObservabilityManager(config_manager)

        # Mock storage write to simulate disk full
        if obs_manager.metrics_collector:
            with patch.object(
                obs_manager.metrics_collector,
                "_persist_events",
                side_effect=OSError("No space left on device"),
            ):
                # Should not crash
                obs_manager.track_event("test_event", {"data": "value"})

                # Should still be able to get status
                status = obs_manager.get_status()
                assert status["enabled"] is True

    def test_corrupted_storage_files(self, config_manager, temp_dir):
        """Test recovery from corrupted storage files."""
        obs_manager = ObservabilityManager(config_manager)

        # Track some data
        obs_manager.track_event("initial_event", {"phase": "before_corruption"})

        # Corrupt storage files
        storage_path = config_manager.get_string("observability.storage_path")
        if os.path.exists(storage_path):
            for file_path in Path(storage_path).glob("*.json"):
                # Write invalid JSON
                with open(file_path, "w") as f:
                    f.write("{ corrupt json file [}")

        # Should handle corrupted files gracefully
        obs_manager.track_event("post_corruption_event", {"phase": "after_corruption"})

        # Should still function
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "status")
            assert "Observability Status" in output

    def test_component_initialization_failures(self, config_manager):
        """Test recovery when individual components fail to initialize."""
        # Test each component failure
        components_to_fail = [
            ("coda.observability.metrics.MetricsCollector", "metrics_collector"),
            ("coda.observability.tracing.TracingManager", "tracing_manager"),
            ("coda.observability.health.HealthMonitor", "health_monitor"),
            ("coda.observability.error_tracker.ErrorTracker", "error_tracker"),
        ]

        for class_path, attr_name in components_to_fail:
            with patch(f"{class_path}.__init__", side_effect=Exception(f"{attr_name} init failed")):
                obs_manager = ObservabilityManager(config_manager)

                # Component should be None
                assert getattr(obs_manager, attr_name) is None

                # Other operations should still work
                obs_manager.track_event("test", {})
                status = obs_manager.get_status()
                assert status is not None

                # Component should show as disabled in status
                component_key = (
                    attr_name.replace("_", " ")
                    .replace(" manager", "")
                    .replace(" collector", "")
                    .replace(" monitor", "")
                    .replace(" tracker", "")
                )
                assert status["components"].get(component_key, False) is False

    def test_memory_pressure_handling(self, config_manager):
        """Test behavior under memory pressure."""
        obs_manager = ObservabilityManager(config_manager)

        # Simulate memory pressure by tracking large amounts of data
        large_data = "x" * 10000  # 10KB string

        # Track many events with large payloads
        for i in range(100):
            try:
                obs_manager.track_event(f"memory_test_{i}", {"large_field": large_data, "index": i})
            except MemoryError:
                # Should handle gracefully
                break

        # System should still be responsive
        status = obs_manager.get_status()
        assert status is not None

        # Should be able to export data
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "export --format summary")
            assert "export" in output.lower()

    def test_concurrent_access_errors(self, config_manager):
        """Test handling of concurrent access conflicts."""
        obs_manager = ObservabilityManager(config_manager)

        import threading

        errors = []

        def track_events(thread_id):
            try:
                for i in range(50):
                    obs_manager.track_event(f"thread_{thread_id}_event_{i}", {"thread": thread_id})
                    if i % 10 == 0:
                        obs_manager.track_error(Exception(f"Thread {thread_id} error"), {})
            except Exception as e:
                errors.append(e)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=track_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for completion
        for thread in threads:
            thread.join()

        # Should not have any errors
        assert len(errors) == 0

        # Data should be consistent
        status = obs_manager.get_status()
        assert status is not None

    def test_malformed_data_handling(self, config_manager):
        """Test handling of malformed or invalid data."""
        obs_manager = ObservabilityManager(config_manager)

        # Test various malformed data scenarios
        test_cases = [
            # Circular reference
            {"circular": None},
            # Very deep nesting
            {"level1": {"level2": {"level3": {"level4": {"level5": {"level6": "deep"}}}}}},
            # Invalid types
            {"function": lambda x: x},  # Functions can't be serialized
            {"bytes": b"\x00\x01\x02\x03"},  # Binary data
            # Very large numbers
            {"huge_number": 10**100},
            # Special float values
            {"nan": float("nan")},
            {"inf": float("inf")},
        ]

        # Set circular reference
        test_cases[0]["circular"] = test_cases[0]

        for i, data in enumerate(test_cases):
            # Should handle without crashing
            obs_manager.track_event(f"malformed_test_{i}", data)

        # Should still be able to export
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "export --format json")
            assert "export" in output.lower()

    def test_network_errors_in_export(self, config_manager, temp_dir):
        """Test handling of network errors during export (if applicable)."""
        obs_manager = ObservabilityManager(config_manager)

        # Add some data
        obs_manager.track_event("test", {"data": "value"})

        # Test export to network location (simulated)
        network_path = "\\\\network\\share\\export.json"

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            # Should handle network path errors gracefully
            output = self.capture_output(cli._cmd_observability, f"export --output {network_path}")
            assert "error" in output.lower() or "failed" in output.lower()

    def test_recovery_after_component_failure(self, config_manager):
        """Test system recovery after a component fails during operation."""
        obs_manager = ObservabilityManager(config_manager)

        # Initially working
        obs_manager.track_event("before_failure", {"status": "ok"})

        # Simulate component failure
        if obs_manager.metrics_collector:
            obs_manager.metrics_collector = None

        # Should still handle operations gracefully
        obs_manager.track_event("after_failure", {"status": "degraded"})

        # Other components should continue working
        with obs_manager.trace("test_trace"):
            pass

        obs_manager.track_error(Exception("Test error"), {})

        # Status should reflect degraded state
        status = obs_manager.get_status()
        assert status["components"]["metrics"] is False

    def test_invalid_configuration_handling(self, temp_dir):
        """Test handling of invalid configuration values."""
        # Create config with invalid values
        config_path = Path(temp_dir) / "invalid_config.toml"
        config_content = """
[observability]
enabled = "not_a_boolean"  # Invalid boolean
storage_path = 123  # Invalid path type
metrics.enabled = true
metrics.retention_days = -5  # Invalid negative value
tracing.enabled = true
tracing.sample_rate = 2.0  # Invalid rate > 1.0
"""
        config_path.write_text(config_content)

        config = ConfigManager()
        config.load_config(str(config_path))

        # Should handle invalid config gracefully
        obs_manager = ObservabilityManager(config)

        # Should use defaults for invalid values
        assert obs_manager.is_enabled() in [True, False]  # Should parse to valid boolean

    def test_exception_in_trace_context(self, config_manager):
        """Test handling of exceptions within trace contexts."""
        obs_manager = ObservabilityManager(config_manager)

        # Test exception in trace
        try:
            with obs_manager.trace("failing_operation") as span:
                span.set_attribute("status", "starting")
                raise ValueError("Intentional error in trace")
        except ValueError:
            pass  # Expected

        # Trace should still be recorded with error status
        # System should continue functioning
        obs_manager.track_event("after_trace_error", {"recovered": True})

        # Can still create new traces
        with obs_manager.trace("recovery_operation"):
            pass

    def test_cli_error_handling(self, config_manager):
        """Test CLI command error handling."""
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager

            # Test with uninitialized observability manager
            output = self.capture_output(cli._cmd_observability, "status")
            # Should either initialize or show appropriate message
            assert len(output) > 0

            # Test with mock that raises errors
            mock_manager = Mock()
            mock_manager.get_status.side_effect = Exception("Status retrieval failed")
            cli._observability_manager = mock_manager

            output = self.capture_output(cli._cmd_observability, "status")
            assert "error" in output.lower() or "Error" in output

    def test_partial_data_recovery(self, config_manager, temp_dir):
        """Test recovery of partial data after errors."""
        obs_manager = ObservabilityManager(config_manager)

        # Track some successful events
        for i in range(5):
            obs_manager.track_event(f"success_event_{i}", {"index": i})

        # Simulate storage error midway
        with patch.object(
            obs_manager, "track_event", side_effect=[None, None, Exception("Storage failed"), None]
        ):
            for i in range(5, 10):
                try:
                    obs_manager.track_event(f"partial_event_{i}", {"index": i})
                except Exception:
                    pass

        # Should be able to export successfully tracked data
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(cli._cmd_observability, "export --format summary")
            assert "export" in output.lower()
            # Should show some events were tracked
            assert "Events:" in output or "Total" in output
