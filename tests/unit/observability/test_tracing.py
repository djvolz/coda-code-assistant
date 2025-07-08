"""Unit tests for tracing manager."""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from coda.configuration import ConfigManager
from coda.observability.tracing import Span, TracingManager


class TestSpan:
    """Test the Span class."""

    def test_span_creation(self):
        """Test creating a span."""
        span = Span("test_operation", {"key": "value"})

        assert span.name == "test_operation"
        assert span.attributes == {"key": "value"}
        assert span.start_time > 0
        assert span.end_time is None
        assert span.duration is None
        assert span.status == "in_progress"
        assert span.children == []

    def test_span_end(self):
        """Test ending a span."""
        span = Span("test_operation")
        time.sleep(0.01)  # Small delay to ensure duration > 0

        span.end()

        assert span.end_time is not None
        assert span.duration is not None
        assert span.duration > 0
        assert span.status == "completed"

    def test_span_end_with_status(self):
        """Test ending a span with custom status."""
        span = Span("test_operation")

        span.end(status="error")

        assert span.status == "error"

    def test_span_set_attribute(self):
        """Test setting span attributes."""
        span = Span("test_operation")

        span.set_attribute("key1", "value1")
        span.set_attribute("key2", 42)

        assert span.attributes["key1"] == "value1"
        assert span.attributes["key2"] == 42

    def test_span_add_event(self):
        """Test adding events to span."""
        span = Span("test_operation")

        span.add_event("event1", {"detail": "info"})
        span.add_event("event2")

        assert len(span.events) == 2
        assert span.events[0]["name"] == "event1"
        assert span.events[0]["attributes"] == {"detail": "info"}
        assert span.events[1]["name"] == "event2"
        assert span.events[1]["attributes"] == {}

    def test_span_context_manager(self):
        """Test span as context manager."""
        with Span("test_operation") as span:
            span.set_attribute("key", "value")
            assert span.status == "in_progress"

        assert span.status == "completed"
        assert span.end_time is not None

    def test_span_context_manager_with_exception(self):
        """Test span context manager with exception."""
        span = Span("test_operation")

        try:
            with span:
                raise ValueError("Test error")
        except ValueError:
            pass

        assert span.status == "error"
        assert "error" in span.attributes
        assert "ValueError: Test error" in span.attributes["error"]

    def test_span_to_dict(self):
        """Test converting span to dictionary."""
        span = Span("test_operation", {"initial": "value"})
        span.set_attribute("added", "later")
        span.add_event("test_event")

        child_span = Span("child_operation")
        child_span.end()
        span.children.append(child_span)

        span.end()

        span_dict = span.to_dict()

        assert span_dict["name"] == "test_operation"
        assert span_dict["attributes"]["initial"] == "value"
        assert span_dict["attributes"]["added"] == "later"
        assert len(span_dict["events"]) == 1
        assert len(span_dict["children"]) == 1
        assert span_dict["status"] == "completed"
        assert "duration" in span_dict


