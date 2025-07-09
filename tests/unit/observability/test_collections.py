"""Unit tests for memory-aware collections."""

import time

from coda.observability.collections import BoundedCache, MemoryAwareDeque, MemoryStats


class TestMemoryAwareDeque:
    """Test the MemoryAwareDeque class."""

    def test_basic_append(self):
        """Test basic append operations."""
        deque = MemoryAwareDeque(maxlen=10, max_memory_mb=10.0)

        for i in range(5):
            deque.append({"id": i, "data": "test"})

        assert len(deque) == 5
        assert list(deque) == [{"id": i, "data": "test"} for i in range(5)]

    def test_maxlen_enforcement(self):
        """Test that maxlen is enforced."""
        deque = MemoryAwareDeque(maxlen=3, max_memory_mb=10.0)

        for i in range(5):
            deque.append({"id": i})

        assert len(deque) == 3
        # Should contain the last 3 items
        assert list(deque) == [{"id": 2}, {"id": 3}, {"id": 4}]

    def test_memory_limit_enforcement(self):
        """Test that memory limits are enforced."""
        # Set a very small memory limit
        deque = MemoryAwareDeque(maxlen=1000, max_memory_mb=0.001)  # 1KB

        # Add items that will exceed memory limit
        large_data = "x" * 1000  # ~1KB per item
        for i in range(10):
            deque.append({"id": i, "data": large_data})

        # Should have evicted items to stay under memory limit
        assert len(deque) < 10

        stats = deque.get_memory_stats()
        assert stats.items_evicted > 0
        assert stats.memory_used_mb <= 0.001

    def test_extend(self):
        """Test extend method."""
        deque = MemoryAwareDeque(maxlen=10, max_memory_mb=10.0)

        items = [{"id": i} for i in range(5)]
        deque.extend(items)

        assert len(deque) == 5
        assert list(deque) == items

    def test_extend_with_memory_limit(self):
        """Test extend with memory limit."""
        deque = MemoryAwareDeque(maxlen=100, max_memory_mb=0.001)

        large_items = [{"data": "x" * 1000} for _ in range(10)]
        deque.extend(large_items)

        # Should have limited items due to memory
        assert len(deque) < 10

    def test_clear(self):
        """Test clear method."""
        deque = MemoryAwareDeque(maxlen=10, max_memory_mb=10.0)

        deque.extend([{"id": i} for i in range(5)])
        assert len(deque) == 5

        deque.clear()
        assert len(deque) == 0

        stats = deque.get_memory_stats()
        assert stats.memory_used_mb == 0

    def test_memory_stats(self):
        """Test memory statistics."""
        deque = MemoryAwareDeque(maxlen=5, max_memory_mb=10.0)

        # Add items that will cause eviction
        for i in range(10):
            deque.append({"id": i})

        stats = deque.get_memory_stats()
        assert isinstance(stats, MemoryStats)
        assert stats.items_count == 5
        assert stats.items_evicted == 5
        assert stats.memory_used_mb > 0
        assert stats.memory_limit_mb == 10.0
        assert 0 <= stats.memory_usage_percent <= 100

    def test_thread_safety(self):
        """Test basic thread safety."""
        import threading

        deque = MemoryAwareDeque(maxlen=1000, max_memory_mb=10.0)
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    deque.append({"thread": thread_id, "item": i})
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
        assert len(deque) <= 1000

    def test_memory_calculation_accuracy(self):
        """Test that memory calculation is reasonably accurate."""
        deque = MemoryAwareDeque(maxlen=100, max_memory_mb=10.0)

        # Add items with known size
        item = {"data": "x" * 1000}  # Approximately 1KB
        for _ in range(10):
            deque.append(item)

        stats = deque.get_memory_stats()
        # Memory usage should be roughly 10KB (0.01MB)
        assert 0.005 < stats.memory_used_mb < 0.02

    def test_eviction_callback(self):
        """Test that eviction tracking works."""
        deque = MemoryAwareDeque(maxlen=3, max_memory_mb=10.0)

        for i in range(5):
            deque.append({"id": i})

        stats = deque.get_memory_stats()
        assert stats.items_evicted == 2


