"""Functional tests for end-to-end observability workflows."""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


@pytest.mark.functional
class TestObservabilityWorkflows:
    """Test complete observability workflows from end to end."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test data."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a fully configured ConfigManager."""
        config = ConfigManager()
        config._config = {
            "observability": {
                "enabled": True,
                "export_directory": str(temp_dir),
                "metrics": {"enabled": True, "max_events": 10000, "max_memory_mb": 50},
                "tracing": {
                    "enabled": True,
                    "max_traces": 5000,
                    "sampling_rate": 100,
                    "max_memory_mb": 50,
                },
                "health": {
                    "enabled": True,
                    "check_interval": 5,  # Fast checks for testing
                    "failure_threshold": 3,
                },
                "error_tracking": {
                    "enabled": True,
                    "max_errors": 5000,
                    "alert_threshold": 5,
                    "max_memory_mb": 50,
                },
                "profiling": {"enabled": False},
                "scheduler": {"max_workers": 4},
            }
        }
        return config

    def test_complete_user_session_monitoring(self, config_manager, temp_dir):
        """Test monitoring a complete user session with all features."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Simulate a complete user session
            session_id = "test_session_123"
            user_id = "user_456"

            # 1. Session starts
            session_span = manager.create_span(
                "user_session",
                {
                    "session_id": session_id,
                    "user_id": user_id,
                    "start_time": datetime.now().isoformat(),
                },
            )

            manager.record_session_event(
                "session_start",
                {"session_id": session_id, "user_id": user_id, "client_version": "1.0.0"},
            )

            # 2. User performs multiple operations
            operations_performed = []

            # Operation 1: List providers
            op1_span = manager.create_span("list_providers", parent_span=session_span)
            manager.record_session_event(
                "command_executed", {"command": "list_providers", "session_id": session_id}
            )
            time.sleep(0.05)  # Simulate work
            manager.tracing_manager.end_span(op1_span)
            operations_performed.append("list_providers")

            # Operation 2: Query with provider
            op2_span = manager.create_span(
                "query_provider", {"provider": "openai", "model": "gpt-4"}, parent_span=session_span
            )

            # Record provider metrics
            manager.metrics_collector.record_provider_metric("openai", "latency", 523.4)
            manager.metrics_collector.record_token_usage("openai", 1500, 750, 0.045)

            manager.record_session_event(
                "query_completed", {"session_id": session_id, "provider": "openai", "success": True}
            )

            manager.tracing_manager.end_span(op2_span)
            operations_performed.append("query_provider")

            # Operation 3: Error scenario
            op3_span = manager.create_span("failed_operation", parent_span=session_span)

            error = ConnectionError("Provider API timeout")
            manager.record_error(
                error,
                {"session_id": session_id, "provider": "anthropic", "retry_count": 3},
                category=manager.error_tracker.ErrorCategory.NETWORK,
            )

            manager.record_session_event(
                "query_failed",
                {"session_id": session_id, "provider": "anthropic", "error": "timeout"},
            )

            manager.tracing_manager.end_span(op3_span, status="error")
            operations_performed.append("failed_operation")

            # 3. Health check during session
            manager.health_monitor.check_provider_health("openai")
            manager.health_monitor.check_provider_health("anthropic")

            # 4. Session ends
            manager.record_session_event(
                "session_end",
                {
                    "session_id": session_id,
                    "duration_seconds": 120,
                    "operations_count": len(operations_performed),
                },
            )

            manager.tracing_manager.end_span(session_span)

            # Give time for async operations
            time.sleep(0.1)

            # Verify comprehensive monitoring data

            # Check metrics
            metrics_summary = manager.metrics_collector.get_summary()
            assert metrics_summary["total_sessions"] >= 4  # start, 2 queries, end
            assert "openai" in metrics_summary["provider_summary"]
            assert metrics_summary["token_usage_summary"]["openai"]["total_cost"] == 0.045

            # Check traces
            traces = manager.tracing_manager.get_recent_traces(limit=10)
            session_trace = next((t for t in traces if t["name"] == "user_session"), None)
            assert session_trace is not None
            assert len(session_trace["children"]) == 3
            assert session_trace["attributes"]["session_id"] == session_id

            # Check errors
            recent_errors = manager.error_tracker.get_recent_errors(limit=5)
            assert len(recent_errors) >= 1
            assert recent_errors[0]["error_type"] == "ConnectionError"
            assert recent_errors[0]["context"]["session_id"] == session_id

            # Check health
            health_status = manager.get_health_status()
            assert "providers" in health_status
            assert "openai" in health_status["providers"]

            # Export complete session data
            export_path = manager.export_data("json", str(temp_dir / "session_export.json"))

            with open(export_path) as f:
                export_data = json.load(f)

            # Verify export contains all components
            assert all(key in export_data for key in ["metrics", "traces", "errors", "health"])
            assert export_data["metadata"]["export_time"]
            assert export_data["metrics"]["summary"]["total_sessions"] >= 4

        finally:
            manager.stop()

    def test_performance_degradation_detection(self, config_manager):
        """Test detecting and reporting performance degradation."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Simulate normal performance
            for i in range(5):
                span = manager.create_span(f"normal_op_{i}")
                manager.metrics_collector.record_provider_metric("openai", "latency", 100 + i * 10)
                time.sleep(0.01)
                manager.tracing_manager.end_span(span)

            # Simulate degraded performance
            for i in range(5):
                span = manager.create_span(f"slow_op_{i}")
                manager.metrics_collector.record_provider_metric("openai", "latency", 500 + i * 100)
                time.sleep(0.05)
                manager.tracing_manager.end_span(span)

            # Check if degradation is detected
            metrics = manager.metrics_collector.get_detailed_metrics()
            provider_metrics = metrics["provider_metrics"]["openai"]["latency"]

            # Calculate average latency for recent operations
            recent_latencies = provider_metrics[-5:]
            avg_recent = sum(recent_latencies) / len(recent_latencies)

            # Should show significant increase
            assert avg_recent > 500

            # Update health status based on performance
            if avg_recent > 400:
                manager.health_monitor.update_component_health(
                    "openai_performance",
                    manager.health_monitor.HealthStatus.DEGRADED,
                    {"avg_latency": avg_recent, "threshold": 400},
                )

            health_status = manager.get_health_status()
            assert health_status["components"]["openai_performance"]["status"] == "degraded"

        finally:
            manager.stop()

    def test_error_pattern_alerting(self, config_manager):
        """Test error pattern detection and alerting."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            alerts_triggered = []

            # Simulate error pattern - repeated authentication failures
            for i in range(6):  # Threshold is 5
                error = PermissionError(f"Authentication failed - attempt {i + 1}")
                should_alert = manager.record_error(
                    error,
                    {"provider": "openai", "attempt": i + 1},
                    category=manager.error_tracker.ErrorCategory.AUTHENTICATION,
                    severity=manager.error_tracker.ErrorSeverity.HIGH,
                )

                if should_alert:
                    alerts_triggered.append(i + 1)

            # Should have triggered alert after 5th error
            assert len(alerts_triggered) >= 1
            assert 6 in alerts_triggered

            # Check error patterns
            patterns = manager.error_tracker.get_error_patterns()
            auth_pattern = next((p for p in patterns if p["error_type"] == "PermissionError"), None)
            assert auth_pattern is not None
            assert auth_pattern["count"] >= 6

            # Get error analysis
            analysis = manager.error_tracker.get_error_analysis(hours=1)
            assert analysis["total_errors"] >= 6
            assert "authentication" in analysis["category_distribution"]

        finally:
            manager.stop()

    def test_resource_monitoring_workflow(self, config_manager, temp_dir):
        """Test monitoring system resources and constraints."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            # Monitor filesystem
            fs_health = manager.health_monitor.check_filesystem_health()
            assert fs_health["status"] in ["healthy", "degraded"]
            assert fs_health["space_available_gb"] > 0

            # Simulate high memory usage scenario
            large_events = []
            for i in range(100):
                event_data = {
                    "id": i,
                    "large_data": "x" * 10000,  # 10KB per event
                    "timestamp": time.time(),
                }
                manager.record_session_event(f"large_event_{i}", event_data)
                large_events.append(event_data)

            # Check memory usage reporting
            metrics_summary = manager.metrics_collector.get_summary()
            assert "memory_usage" in metrics_summary
            memory_mb = metrics_summary["memory_usage"]["session_events_memory_mb"]
            assert memory_mb > 0

            # Verify memory bounds are respected
            stats = manager.metrics_collector._session_events.get_memory_stats()
            assert stats.memory_usage_percent <= 100

        finally:
            manager.stop()

    def test_multi_provider_comparison(self, config_manager):
        """Test comparing performance across multiple providers."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            providers = ["openai", "anthropic", "google"]

            # Simulate operations with different providers
            for provider in providers:
                for i in range(10):
                    span = manager.create_span(f"{provider}_operation_{i}", {"provider": provider})

                    # Simulate varying performance
                    base_latency = {"openai": 100, "anthropic": 150, "google": 200}
                    latency = base_latency[provider] + (i * 10)

                    manager.metrics_collector.record_provider_metric(provider, "latency", latency)

                    # Simulate varying error rates
                    if provider == "google" and i % 3 == 0:
                        manager.record_error(
                            ConnectionError(f"{provider} connection failed"), {"provider": provider}
                        )

                    manager.tracing_manager.end_span(span)

            # Get comparative analysis
            metrics = manager.metrics_collector.get_summary()
            provider_summary = metrics["provider_summary"]

            # Verify all providers are tracked
            for provider in providers:
                assert provider in provider_summary
                assert "latency" in provider_summary[provider]

            # Compare average latencies
            openai_avg = provider_summary["openai"]["latency"]["average"]
            anthropic_avg = provider_summary["anthropic"]["latency"]["average"]
            google_avg = provider_summary["google"]["latency"]["average"]

            assert openai_avg < anthropic_avg < google_avg

            # Check error rates
            error_summary = manager.error_tracker.get_error_summary()
            assert error_summary["total_errors"] >= 3  # Google errors

        finally:
            manager.stop()

    def test_long_running_session_monitoring(self, config_manager):
        """Test monitoring a long-running session with periodic health checks."""
        manager = ObservabilityManager(config_manager)
        manager.start()

        try:
            session_start = time.time()

            # Start long-running operation
            main_span = manager.create_span("long_running_task", {"task_type": "batch_processing"})

            # Simulate periodic progress updates
            for i in range(5):
                # Progress update
                manager.record_session_event(
                    "progress_update", {"progress": (i + 1) * 20, "items_processed": (i + 1) * 100}
                )

                # Sub-operation
                sub_span = manager.create_span(f"batch_{i}", parent_span=main_span)
                time.sleep(0.1)  # Simulate work
                manager.tracing_manager.end_span(sub_span)

                # Periodic health check
                if i % 2 == 0:
                    manager.health_monitor.run_all_checks()

            # Complete main operation
            manager.tracing_manager.end_span(main_span)

            _session_duration = time.time() - session_start

            # Verify monitoring data
            traces = manager.tracing_manager.get_recent_traces(limit=10)
            main_trace = next((t for t in traces if t["name"] == "long_running_task"), None)

            assert main_trace is not None
            assert len(main_trace["children"]) == 5
            assert main_trace["duration"] >= 0.5  # At least 500ms

            # Check progress events
            events = list(manager.metrics_collector._session_events)
            progress_events = [e for e in events if e["event_type"] == "progress_update"]
            assert len(progress_events) == 5

        finally:
            manager.stop()

    @patch("coda.cli.interactive_cli.ConfigManager")
    def test_cli_driven_monitoring_workflow(self, mock_config_class, config_manager, temp_dir):
        """Test complete workflow driven through CLI commands."""
        mock_config_class.return_value = config_manager

        cli = InteractiveCLI()
        cli.config_manager = config_manager

        try:
            # Initialize observability through CLI
            cli._cmd_observability("status")

            # Simulate user operations
            manager = cli._observability_manager

            # Record some activity
            for i in range(3):
                manager.record_session_event(f"cli_operation_{i}", {"index": i})
                span = manager.create_span(f"operation_{i}")
                if i == 1:
                    manager.record_error(ValueError(f"Error in operation {i}"), {"op": i})
                manager.tracing_manager.end_span(span)

            # User checks various statuses through CLI
            import io
            import sys

            def capture_cli_output(command):
                old_stdout = sys.stdout
                sys.stdout = captured = io.StringIO()
                try:
                    cli._cmd_observability(command)
                    return captured.getvalue()
                finally:
                    sys.stdout = old_stdout

            # Check different views
            status_out = capture_cli_output("status")
            assert "Enabled: True" in status_out

            metrics_out = capture_cli_output("metrics")
            assert "Total Sessions: 3" in metrics_out

            errors_out = capture_cli_output("errors")
            assert "Total errors: 1" in errors_out

            traces_out = capture_cli_output("traces")
            assert "operation_" in traces_out

            # Export data
            export_out = capture_cli_output(f"export --output {temp_dir}/cli_export.json")
            assert "exported to" in export_out

            # Verify export
            assert (temp_dir / "cli_export.json").exists()

        finally:
            if hasattr(cli, "_observability_manager") and cli._observability_manager:
                cli._observability_manager.stop()