class TestTracingManager:
    """Test the TracingManager class."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager."""
        config = Mock(spec=ConfigManager)
        config.get_int.side_effect = lambda key, default=0: {
            "observability.tracing.max_traces": 1000,
            "observability.tracing.max_memory_mb": 10,
            "observability.tracing.sampling_rate": 100,  # 100% sampling
        }.get(key, default)
        return config

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, temp_dir, config_manager):
        """Test TracingManager initialization."""
        manager = TracingManager(temp_dir, config_manager)

        assert manager.base_dir == temp_dir
        assert manager.config_manager == config_manager
        assert hasattr(manager, "_traces")
        assert hasattr(manager, "_active_spans")
        assert manager._sampling_rate == 1.0  # 100% converted to 1.0

    def test_create_span(self, temp_dir, config_manager):
        """Test creating a span."""
        manager = TracingManager(temp_dir, config_manager)

        span = manager.create_span("test_operation", {"attr": "value"})

        assert isinstance(span, Span)
        assert span.name == "test_operation"
        assert span.attributes == {"attr": "value"}
        assert span in manager._active_spans

    def test_end_span(self, temp_dir, config_manager):
        """Test ending a span."""
        manager = TracingManager(temp_dir, config_manager)

        span = manager.create_span("test_operation")
        manager.end_span(span)

        assert span not in manager._active_spans
        assert span.status == "completed"

        # Check span was added to traces
        traces = list(manager._traces)
        assert len(traces) == 1
        assert traces[0] == span

    def test_end_span_with_status(self, temp_dir, config_manager):
        """Test ending a span with custom status."""
        manager = TracingManager(temp_dir, config_manager)

        span = manager.create_span("test_operation")
        manager.end_span(span, status="error")

        assert span.status == "error"

    def test_create_child_span(self, temp_dir, config_manager):
        """Test creating child spans."""
        manager = TracingManager(temp_dir, config_manager)

        parent = manager.create_span("parent_operation")
        child = manager.create_span("child_operation", parent_span=parent)

        assert child in parent.children
        assert child in manager._active_spans

    def test_get_active_spans(self, temp_dir, config_manager):
        """Test getting active spans."""
        manager = TracingManager(temp_dir, config_manager)

        span1 = manager.create_span("operation1")
        span2 = manager.create_span("operation2")

        active = manager.get_active_spans()
        assert len(active) == 2
        assert span1 in active
        assert span2 in active

        manager.end_span(span1)

        active = manager.get_active_spans()
        assert len(active) == 1
        assert span2 in active

    def test_get_recent_traces(self, temp_dir, config_manager):
        """Test getting recent traces."""
        manager = TracingManager(temp_dir, config_manager)

        # Create and end some spans
        for i in range(5):
            span = manager.create_span(f"operation_{i}")
            manager.end_span(span)

        recent = manager.get_recent_traces(limit=3)
        assert len(recent) == 3

        # Should be most recent first
        assert recent[0]["name"] == "operation_4"
        assert recent[1]["name"] == "operation_3"
        assert recent[2]["name"] == "operation_2"

    def test_get_summary(self, temp_dir, config_manager):
        """Test getting tracing summary."""
        manager = TracingManager(temp_dir, config_manager)

        # Create various spans
        for i in range(10):
            span = manager.create_span(f"operation_{i % 3}")
            if i % 4 == 0:
                manager.end_span(span, status="error")
            else:
                manager.end_span(span)

        summary = manager.get_summary()

        assert summary["total_traces"] == 10
        assert summary["active_spans"] == 0
        assert "operation_summary" in summary
        assert "status_summary" in summary
        assert summary["status_summary"]["error"] == 3
        assert summary["status_summary"]["completed"] == 7

    def test_sampling(self, temp_dir, config_manager):
        """Test trace sampling."""
        # Set 50% sampling rate
        config_manager.get_int.side_effect = lambda key, default=0: {
            "observability.tracing.max_traces": 1000,
            "observability.tracing.max_memory_mb": 10,
            "observability.tracing.sampling_rate": 50,
        }.get(key, default)

        manager = TracingManager(temp_dir, config_manager)

        # Create many spans
        created_count = 0
        for i in range(100):
            span = manager.create_span(f"operation_{i}")
            if span is not None:
                created_count += 1
                manager.end_span(span)

        # With 50% sampling, we should have roughly 50 spans
        # Allow for some variance due to randomness
        assert 30 < created_count < 70

    def test_memory_limit(self, temp_dir, config_manager):
        """Test memory limit enforcement."""
        # Set very low memory limit
        config_manager.get_int.side_effect = lambda key, default=0: {
            "observability.tracing.max_traces": 10000,
            "observability.tracing.max_memory_mb": 0.001,  # 1KB
            "observability.tracing.sampling_rate": 100,
        }.get(key, default)

        manager = TracingManager(temp_dir, config_manager)

        # Create spans with large attributes
        for i in range(20):
            span = manager.create_span(f"operation_{i}", {"data": "x" * 500})
            manager.end_span(span)

        # Should have evicted some traces
        stats = manager._traces.get_memory_stats()
        assert stats.items_evicted > 0

    def test_flush_data(self, temp_dir, config_manager):
        """Test flushing trace data."""
        manager = TracingManager(temp_dir, config_manager)

        # Create some traces
        for i in range(3):
            span = manager.create_span(f"operation_{i}")
            manager.end_span(span)

        manager._flush_data()

        # Check data was saved
        traces_file = temp_dir / "traces.json"
        assert traces_file.exists()

        with open(traces_file) as f:
            saved_traces = json.load(f)
        assert len(saved_traces) == 3

    def test_thread_safety(self, temp_dir, config_manager):
        """Test thread safety of tracing operations."""
        import threading

        manager = TracingManager(temp_dir, config_manager)
        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    span = manager.create_span(f"op_{thread_id}_{i}")
                    span.set_attribute("thread", thread_id)
                    time.sleep(0.001)  # Simulate work
                    manager.end_span(span)
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

        # Verify all traces were recorded
        summary = manager.get_summary()
        assert summary["total_traces"] == 250

    def test_span_duration_calculation(self, temp_dir, config_manager):
        """Test span duration calculation accuracy."""
        manager = TracingManager(temp_dir, config_manager)

        span = manager.create_span("test_operation")
        time.sleep(0.1)  # 100ms
        manager.end_span(span)

        # Duration should be approximately 100ms
        assert 0.09 < span.duration < 0.11

    def test_nested_spans(self, temp_dir, config_manager):
        """Test nested span relationships."""
        manager = TracingManager(temp_dir, config_manager)

        # Create nested spans
        root = manager.create_span("root_operation")
        child1 = manager.create_span("child1", parent_span=root)
        child2 = manager.create_span("child2", parent_span=root)
        grandchild = manager.create_span("grandchild", parent_span=child1)

        # End spans in order
        manager.end_span(grandchild)
        manager.end_span(child1)
        manager.end_span(child2)
        manager.end_span(root)

        # Check relationships
        assert len(root.children) == 2
        assert child1 in root.children
        assert child2 in root.children
        assert len(child1.children) == 1
        assert grandchild in child1.children

    def test_export_format(self, temp_dir, config_manager):
        """Test export data format."""
        manager = TracingManager(temp_dir, config_manager)

        # Create a complex trace
        root = manager.create_span("root", {"service": "test"})
        root.add_event("started", {"detail": "info"})

        child = manager.create_span("child", {"operation": "query"}, parent_span=root)
        child.set_attribute("result", "success")
        manager.end_span(child)

        manager.end_span(root)

        export_data = manager.get_export_data()

        assert "traces" in export_data
        assert "summary" in export_data
        assert len(export_data["traces"]) == 1

        exported_trace = export_data["traces"][0]
        assert exported_trace["name"] == "root"
        assert len(exported_trace["children"]) == 1
        assert len(exported_trace["events"]) == 1