class TestBoundedCache:
    """Test the BoundedCache class."""

    def test_basic_put_get(self):
        """Test basic put and get operations."""
        cache = BoundedCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key2", {"data": "value2"})

        assert cache.get("key1") == "value1"
        assert cache.get("key2") == {"data": "value2"}
        assert cache.get("nonexistent") is None

    def test_max_size_enforcement(self):
        """Test that max_size is enforced."""
        cache = BoundedCache(max_size=3, ttl_seconds=60)

        # Add more items than max_size
        for i in range(5):
            cache.put(f"key{i}", f"value{i}")

        stats = cache.get_stats()
        assert stats["size"] == 3

        # First two items should be evicted (LRU)
        assert cache.get("key0") is None
        assert cache.get("key1") is None
        assert cache.get("key4") == "value4"

    def test_ttl_expiration(self):
        """Test TTL expiration."""
        cache = BoundedCache(max_size=10, ttl_seconds=0.1)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        # Wait for expiration
        time.sleep(0.2)

        assert cache.get("key1") is None

    def test_memory_limit_enforcement(self):
        """Test memory limit enforcement."""
        cache = BoundedCache(max_size=100, ttl_seconds=60, max_memory_mb=0.001)

        # Add large items
        large_value = "x" * 1000
        for i in range(10):
            cache.put(f"key{i}", large_value)

        stats = cache.get_stats()
        assert stats["size"] < 10  # Should have evicted some items

    def test_delete(self):
        """Test delete operation."""
        cache = BoundedCache(max_size=10, ttl_seconds=60)

        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

        cache.delete("key1")
        assert cache.get("key1") is None

    def test_clear(self):
        """Test clear operation."""
        cache = BoundedCache(max_size=10, ttl_seconds=60)

        for i in range(5):
            cache.put(f"key{i}", f"value{i}")

        assert cache.get_stats()["size"] == 5

        cache.clear()
        assert cache.get_stats()["size"] == 0

    def test_get_stats(self):
        """Test cache statistics."""
        cache = BoundedCache(max_size=5, ttl_seconds=60)

        # Generate some cache activity
        for i in range(10):
            cache.put(f"key{i}", f"value{i}")

        # Generate hits and misses
        cache.get("key7")  # hit
        cache.get("key8")  # hit
        cache.get("key0")  # miss (evicted)
        cache.get("nonexistent")  # miss

        stats = cache.get_stats()
        assert isinstance(stats, dict)
        assert stats["size"] == 5
        assert stats["hits"] == 2
        assert stats["misses"] == 2
        assert stats["evictions"] > 0
        assert 0 <= stats["hit_rate"] <= 1

    def test_lru_behavior(self):
        """Test LRU eviction behavior."""
        cache = BoundedCache(max_size=3, ttl_seconds=60)

        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)

        # Access 'a' to make it recently used
        cache.get("a")

        # Add new item, 'b' should be evicted (least recently used)
        cache.put("d", 4)

        assert cache.get("a") == 1  # Still present
        assert cache.get("b") is None  # Evicted
        assert cache.get("c") == 3  # Still present
        assert cache.get("d") == 4  # Newly added

    def test_update_existing_key(self):
        """Test updating existing key."""
        cache = BoundedCache(max_size=3, ttl_seconds=60)

        cache.put("key1", "value1")
        cache.put("key1", "value2")

        assert cache.get("key1") == "value2"
        assert cache.get_stats()["size"] == 1

    def test_none_values(self):
        """Test handling of None values."""
        cache = BoundedCache(max_size=10, ttl_seconds=60)

        cache.put("key1", None)
        # get returns None for both missing keys and None values
        # This is expected behavior
        assert cache.get("key1") is None
        assert cache.get("nonexistent") is None

    def test_thread_safety(self):
        """Test basic thread safety."""
        import threading

        cache = BoundedCache(max_size=100, ttl_seconds=60)
        errors = []

        def worker(thread_id):
            try:
                for i in range(50):
                    key = f"thread_{thread_id}_item_{i}"
                    cache.put(key, {"thread": thread_id, "item": i})
                    value = cache.get(key)
                    if value and value["thread"] != thread_id:
                        errors.append(f"Data corruption in thread {thread_id}")
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

    def test_memory_stats_in_cache_stats(self):
        """Test that memory stats are included in cache stats."""
        cache = BoundedCache(max_size=10, ttl_seconds=60, max_memory_mb=10.0)

        cache.put("key1", {"data": "x" * 1000})

        stats = cache.get_stats()
        assert "memory_used_mb" in stats
        assert stats["memory_used_mb"] > 0
