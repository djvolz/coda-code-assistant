"""Storage abstraction layer for observability components.

This module provides a unified interface for storing and retrieving
observability data with support for different backends.
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Any, Protocol

logger = logging.getLogger(__name__)


class StorageBackend(Protocol):
    """Protocol for storage backends."""

    def save(self, key: str, data: dict[str, Any]) -> None:
        """Save data with the given key."""
        ...

    def load(self, key: str) -> dict[str, Any] | None:
        """Load data for the given key."""
        ...

    def exists(self, key: str) -> bool:
        """Check if data exists for the given key."""
        ...

    def delete(self, key: str) -> None:
        """Delete data for the given key."""
        ...

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys, optionally filtered by prefix."""
        ...


class FileStorageBackend:
    """File-based storage implementation with atomic writes."""

    def __init__(self, base_path: Path):
        """Initialize file storage backend.

        Args:
            base_path: Base directory for storing files
        """
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, key: str) -> Path:
        """Get the file path for a given key."""
        # Sanitize key to prevent path traversal
        safe_key = key.replace("..", "").replace("/", "_").replace("\\", "_")
        return self.base_path / f"{safe_key}.json"

    def save(self, key: str, data: dict[str, Any]) -> None:
        """Save data with atomic write operation."""
        file_path = self._get_file_path(key)

        # Create temp file in same directory for atomic rename
        fd, temp_path = tempfile.mkstemp(dir=self.base_path, suffix=".tmp")

        try:
            # Write data to temp file
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
                f.flush()
                os.fsync(f.fileno())

            # Set secure permissions (owner read/write only)
            os.chmod(temp_path, 0o600)

            # Atomic rename
            os.replace(temp_path, file_path)

        except Exception as e:
            # Clean up temp file on error
            try:
                os.unlink(temp_path)
            except OSError:
                pass
            raise e

    def load(self, key: str) -> dict[str, Any] | None:
        """Load data from file."""
        file_path = self._get_file_path(key)

        if not file_path.exists():
            return None

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load data for key '{key}': {e}")
            return None

    def exists(self, key: str) -> bool:
        """Check if file exists for the given key."""
        return self._get_file_path(key).exists()

    def delete(self, key: str) -> None:
        """Delete file for the given key."""
        file_path = self._get_file_path(key)
        if file_path.exists():
            file_path.unlink()

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys in storage."""
        keys = []

        for file_path in self.base_path.glob("*.json"):
            key = file_path.stem
            if prefix is None or key.startswith(prefix):
                keys.append(key)

        return sorted(keys)

    def clear(self) -> None:
        """Clear all stored data."""
        for file_path in self.base_path.glob("*.json"):
            try:
                file_path.unlink()
            except Exception as e:
                logger.error(f"Failed to delete file {file_path}: {e}")

    def size(self) -> int:
        """Get total size of stored data in bytes."""
        total_size = 0
        for file_path in self.base_path.glob("*.json"):
            try:
                total_size += file_path.stat().st_size
            except Exception as e:
                logger.error(f"Failed to get size of file {file_path}: {e}")
        return total_size


class MemoryStorageBackend:
    """In-memory storage implementation for testing."""

    def __init__(self):
        """Initialize memory storage backend."""
        self.data: dict[str, dict[str, Any]] = {}

    def save(self, key: str, data: dict[str, Any]) -> None:
        """Save data in memory."""
        # Deep copy to prevent external modifications
        import copy

        self.data[key] = copy.deepcopy(data)

    def load(self, key: str) -> dict[str, Any] | None:
        """Load data from memory."""
        if key not in self.data:
            return None

        # Deep copy to prevent external modifications
        import copy

        return copy.deepcopy(self.data[key])

    def exists(self, key: str) -> bool:
        """Check if key exists in memory."""
        return key in self.data

    def delete(self, key: str) -> None:
        """Delete data from memory."""
        self.data.pop(key, None)

    def list_keys(self, prefix: str | None = None) -> list[str]:
        """List all keys in memory."""
        keys = list(self.data.keys())

        if prefix:
            keys = [k for k in keys if k.startswith(prefix)]

        return sorted(keys)

    def clear(self) -> None:
        """Clear all stored data."""
        self.data.clear()

    def size(self) -> int:
        """Get total size of stored data in bytes (estimated)."""
        # Return 0 for empty storage
        if not self.data:
            return 0

        # Estimate size by converting to JSON string
        import json

        try:
            json_str = json.dumps(self.data)
            return len(json_str.encode("utf-8"))
        except Exception:
            # Fallback: rough estimate based on number of items
            return len(self.data) * 100


class BatchWriter:
    """Batches write operations for improved performance."""

    def __init__(
        self, storage_backend: StorageBackend, batch_size: int = 100, batch_timeout: float = 5.0
    ):
        """Initialize batch writer.

        Args:
            storage_backend: Backend to write to
            batch_size: Maximum items before automatic flush
            batch_timeout: Maximum seconds before automatic flush
        """
        import threading
        from collections import defaultdict

        self.storage = storage_backend
        self.batch_size = batch_size
        self.batch_timeout = batch_timeout

        # Pending writes organized by key prefix
        self.pending: dict[str, list[dict[str, Any]]] = defaultdict(list)
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None

    def write(self, key: str, data: dict[str, Any]) -> None:
        """Queue data for batch writing."""
        should_flush = False

        with self._lock:
            # Extract prefix from key (e.g., "metrics_2024" -> "metrics")
            prefix = key.split("_")[0] if "_" in key else key

            self.pending[prefix].append(
                {"key": key, "data": data, "timestamp": data.get("timestamp", "")}
            )

            # Check if we should flush
            total_pending = sum(len(items) for items in self.pending.values())

            if total_pending >= self.batch_size:
                should_flush = True
            elif not self._timer:
                self._schedule_flush()

        # Flush outside of lock to avoid deadlock
        if should_flush:
            self._flush()

    def _schedule_flush(self) -> None:
        """Schedule a timed flush."""
        import threading

        if self._timer:
            self._timer.cancel()

        self._timer = threading.Timer(self.batch_timeout, self._flush)
        self._timer.daemon = True
        self._timer.start()

    def _flush(self) -> None:
        """Flush all pending writes."""
        with self._lock:
            if self._timer:
                self._timer.cancel()
                self._timer = None

            if not self.pending:
                return

            # Process each prefix group
            for prefix, items in self.pending.items():
                if not items:
                    continue

                # Create batch key with timestamp
                from datetime import datetime

                batch_key = f"{prefix}_batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

                # Save batch
                batch_data = {"prefix": prefix, "count": len(items), "items": items}

                try:
                    self.storage.save(batch_key, batch_data)
                except Exception as e:
                    logger.error(f"Failed to flush batch for prefix '{prefix}': {e}")

            # Clear pending
            self.pending.clear()

    def flush(self) -> None:
        """Force an immediate flush."""
        self._flush()

    def close(self) -> None:
        """Close the batch writer and flush remaining data."""
        self._flush()
        if self._timer:
            self._timer.cancel()
            self._timer = None
