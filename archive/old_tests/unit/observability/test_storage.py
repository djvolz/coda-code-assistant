"""Unit tests for storage backends."""

import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.observability.storage import (
    BatchWriter,
    FileStorageBackend,
    MemoryStorageBackend,
    StorageBackend,
)


class StorageError(Exception):
    """Storage error used in tests."""

    pass


class TestStorageBackend:
    """Test the abstract StorageBackend class."""

    def test_abstract_class_cannot_be_instantiated(self):
        """Test that StorageBackend cannot be instantiated directly."""
        with pytest.raises(TypeError):
            StorageBackend()


class TestFileStorageBackend:
    """Test the FileStorageBackend class."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, temp_dir):
        """Test FileStorageBackend initialization."""
        storage = FileStorageBackend(temp_dir)
        assert storage.base_dir == temp_dir

    def test_save_and_load(self, temp_dir):
        """Test saving and loading data."""
        storage = FileStorageBackend(temp_dir)
        test_data = {"key": "value", "number": 42, "list": [1, 2, 3]}

        storage.save("test_key", test_data)
        loaded_data = storage.load("test_key")

        assert loaded_data == test_data

    def test_load_nonexistent_key(self, temp_dir):
        """Test loading a key that doesn't exist."""
        storage = FileStorageBackend(temp_dir)
        result = storage.load("nonexistent")

        assert result is None

    def test_delete(self, temp_dir):
        """Test deleting a key."""
        storage = FileStorageBackend(temp_dir)
        test_data = {"data": "to_delete"}

        storage.save("delete_me", test_data)
        assert storage.load("delete_me") == test_data

        storage.delete("delete_me")
        assert storage.load("delete_me") is None

    def test_delete_nonexistent(self, temp_dir):
        """Test deleting a key that doesn't exist."""
        storage = FileStorageBackend(temp_dir)
        # Should not raise an error
        storage.delete("nonexistent")

    def test_exists(self, temp_dir):
        """Test checking if a key exists."""
        storage = FileStorageBackend(temp_dir)

        assert not storage.exists("test_key")

        storage.save("test_key", {"data": "value"})
        assert storage.exists("test_key")

    def test_list_keys(self, temp_dir):
        """Test listing all keys."""
        storage = FileStorageBackend(temp_dir)

        # Save multiple items
        storage.save("key1", {"id": 1})
        storage.save("key2", {"id": 2})
        storage.save("key3", {"id": 3})

        keys = storage.list_keys()
        assert set(keys) == {"key1", "key2", "key3"}

    def test_list_keys_with_prefix(self, temp_dir):
        """Test listing keys with a prefix."""
        storage = FileStorageBackend(temp_dir)

        storage.save("metrics_1", {"type": "metrics"})
        storage.save("metrics_2", {"type": "metrics"})
        storage.save("traces_1", {"type": "traces"})

        metrics_keys = storage.list_keys(prefix="metrics")
        assert set(metrics_keys) == {"metrics_1", "metrics_2"}

    def test_clear(self, temp_dir):
        """Test clearing all data."""
        storage = FileStorageBackend(temp_dir)

        storage.save("key1", {"id": 1})
        storage.save("key2", {"id": 2})
        assert len(storage.list_keys()) == 2

        storage.clear()
        assert len(storage.list_keys()) == 0

    def test_size(self, temp_dir):
        """Test getting storage size."""
        storage = FileStorageBackend(temp_dir)

        assert storage.size() == 0

        storage.save("key1", {"data": "x" * 1000})
        storage.save("key2", {"data": "y" * 1000})

        size = storage.size()
        assert size > 0

    def test_invalid_json_handling(self, temp_dir):
        """Test handling of corrupted JSON files."""
        storage = FileStorageBackend(temp_dir)

        # Create a corrupted JSON file
        bad_file = temp_dir / "bad_key.json"
        bad_file.write_text("not valid json")

        result = storage.load("bad_key")
        assert result is None

    def test_unicode_handling(self, temp_dir):
        """Test handling of unicode data."""
        storage = FileStorageBackend(temp_dir)
        test_data = {"emoji": "🚀", "chinese": "你好", "arabic": "مرحبا"}

        storage.save("unicode_test", test_data)
        loaded = storage.load("unicode_test")

        assert loaded == test_data

    @patch("pathlib.Path.write_text")
    def test_save_error_handling(self, mock_write, temp_dir):
        """Test error handling during save."""
        mock_write.side_effect = OSError("Disk full")
        storage = FileStorageBackend(temp_dir)

        with pytest.raises(StorageError):
            storage.save("test", {"data": "value"})


