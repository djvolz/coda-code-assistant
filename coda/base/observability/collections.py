"""Memory-aware collections for observability data.

This module provides memory-bounded data structures to prevent
unbounded growth in observability components.
"""

import gc
import logging
import sys
import threading
import weakref
from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def get_size_of(obj: Any, seen: set | None = None) -> int:
    """Calculate the approximate memory size of an object in bytes.

    This recursively calculates size for containers, but has a depth limit
    to avoid infinite recursion.
    """
    if seen is None:
        seen = set()

    obj_id = id(obj)
    if obj_id in seen:
        return 0

    seen.add(obj_id)
    size = sys.getsizeof(obj)

    # Handle containers
    if isinstance(obj, dict):
        for key, value in obj.items():
            size += get_size_of(key, seen)
            size += get_size_of(value, seen)
    elif isinstance(obj, list | tuple | set | frozenset):
        for item in obj:
            size += get_size_of(item, seen)
    elif hasattr(obj, "__dict__"):
        size += get_size_of(obj.__dict__, seen)

    return size


@dataclass
class MemoryStats:
    """Memory usage statistics."""

    current_size_bytes: int
    max_size_bytes: int
    items_count: int
    items_evicted: int

    @property
    def usage_percentage(self) -> float:
        """Get memory usage as percentage of max."""
        if self.max_size_bytes == 0:
            return 0.0
        return (self.current_size_bytes / self.max_size_bytes) * 100


class MemoryAwareDeque(Generic[T]):
    """Memory-aware deque that monitors and limits memory usage."""

    def __init__(
        self,
        maxlen: int,
        max_memory_mb: float = 100.0,
        eviction_callback: Callable[[T], None] | None = None,
    ):
        """Initialize memory-aware deque.

        Args:
            maxlen: Maximum number of items
            max_memory_mb: Maximum memory usage in megabytes
            eviction_callback: Optional callback when items are evicted
        """
        self.deque = deque(maxlen=maxlen)
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.eviction_callback = eviction_callback

        # Track sizes of items for efficiency
        self._item_sizes: deque[int] = deque(maxlen=maxlen)
        self._current_size = 0
        self._items_evicted = 0
        self._lock = threading.RLock()

        # Periodic memory pressure check
        self._memory_pressure_threshold = 0.9  # 90% of max

    def append(self, item: T) -> None:
        """Append item with memory check."""
        with self._lock:
            item_size = get_size_of(item)

            # Check if we need to make room
            while self._current_size + item_size > self.max_memory_bytes and len(self.deque) > 0:
                self._evict_oldest()

            # Check if item is too large by itself
            if item_size > self.max_memory_bytes:
                logger.warning(
                    f"Item size ({item_size / 1024 / 1024:.2f}MB) exceeds "
                    f"max memory limit ({self.max_memory_bytes / 1024 / 1024:.2f}MB)"
                )
                return

            # Add item
            if len(self.deque) >= self.deque.maxlen:
                # Will evict oldest due to maxlen
                if len(self._item_sizes) > 0:
                    evicted_size = self._item_sizes[0]
                    self._current_size -= evicted_size
                    self._items_evicted += 1

            self.deque.append(item)
            self._item_sizes.append(item_size)
            self._current_size += item_size

    def appendleft(self, item: T) -> None:
        """Append item to the left with memory check."""
        with self._lock:
            item_size = get_size_of(item)

            # Check if we need to make room
            while self._current_size + item_size > self.max_memory_bytes and len(self.deque) > 0:
                self._evict_newest()

            # Check if item is too large by itself
            if item_size > self.max_memory_bytes:
                logger.warning(
                    f"Item size ({item_size / 1024 / 1024:.2f}MB) exceeds "
                    f"max memory limit ({self.max_memory_bytes / 1024 / 1024:.2f}MB)"
                )
                return

            # Add item
            if len(self.deque) >= self.deque.maxlen:
                # Will evict newest due to maxlen
                if len(self._item_sizes) > 0:
                    evicted_size = self._item_sizes[-1]
                    self._current_size -= evicted_size
                    self._items_evicted += 1

            self.deque.appendleft(item)
            self._item_sizes.appendleft(item_size)
            self._current_size += item_size

    def _evict_oldest(self) -> None:
        """Evict the oldest item."""
        if not self.deque:
            return

        evicted = self.deque.popleft()
        if self._item_sizes:
            evicted_size = self._item_sizes.popleft()
            self._current_size -= evicted_size
            self._items_evicted += 1

        if self.eviction_callback:
            try:
                self.eviction_callback(evicted)
            except Exception as e:
                logger.error(f"Error in eviction callback: {e}")

    def _evict_newest(self) -> None:
        """Evict the newest item."""
        if not self.deque:
            return

        evicted = self.deque.pop()
        if self._item_sizes:
            evicted_size = self._item_sizes.pop()
            self._current_size -= evicted_size
            self._items_evicted += 1

        if self.eviction_callback:
            try:
                self.eviction_callback(evicted)
            except Exception as e:
                logger.error(f"Error in eviction callback: {e}")

    def clear(self) -> None:
        """Clear the deque and reset memory tracking."""
        with self._lock:
            self.deque.clear()
            self._item_sizes.clear()
            self._current_size = 0

    def get_memory_stats(self) -> MemoryStats:
        """Get current memory statistics."""
        with self._lock:
            return MemoryStats(
                current_size_bytes=self._current_size,
                max_size_bytes=self.max_memory_bytes,
                items_count=len(self.deque),
                items_evicted=self._items_evicted,
            )

    def is_memory_pressure_high(self) -> bool:
        """Check if memory pressure is high."""
        with self._lock:
            if self.max_memory_bytes == 0:
                return False
            usage_ratio = self._current_size / self.max_memory_bytes
            return usage_ratio >= self._memory_pressure_threshold

    def compact(self) -> None:
        """Compact memory by forcing garbage collection if needed."""
        if self.is_memory_pressure_high():
            gc.collect()

    def __len__(self) -> int:
        """Get number of items."""
        return len(self.deque)

    def __iter__(self):
        """Iterate over items."""
        return iter(self.deque)

    def __getitem__(self, index):
        """Get item by index."""
        return self.deque[index]


