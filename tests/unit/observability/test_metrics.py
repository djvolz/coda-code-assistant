"""Unit tests for metrics collector."""

import json
import tempfile
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from coda.configuration import ConfigManager
from coda.observability.metrics import MetricsCollector


class TestMetricsCollector:
    """Test the MetricsCollector class."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager."""
        config = Mock(spec=ConfigManager)
        config.get_int.side_effect = lambda key, default=0: {
            "observability.metrics.max_events": 10000,
            "observability.metrics.max_memory_mb": 10,
        }.get(key, default)
        return config

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, temp_dir, config_manager):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector(temp_dir, config_manager)

        assert collector.base_dir == temp_dir
        assert collector.config_manager == config_manager
        assert hasattr(collector, "_session_events")
        assert hasattr(collector, "_lifecycle_events")
        assert hasattr(collector, "_provider_metrics")
        assert hasattr(collector, "_error_counts")
        assert hasattr(collector, "_token_usage")

    def test_record_session_event(self, temp_dir, config_manager):
        """Test recording session events."""
        collector = MetricsCollector(temp_dir, config_manager)

        event_data = {"user": "test", "action": "query"}
        collector.record_session_event("user_query", event_data)

        # Check event was recorded
        events = list(collector._session_events)
        assert len(events) == 1
        assert events[0]["event_type"] == "user_query"
        assert events[0]["data"] == event_data
        assert "timestamp" in events[0]

    def test_record_session_event_memory_limit(self, temp_dir, config_manager):
        """Test session event memory limits."""
        # Set very low memory limit
        config_manager.get_int.side_effect = lambda key, default=0: {
            "observability.metrics.max_events": 10000,
            "observability.metrics.max_memory_mb": 0.001,  # 1KB
        }.get(key, default)

        collector = MetricsCollector(temp_dir, config_manager)

        # Add large events
        large_data = {"data": "x" * 1000}  # ~1KB
        for i in range(10):
            collector.record_session_event(f"event_{i}", large_data)

        # Should have evicted some events
        stats = collector._session_events.get_memory_stats()
        assert stats.items_evicted > 0

    def test_record_lifecycle_event(self, temp_dir, config_manager):
        """Test recording lifecycle events."""
        collector = MetricsCollector(temp_dir, config_manager)

        collector.record_lifecycle_event("startup", {"version": "1.0"})
        collector.record_lifecycle_event("shutdown", {"reason": "normal"})

        events = list(collector._lifecycle_events)
        assert len(events) == 2
        assert events[0]["event_type"] == "startup"
        assert events[1]["event_type"] == "shutdown"

    def test_record_provider_metric(self, temp_dir, config_manager):
        """Test recording provider metrics."""
        collector = MetricsCollector(temp_dir, config_manager)

        collector.record_provider_metric("openai", "latency", 150.5)
        collector.record_provider_metric("openai", "latency", 200.0)
        collector.record_provider_metric("anthropic", "latency", 100.0)

        # Check metrics were recorded
        assert "openai" in collector._provider_metrics
        assert "anthropic" in collector._provider_metrics
        assert "latency" in collector._provider_metrics["openai"]
        assert len(collector._provider_metrics["openai"]["latency"]) == 2

    def test_increment_error_count(self, temp_dir, config_manager):
        """Test incrementing error counts."""
        collector = MetricsCollector(temp_dir, config_manager)

        collector.increment_error_count("network_error")
        collector.increment_error_count("network_error")
        collector.increment_error_count("auth_error")

        assert collector._error_counts["network_error"] == 2
        assert collector._error_counts["auth_error"] == 1

    def test_record_token_usage(self, temp_dir, config_manager):
        """Test recording token usage."""
        collector = MetricsCollector(temp_dir, config_manager)

        collector.record_token_usage("openai", 1000, 500, 0.02)
        collector.record_token_usage("openai", 500, 250, 0.01)
        collector.record_token_usage("anthropic", 2000, 1000, 0.03)

        assert "openai" in collector._token_usage
        assert "anthropic" in collector._token_usage

        openai_usage = collector._token_usage["openai"]
        assert openai_usage["input_tokens"] == 1500
        assert openai_usage["output_tokens"] == 750
        assert openai_usage["total_cost"] == 0.03

    def test_get_summary(self, temp_dir, config_manager):
        """Test getting metrics summary."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Add some data
        collector.record_session_event("query", {"test": "data"})
        collector.record_lifecycle_event("startup", {})
        collector.record_provider_metric("openai", "latency", 150.0)
        collector.increment_error_count("network_error")
        collector.record_token_usage("openai", 1000, 500, 0.02)

        summary = collector.get_summary()

        assert summary["total_sessions"] == 1
        assert summary["total_lifecycle_events"] == 1
        assert "provider_summary" in summary
        assert "error_summary" in summary
        assert "token_usage_summary" in summary

    def test_get_detailed_metrics(self, temp_dir, config_manager):
        """Test getting detailed metrics."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Add test data
        for i in range(5):
            collector.record_session_event(f"event_{i}", {"index": i})

        collector.record_provider_metric("openai", "latency", 150.0)
        collector.record_provider_metric("openai", "latency", 200.0)

        detailed = collector.get_detailed_metrics()

        assert "session_events" in detailed
        assert len(detailed["session_events"]) == 5
        assert "provider_metrics" in detailed
        assert "openai" in detailed["provider_metrics"]

    def test_get_daily_stats(self, temp_dir, config_manager):
        """Test getting daily statistics."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Simulate activity over multiple days
        today = datetime.now().strftime("%Y-%m-%d")

        # Add data for today
        collector.record_session_event("query", {})
        collector.record_session_event("query", {})
        collector.increment_error_count("error1")

        # Update daily stats
        collector._update_daily_stats()

        stats = collector.get_daily_stats(days=7)

        assert today in stats
        assert stats[today]["sessions"] == 2
        assert stats[today]["errors"] == 1

    def test_flush_data(self, temp_dir, config_manager):
        """Test flushing data to storage."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Add some data
        collector.record_session_event("test", {"data": "value"})
        collector.record_provider_metric("openai", "latency", 100.0)

        # Flush data
        collector._flush_data()

        # Check that data was saved
        session_file = temp_dir / "session_events.json"
        assert session_file.exists()

        with open(session_file) as f:
            saved_events = json.load(f)
        assert len(saved_events) > 0

    def test_load_existing_data(self, temp_dir, config_manager):
        """Test loading existing data on initialization."""
        # Pre-create some data files
        session_data = [{"event_type": "old_event", "data": {}, "timestamp": time.time()}]
        daily_stats = {"2023-01-01": {"sessions": 10, "errors": 2}}

        with open(temp_dir / "session_events.json", "w") as f:
            json.dump(session_data, f)

        with open(temp_dir / "daily_stats.json", "w") as f:
            json.dump(daily_stats, f)

        # Create collector - should load existing data
        collector = MetricsCollector(temp_dir, config_manager)

        # Check data was loaded
        events = list(collector._session_events)
        assert len(events) == 1
        assert events[0]["event_type"] == "old_event"

        assert "2023-01-01" in collector._daily_stats

    def test_thread_safety(self, temp_dir, config_manager):
        """Test thread safety of metrics recording."""
        import threading

        collector = MetricsCollector(temp_dir, config_manager)
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    collector.record_session_event(f"event_{thread_id}_{i}", {"thread": thread_id})
                    collector.record_provider_metric(f"provider_{thread_id}", "metric", float(i))
                    collector.increment_error_count(f"error_{thread_id}")
                    collector.record_token_usage(f"provider_{thread_id}", 100, 50, 0.01)
            except Exception as e:
                errors.append(e)

        threads = []
        for i in range(5):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0

        # Verify data integrity
        summary = collector.get_summary()
        assert summary["total_sessions"] == 500  # 5 threads * 100 events

    def test_provider_metric_aggregation(self, temp_dir, config_manager):
        """Test provider metric aggregation in summary."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Add latency metrics
        latencies = [100, 150, 200, 250, 300]
        for latency in latencies:
            collector.record_provider_metric("openai", "latency", latency)

        summary = collector.get_summary()
        provider_summary = summary["provider_summary"]["openai"]["latency"]

        assert provider_summary["count"] == 5
        assert provider_summary["average"] == 200.0
        assert provider_summary["min"] == 100
        assert provider_summary["max"] == 300

    def test_memory_stats_in_summary(self, temp_dir, config_manager):
        """Test that memory stats are included in summary."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Add some data
        for i in range(10):
            collector.record_session_event(f"event_{i}", {"data": "x" * 100})

        summary = collector.get_summary()

        assert "memory_usage" in summary
        assert "session_events_memory_mb" in summary["memory_usage"]
        assert summary["memory_usage"]["session_events_memory_mb"] > 0

    def test_export_format(self, temp_dir, config_manager):
        """Test the format of exported data."""
        collector = MetricsCollector(temp_dir, config_manager)

        # Add various types of data
        collector.record_session_event("test", {"key": "value"})
        collector.record_provider_metric("openai", "latency", 150.0)
        collector.increment_error_count("test_error")
        collector.record_token_usage("openai", 1000, 500, 0.02)

        # Get export data
        export_data = collector.get_export_data()

        assert "session_events" in export_data
        assert "provider_metrics" in export_data
        assert "error_counts" in export_data
        assert "token_usage" in export_data
        assert "daily_stats" in export_data
        assert "summary" in export_data

    def test_cleanup_old_events(self, temp_dir, config_manager):
        """Test cleanup of old events based on max_events setting."""
        config_manager.get_int.side_effect = lambda key, default=0: {
            "observability.metrics.max_events": 5,  # Very low limit
            "observability.metrics.max_memory_mb": 10,
        }.get(key, default)

        collector = MetricsCollector(temp_dir, config_manager)

        # Add more events than the limit
        for i in range(10):
            collector.record_session_event(f"event_{i}", {"index": i})

        # Should only keep the most recent 5
        events = list(collector._session_events)
        assert len(events) == 5
        assert events[0]["data"]["index"] == 5  # Oldest remaining
        assert events[4]["data"]["index"] == 9  # Newest