class TestMemoryStorageBackend:
    """Test the MemoryStorageBackend class."""

    def test_save_and_load(self):
        """Test saving and loading data in memory."""
        storage = MemoryStorageBackend()
        test_data = {"key": "value", "number": 42}

        storage.save("test_key", test_data)
        loaded_data = storage.load("test_key")

        assert loaded_data == test_data

    def test_load_nonexistent(self):
        """Test loading a nonexistent key."""
        storage = MemoryStorageBackend()
        assert storage.load("nonexistent") is None

    def test_delete(self):
        """Test deleting a key."""
        storage = MemoryStorageBackend()

        storage.save("delete_me", {"data": "value"})
        assert storage.exists("delete_me")

        storage.delete("delete_me")
        assert not storage.exists("delete_me")

    def test_exists(self):
        """Test checking existence."""
        storage = MemoryStorageBackend()

        assert not storage.exists("key")
        storage.save("key", {"data": "value"})
        assert storage.exists("key")

    def test_list_keys(self):
        """Test listing keys."""
        storage = MemoryStorageBackend()

        storage.save("a", {})
        storage.save("b", {})
        storage.save("c", {})

        keys = storage.list_keys()
        assert set(keys) == {"a", "b", "c"}

    def test_list_keys_with_prefix(self):
        """Test listing keys with prefix."""
        storage = MemoryStorageBackend()

        storage.save("test_1", {})
        storage.save("test_2", {})
        storage.save("other_1", {})

        test_keys = storage.list_keys(prefix="test")
        assert set(test_keys) == {"test_1", "test_2"}

    def test_clear(self):
        """Test clearing all data."""
        storage = MemoryStorageBackend()

        storage.save("a", {})
        storage.save("b", {})
        assert len(storage.list_keys()) == 2

        storage.clear()
        assert len(storage.list_keys()) == 0

    def test_size(self):
        """Test size calculation."""
        storage = MemoryStorageBackend()

        assert storage.size() == 0

        storage.save("key", {"data": "value"})
        assert storage.size() > 0

    def test_thread_safety(self):
        """Test basic thread safety of operations."""
        import threading

        storage = MemoryStorageBackend()
        errors = []

        def worker(thread_id):
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_item_{i}"
                    storage.save(key, {"thread": thread_id, "item": i})
                    loaded = storage.load(key)
                    assert loaded["thread"] == thread_id
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
        assert len(storage.list_keys()) == 500


class TestBatchWriter:
    """Test the BatchWriter class."""

    def test_basic_batching(self):
        """Test basic batch writing."""
        backend = MemoryStorageBackend()
        writer = BatchWriter(backend, batch_size=3)

        # Write less than batch size
        writer.write("key1", {"id": 1})
        writer.write("key2", {"id": 2})

        # Data should not be written yet
        assert not backend.exists("key1")
        assert not backend.exists("key2")

        # Write one more to trigger batch
        writer.write("key3", {"id": 3})

        # All data should be written
        assert backend.exists("key1")
        assert backend.exists("key2")
        assert backend.exists("key3")

    def test_flush_on_close(self):
        """Test that remaining data is flushed on close."""
        backend = MemoryStorageBackend()
        writer = BatchWriter(backend, batch_size=10)

        writer.write("key1", {"id": 1})
        writer.write("key2", {"id": 2})

        assert not backend.exists("key1")

        writer.close()

        assert backend.exists("key1")
        assert backend.exists("key2")

    def test_time_based_flush(self):
        """Test time-based flushing."""
        backend = MemoryStorageBackend()
        writer = BatchWriter(backend, batch_size=100, flush_interval=0.1)

        writer.write("key1", {"id": 1})
        assert not backend.exists("key1")

        # Wait for time-based flush
        time.sleep(0.2)

        # Force a write to trigger the time check
        writer.write("key2", {"id": 2})

        # Both should be written
        assert backend.exists("key1")
        assert backend.exists("key2")

    def test_multiple_batches(self):
        """Test writing multiple batches."""
        backend = MemoryStorageBackend()
        writer = BatchWriter(backend, batch_size=2)

        for i in range(6):
            writer.write(f"key{i}", {"id": i})

        writer.close()

        # All items should be written
        assert len(backend.list_keys()) == 6

    def test_error_handling(self):
        """Test error handling during batch write."""
        backend = Mock(spec=StorageBackend)
        backend.save.side_effect = StorageError("Write failed")

        writer = BatchWriter(backend, batch_size=2)

        # These writes should not raise immediately
        writer.write("key1", {"id": 1})
        writer.write("key2", {"id": 2})  # This triggers batch write

        # The error should be logged but not raised
        writer.close()
