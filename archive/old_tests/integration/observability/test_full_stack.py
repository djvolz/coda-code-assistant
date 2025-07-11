"""Integration tests for full observability stack."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


@pytest.mark.integration
class TestObservabilityFullStack:
    """Test the full observability stack integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a configured ConfigManager for testing."""
        config = ConfigManager()
        config._config = {
            "observability": {
                "enabled": True,
                "export_directory": str(temp_dir),
                "metrics": {"enabled": True, "max_events": 1000, "max_memory_mb": 10},
                "tracing": {
                    "enabled": True,
                    "max_traces": 1000,
                    "sampling_rate": 100,  # 100% for testing
                },
                "health": {"enabled": True, "check_interval": 30},
                "error_tracking": {"enabled": True, "max_errors": 1000, "alert_threshold": 5},
                "profiling": {"enabled": False},  # Disabled for integration tests
                "scheduler": {"max_workers": 2},
            }
        }
        return config

    def test_full_initialization_and_shutdown(self, config_manager):
        """Test full system initialization and shutdown."""
        manager = ObservabilityManager(config_manager)

        # Verify all components are initialized
        assert manager.enabled
        assert manager.metrics_collector is not None
        assert manager.tracing_manager is not None
        assert manager.health_monitor is not None
        assert manager.error_tracker is not None
        assert manager.scheduler is not None

        # Start the system
        manager.start()
        assert manager._running

        # Give scheduler time to start
        time.sleep(0.1)

        # Stop the system
        manager.stop()
        assert not manager._running

    def test_cross_component_event_flow(self, config_manager):
        """Test event flow across components."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Create a traced operation
            span = manager.create_span("test_operation", {"component": "test"})
            assert span is not None

            # Record metrics within the span
            manager.record_session_event("test_event", {"data": "value"})

            # Simulate an error
            error = ValueError("Test error in operation")
            manager.record_error(error, {"operation": "test_operation"})

            # End the span
            manager.tracing_manager.end_span(span, status="error")

            # Verify data was recorded in all components
            metrics_summary = manager.metrics_collector.get_summary()
            assert metrics_summary["total_sessions"] >= 1

            traces = manager.tracing_manager.get_recent_traces(limit=10)
            assert len(traces) >= 1
            assert traces[0]["name"] == "test_operation"
            assert traces[0]["status"] == "error"

            error_summary = manager.error_tracker.get_error_summary()
            assert error_summary["total_errors"] >= 1

        finally:
            manager.stop()

    def test_health_monitoring_integration(self, config_manager):
        """Test health monitoring across components."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Update component health
            manager.health_monitor.update_component_health(
                "metrics", manager.health_monitor.HealthStatus.HEALTHY, {"info": "All good"}
            )

            # Check overall health
            health_status = manager.get_health_status()
            assert "overall_status" in health_status
            assert "components" in health_status
            assert health_status["components"]["metrics"]["status"] == "healthy"

            # Simulate a degraded component
            manager.health_monitor.update_component_health(
                "tracing",
                manager.health_monitor.HealthStatus.DEGRADED,
                {"reason": "High memory usage"},
            )

            health_status = manager.get_health_status()
            assert health_status["overall_status"] == "degraded"

        finally:
            manager.stop()

    def test_data_persistence_and_recovery(self, config_manager, temp_dir):
        """Test data persistence across restarts."""
        # First instance - record data
        manager1 = ObservabilityManager(config_manager)
        manager1.start()

        # Record various data
        manager1.record_session_event("persist_test", {"id": 1})
        manager1.record_error(ValueError("Persist error"), {"test": True})
        span = manager1.create_span("persist_span")
        manager1.tracing_manager.end_span(span)

        # Force flush
        manager1.metrics_collector.flush()
        manager1.error_tracker.flush()
        manager1.tracing_manager.flush()

        manager1.stop()

        # Verify data files exist
        assert (temp_dir / "session_events.json").exists()
        assert (temp_dir / "errors.json").exists()
        assert (temp_dir / "traces.json").exists()

        # Second instance - verify data loaded
        manager2 = ObservabilityManager(config_manager)

        # Check data was loaded
        metrics_summary = manager2.metrics_collector.get_summary()
        assert metrics_summary["total_sessions"] >= 1

        error_summary = manager2.error_tracker.get_error_summary()
        assert error_summary["total_errors"] >= 1

    def test_concurrent_operations(self, config_manager):
        """Test concurrent operations across components."""
        import threading

        manager = ObservabilityManager(config_manager)
        manager.start()

        errors = []
        completed = []

        def worker(thread_id):
            try:
                # Each thread performs multiple operations
                for i in range(10):
                    # Create span
                    span = manager.create_span(f"op_{thread_id}_{i}")

                    # Record metrics
                    manager.record_session_event(f"event_{thread_id}_{i}", {"thread": thread_id})

                    # Simulate some work
                    time.sleep(0.01)

                    # Maybe record an error
                    if i % 3 == 0:
                        manager.record_error(
                            ValueError(f"Error from thread {thread_id}"), {"iteration": i}
                        )

                    # End span
                    manager.tracing_manager.end_span(span)

                completed.append(thread_id)
            except Exception as e:
                errors.append((thread_id, e))

        # Run concurrent workers
        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Verify no errors and all completed
        assert len(errors) == 0
        assert len(completed) == 5

        # Verify data integrity
        metrics_summary = manager.metrics_collector.get_summary()
        assert metrics_summary["total_sessions"] == 50  # 5 threads * 10 events

        traces = manager.tracing_manager.get_recent_traces(limit=100)
        assert len(traces) >= 50

        manager.stop()

    def test_export_functionality(self, config_manager, temp_dir):
        """Test exporting observability data."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Generate some data
            for i in range(5):
                manager.record_session_event(f"export_test_{i}", {"index": i})
                span = manager.create_span(f"export_span_{i}")
                manager.tracing_manager.end_span(span)

            manager.record_error(ValueError("Export test error"), {})

            # Export data
            export_path = manager.export_data("json", str(temp_dir / "export.json"))
            assert export_path

            # Verify export file
            export_file = Path(export_path)
            assert export_file.exists()

            with open(export_file) as f:
                export_data = json.load(f)

            assert "metrics" in export_data
            assert "traces" in export_data
            assert "errors" in export_data
            assert "health" in export_data
            assert "metadata" in export_data

            # Verify data content
            assert export_data["metrics"]["summary"]["total_sessions"] >= 5
            assert len(export_data["traces"]["traces"]) >= 5
            assert export_data["errors"]["summary"]["total_errors"] >= 1

        finally:
            manager.stop()

    def test_memory_limits_enforced(self, config_manager):
        """Test that memory limits are enforced across components."""
        # Set very low memory limits
        config_manager._config["observability"]["metrics"]["max_memory_mb"] = 0.01
        config_manager._config["observability"]["tracing"]["max_memory_mb"] = 0.01
        config_manager._config["observability"]["error_tracking"]["max_memory_mb"] = 0.01

        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Generate lots of data
            large_data = {"data": "x" * 1000}  # ~1KB per item

            for i in range(100):
                manager.record_session_event(f"memory_test_{i}", large_data)
                span = manager.create_span(f"memory_span_{i}", large_data)
                manager.tracing_manager.end_span(span)
                manager.record_error(ValueError(f"Error {i}"), large_data)

            # Check that evictions occurred
            metrics_stats = manager.metrics_collector._session_events.get_memory_stats()
            traces_stats = manager.tracing_manager._traces.get_memory_stats()
            errors_stats = manager.error_tracker._errors.get_memory_stats()

            assert metrics_stats.items_evicted > 0
            assert traces_stats.items_evicted > 0
            assert errors_stats.items_evicted > 0

        finally:
            manager.stop()

    def test_scheduler_integration(self, config_manager):
        """Test scheduler integration with components."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        # Wait for scheduled tasks to run
        time.sleep(0.5)

        # Verify scheduler is running tasks
        assert manager.scheduler._running
        assert len(manager.scheduler._tasks) > 0

        # Verify health checks are being performed
        health_status = manager.get_health_status()
        assert "system" in health_status
        assert "filesystem" in health_status["system"]

        manager.stop()

    @patch("coda.observability.health.HealthMonitor._check_provider_availability")
    def test_provider_health_integration(self, mock_provider_check, config_manager):
        """Test provider health monitoring integration."""
        mock_provider_check.return_value = True

        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Check a provider
            manager.health_monitor.check_provider_health("openai")

            # Record provider metrics
            manager.metrics_collector.record_provider_metric("openai", "latency", 150.0)
            manager.metrics_collector.record_provider_metric("openai", "latency", 200.0)

            # Get integrated status
            status = manager.get_status()
            assert status["enabled"] is True

            # Export should include provider data
            export_data = manager.metrics_collector.get_export_data()
            assert "provider_metrics" in export_data
            assert "openai" in export_data["provider_metrics"]

        finally:
            manager.stop()