class BoundedCache(Generic[T]):
    """Memory and time bounded cache using weak references."""

    def __init__(
        self, max_size: int = 1000, max_memory_mb: float = 50.0, ttl_seconds: float | None = None
    ):
        """Initialize bounded cache.

        Args:
            max_size: Maximum number of items to cache
            max_memory_mb: Maximum memory usage in megabytes
            ttl_seconds: Time to live for cache entries (None = no expiry)
        """
        self.max_size = max_size
        self.max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self.ttl_seconds = ttl_seconds

        # Use OrderedDict to maintain insertion order for LRU
        from collections import OrderedDict

        self._cache: OrderedDict[str, weakref.ref] = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self._sizes: dict[str, int] = {}
        self._current_size = 0
        self._lock = threading.RLock()

        # Stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str, default: T | None = None) -> T | None:
        """Get item from cache."""
        import time

        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default

            # Check if expired
            if self.ttl_seconds and key in self._timestamps:
                if time.time() - self._timestamps[key] > self.ttl_seconds:
                    self._remove(key)
                    self._misses += 1
                    return default

            # Get weak reference
            ref = self._cache[key]
            value = ref()

            if value is None:
                # Object was garbage collected
                self._remove(key)
                self._misses += 1
                return default

            # Move to end for LRU
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def put(self, key: str, value: T) -> None:
        """Put item in cache."""
        import time

        with self._lock:
            # Remove old value if exists
            if key in self._cache:
                self._remove(key)

            # Calculate size
            size = get_size_of(value)

            # Check if item is too large
            if size > self.max_memory_bytes:
                logger.warning(
                    f"Item size ({size / 1024 / 1024:.2f}MB) exceeds "
                    f"cache limit ({self.max_memory_bytes / 1024 / 1024:.2f}MB)"
                )
                return

            # Evict items if necessary
            while (
                self._current_size + size > self.max_memory_bytes
                or len(self._cache) >= self.max_size
            ) and self._cache:
                self._evict_lru()

            # Add to cache
            self._cache[key] = weakref.ref(value)
            self._sizes[key] = size
            self._current_size += size

            if self.ttl_seconds:
                self._timestamps[key] = time.time()

    def _remove(self, key: str) -> None:
        """Remove item from cache."""
        if key in self._cache:
            del self._cache[key]

        if key in self._sizes:
            self._current_size -= self._sizes[key]
            del self._sizes[key]

        if key in self._timestamps:
            del self._timestamps[key]

    def _evict_lru(self) -> None:
        """Evict least recently used item."""
        if not self._cache:
            return

        # Get oldest key (first in OrderedDict)
        key = next(iter(self._cache))
        self._remove(key)
        self._evictions += 1

    def clear(self) -> None:
        """Clear the cache."""
        with self._lock:
            self._cache.clear()
            self._timestamps.clear()
            self._sizes.clear()
            self._current_size = 0

    def get_stats(self) -> dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests if total_requests > 0 else 0.0

            return {
                "size": len(self._cache),
                "memory_bytes": self._current_size,
                "memory_mb": self._current_size / 1024 / 1024,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": hit_rate,
            }
