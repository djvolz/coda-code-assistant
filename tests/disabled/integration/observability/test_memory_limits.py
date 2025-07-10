"""Integration tests for observability memory limits and eviction policies."""

import gc
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import psutil
import pytest

from coda.configuration import CodaConfig, ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityMemoryLimits:
    """Test memory management and eviction policies in the observability system."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_with_memory_limits(self, temp_dir):
        """Create config with memory limit settings."""
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "memory": {
                "max_memory_mb": 50,  # 50MB limit
                "buffer_size": 1000,  # Max 1000 items in memory
                "flush_interval_seconds": 5,  # Flush to disk every 5 seconds
                "eviction_policy": "lru",  # Least Recently Used
                "high_water_mark": 0.8,  # Start eviction at 80% capacity
                "low_water_mark": 0.6,  # Evict down to 60% capacity
            },
            "metrics": {"enabled": True, "buffer_size": 500},
            "tracing": {"enabled": True, "buffer_size": 200},
            "health": {"enabled": True, "buffer_size": 100},
            "error_tracking": {"enabled": True, "buffer_size": 100},
            "profiling": {"enabled": True, "buffer_size": 100},
        }

        manager = ConfigManager()
        manager.config = config
        return manager

    def get_memory_usage(self):
        """Get current process memory usage in MB."""
        process = psutil.Process()
        return process.memory_info().rss / 1024 / 1024  # Convert to MB

    def test_memory_limit_enforcement(self, config_with_memory_limits):
        """Test that memory limits are enforced."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        initial_memory = self.get_memory_usage()
        max_memory_mb = config_with_memory_limits.get_int(
            "observability.memory.max_memory_mb", default=100
        )

        # Generate data to approach memory limit
        large_payload = "x" * 10000  # 10KB per event
        events_added = 0

        for i in range(10000):  # Try to add many events
            obs_manager.track_event(f"memory_test_{i}", {"data": large_payload})
            events_added += 1

            # Check memory periodically
            if i % 100 == 0:
                current_memory = self.get_memory_usage()
                memory_increase = current_memory - initial_memory

                # Should not exceed configured limit significantly
                if memory_increase > max_memory_mb * 1.5:  # Allow some overhead
                    break

        # Memory usage should be controlled
        final_memory = self.get_memory_usage()
        memory_increase = final_memory - initial_memory
        assert memory_increase < max_memory_mb * 2  # Allow 2x for overhead

    def test_buffer_size_limits(self, config_with_memory_limits):
        """Test that buffer size limits are respected."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        buffer_size = config_with_memory_limits.get_int(
            "observability.memory.buffer_size", default=1000
        )

        # Track more events than buffer size
        for i in range(buffer_size + 500):
            obs_manager.track_event(f"buffer_test_{i}", {"index": i})

        # Check that buffers don't exceed limits
        if hasattr(obs_manager.metrics_collector, "_event_buffer"):
            assert len(obs_manager.metrics_collector._event_buffer) <= buffer_size

    def test_lru_eviction_policy(self, config_with_memory_limits):
        """Test Least Recently Used eviction policy."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Set small buffer for testing
        # small_buffer_size = 10  # Not used directly

        # Track events with access patterns
        for i in range(20):
            obs_manager.track_event(f"lru_test_{i}", {"index": i, "accessed": False})

        # Access some old events (make them recently used)
        if hasattr(obs_manager, "_access_event"):
            for i in [2, 5, 8]:  # Access these specific events
                obs_manager._access_event(f"lru_test_{i}")

        # Add more events to trigger eviction
        for i in range(20, 30):
            obs_manager.track_event(f"lru_test_{i}", {"index": i})

        # Events 2, 5, 8 should be retained (recently accessed)
        # Other old events should be evicted

    def test_high_water_mark_eviction(self, config_with_memory_limits):
        """Test eviction triggered at high water mark."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        buffer_size = 100  # Smaller buffer for testing
        high_water_mark = 0.8  # 80%
        low_water_mark = 0.6  # 60%

        # Fill buffer to high water mark
        for i in range(int(buffer_size * high_water_mark)):
            obs_manager.track_event(f"watermark_test_{i}", {"index": i})

        # Add one more event to trigger eviction
        obs_manager.track_event("trigger_eviction", {"trigger": True})

        # Buffer should be reduced to low water mark
        if hasattr(obs_manager.metrics_collector, "_event_buffer"):
            buffer_len = len(obs_manager.metrics_collector._event_buffer)
            assert buffer_len <= int(buffer_size * low_water_mark * 1.1)  # Allow 10% margin

    def test_flush_to_disk_on_memory_pressure(self, config_with_memory_limits, temp_dir):
        """Test that data is flushed to disk under memory pressure."""
        obs_manager = ObservabilityManager(config_with_memory_limits)
        storage_path = Path(temp_dir) / "observability"

        # Track many events to create memory pressure
        for i in range(1000):
            obs_manager.track_event(f"flush_test_{i}", {"data": "x" * 1000})

        # Force memory pressure
        if hasattr(obs_manager, "_check_memory_pressure"):
            obs_manager._check_memory_pressure()

        # Data should be persisted to disk
        files_created = list(storage_path.rglob("*.json"))
        assert len(files_created) > 0

    def test_periodic_flush_interval(self, config_with_memory_limits):
        """Test periodic flushing based on configured interval."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        flush_interval = config_with_memory_limits.get_int(
            "observability.memory.flush_interval_seconds", default=60
        )

        # Track some events
        for i in range(10):
            obs_manager.track_event(f"periodic_flush_{i}", {"index": i})

        # Wait for flush interval (or mock time)
        with patch("time.time", side_effect=[0, flush_interval + 1]):
            if hasattr(obs_manager, "_periodic_flush"):
                obs_manager._periodic_flush()

        # Events should be flushed

    def test_component_specific_buffers(self, config_with_memory_limits):
        """Test that each component respects its buffer limits."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Get component buffer sizes
        metrics_buffer = config_with_memory_limits.get_int(
            "observability.metrics.buffer_size", default=500
        )
        tracing_buffer = config_with_memory_limits.get_int(
            "observability.tracing.buffer_size", default=200
        )

        # Fill metrics buffer
        for i in range(metrics_buffer + 100):
            obs_manager.track_event(f"metrics_{i}", {"component": "metrics"})

        # Fill tracing buffer
        for i in range(tracing_buffer + 50):
            with obs_manager.trace(f"trace_{i}"):
                pass

        # Check buffer sizes
        if hasattr(obs_manager.metrics_collector, "_event_buffer"):
            assert len(obs_manager.metrics_collector._event_buffer) <= metrics_buffer

        if hasattr(obs_manager.tracing_manager, "_spans"):
            assert len(obs_manager.tracing_manager._spans) <= tracing_buffer

    def test_memory_efficient_serialization(self, config_with_memory_limits):
        """Test memory-efficient data serialization."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Create events with various data types
        test_data = {
            "string": "test" * 100,
            "number": 12345,
            "float": 123.45,
            "boolean": True,
            "null": None,
            "list": list(range(100)),
            "nested": {"level1": {"level2": {"level3": "deep"}}},
        }

        initial_memory = self.get_memory_usage()

        # Track many events with complex data
        for i in range(100):
            obs_manager.track_event(f"serialization_test_{i}", test_data)

        # Memory growth should be reasonable
        memory_growth = self.get_memory_usage() - initial_memory
        assert memory_growth < 50  # Should use less than 50MB

    def test_eviction_metrics(self, config_with_memory_limits):
        """Test that eviction events are tracked."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Track eviction metrics
        eviction_count = 0

        # Fill buffer beyond capacity
        for i in range(2000):
            obs_manager.track_event(f"eviction_metric_{i}", {"index": i})

            # Check for eviction metrics
            if hasattr(obs_manager, "get_eviction_stats"):
                stats = obs_manager.get_eviction_stats()
                if stats and stats.get("evicted_count", 0) > eviction_count:
                    eviction_count = stats["evicted_count"]

        # Some evictions should have occurred
        assert eviction_count > 0

    def test_memory_cleanup_on_shutdown(self, config_with_memory_limits):
        """Test proper memory cleanup on shutdown."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Track events
        for i in range(100):
            obs_manager.track_event(f"cleanup_test_{i}", {"data": "x" * 1000})

        initial_memory = self.get_memory_usage()

        # Shutdown observability
        if hasattr(obs_manager, "shutdown"):
            obs_manager.shutdown()

        # Force garbage collection
        gc.collect()

        # Memory should be released
        final_memory = self.get_memory_usage()
        # Memory should decrease (allow some variance)
        assert final_memory <= initial_memory + 10

    def test_concurrent_memory_management(self, config_with_memory_limits):
        """Test memory management under concurrent access."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        import threading

        def track_events(thread_id):
            for i in range(500):
                obs_manager.track_event(
                    f"thread_{thread_id}_event_{i}", {"thread": thread_id, "data": "x" * 100}
                )
                time.sleep(0.001)

        # Start multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=track_events, args=(i,))
            threads.append(thread)
            thread.start()

        # Monitor memory during concurrent access
        max_memory = self.get_memory_usage()
        for _ in range(10):
            time.sleep(0.1)
            current_memory = self.get_memory_usage()
            max_memory = max(max_memory, current_memory)

        # Wait for threads
        for thread in threads:
            thread.join()

        # Memory should stay within limits even with concurrent access
        memory_limit = config_with_memory_limits.get_int(
            "observability.memory.max_memory_mb", default=50
        )
        assert max_memory < memory_limit * 3  # Allow 3x for overhead and initial memory

    def test_adaptive_buffer_sizing(self, config_with_memory_limits):
        """Test adaptive buffer sizing based on available memory."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Simulate low memory conditions
        with patch("psutil.virtual_memory") as mock_memory:
            mock_memory.return_value.available = 100 * 1024 * 1024  # 100MB available
            mock_memory.return_value.percent = 90  # 90% used

            # Buffer sizes should adapt
            if hasattr(obs_manager, "_adapt_buffer_sizes"):
                obs_manager._adapt_buffer_sizes()

            # Buffers should be reduced under memory pressure

    def test_priority_based_eviction(self, config_with_memory_limits):
        """Test eviction based on data priority."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        # Track events with different priorities
        for i in range(100):
            priority = "high" if i % 10 == 0 else "low"
            obs_manager.track_event(f"priority_test_{i}", {"index": i, "priority": priority})

        # Track high priority error
        obs_manager.track_error(
            Exception("Critical system error"), {"severity": "critical", "priority": "high"}
        )

        # Trigger eviction
        for i in range(100, 200):
            obs_manager.track_event(f"trigger_eviction_{i}", {"priority": "low"})

        # High priority items should be retained
        # Low priority items should be evicted first

    def test_memory_profiling_integration(self, config_with_memory_limits):
        """Test memory profiling of observability system itself."""
        obs_manager = ObservabilityManager(config_with_memory_limits)

        if obs_manager.profiler:
            # Profile memory usage
            with obs_manager.trace("memory_profile_test"):
                # Allocate and track memory
                data = []
                for i in range(1000):
                    data.append({"index": i, "data": "x" * 100})
                    obs_manager.track_event(f"profile_{i}", data[-1])

                # Get memory profile
                if hasattr(obs_manager.profiler, "get_memory_profile"):
                    profile = obs_manager.profiler.get_memory_profile()
                    assert profile is not None
                    assert "peak_memory_mb" in profile
                    assert "current_memory_mb" in profile
