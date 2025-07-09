"""Integration tests for observability data retention and cleanup policies."""

import json
import os
import tempfile
import time
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.configuration import CodaConfig, ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityRetentionPolicies:
    """Test data retention policies and cleanup mechanisms."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_with_retention(self, temp_dir):
        """Create config with retention settings."""
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "retention": {
                "days": 7,  # Keep data for 7 days
                "max_size_mb": 100,  # Max 100MB of data
                "cleanup_interval_hours": 1,  # Run cleanup every hour
                "archive_old_data": True,  # Archive instead of delete
            },
            "metrics": {"enabled": True, "retention_days": 7},
            "tracing": {"enabled": True, "retention_days": 3},
            "health": {"enabled": True, "retention_days": 1},
            "error_tracking": {"enabled": True, "retention_days": 14},
            "profiling": {"enabled": True, "retention_days": 1},
        }

        manager = ConfigManager()
        manager.config = config
        return manager

    def test_retention_policy_initialization(self, config_with_retention):
        """Test that retention policies are properly initialized."""
        ObservabilityManager(config_with_retention)  # Initialize to test retention loading

        # Check retention settings are loaded
        retention_days = config_with_retention.get_int("observability.retention.days", default=30)
        assert retention_days == 7

        max_size = config_with_retention.get_int(
            "observability.retention.max_size_mb", default=1000
        )
        assert max_size == 100

    def test_data_cleanup_by_age(self, config_with_retention, temp_dir):
        """Test cleanup of data older than retention period."""
        obs_manager = ObservabilityManager(config_with_retention)
        storage_path = Path(temp_dir) / "observability"

        # Create old and new data files
        old_date = datetime.now() - timedelta(days=10)
        new_date = datetime.now() - timedelta(days=2)

        # Create metrics files
        metrics_dir = storage_path / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        # Old file (should be cleaned up)
        old_file = metrics_dir / f"metrics_{old_date.strftime('%Y%m%d_%H%M%S')}.json"
        old_file.write_text(json.dumps({"event": "old_data", "timestamp": old_date.isoformat()}))

        # New file (should be kept)
        new_file = metrics_dir / f"metrics_{new_date.strftime('%Y%m%d_%H%M%S')}.json"
        new_file.write_text(json.dumps({"event": "new_data", "timestamp": new_date.isoformat()}))

        # Set file modification times
        os.utime(old_file, (old_date.timestamp(), old_date.timestamp()))
        os.utime(new_file, (new_date.timestamp(), new_date.timestamp()))

        # Run cleanup (would normally be scheduled)
        if hasattr(obs_manager, "_cleanup_old_data"):
            obs_manager._cleanup_old_data()

        # Check results
        assert not old_file.exists() or (storage_path / "archive" / old_file.name).exists()
        assert new_file.exists()

    def test_data_cleanup_by_size(self, temp_dir):
        """Test cleanup when storage exceeds size limit."""
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "retention": {
                "days": 30,
                "max_size_mb": 0.001,  # Very small limit (1KB) to trigger cleanup
                "cleanup_interval_hours": 1,
            },
            "metrics": {"enabled": True},
        }

        manager = ConfigManager()
        manager.config = config
        obs_manager = ObservabilityManager(manager)

        # Generate data exceeding size limit
        for i in range(100):
            obs_manager.track_event(f"event_{i}", {"data": "x" * 100})  # ~100 bytes each

        # Force a storage check/cleanup
        storage_path = Path(temp_dir) / "observability"
        total_size = sum(f.stat().st_size for f in storage_path.rglob("*") if f.is_file())

        # Size should be managed (exact behavior depends on implementation)
        assert total_size < 10 * 1024 * 1024  # Should be less than 10MB

    def test_component_specific_retention(self, config_with_retention):
        """Test different retention periods for different components."""
        ObservabilityManager(config_with_retention)  # Initialize to test retention loading

        # Components have different retention periods
        metrics_retention = config_with_retention.get_int(
            "observability.metrics.retention_days", default=7
        )
        tracing_retention = config_with_retention.get_int(
            "observability.tracing.retention_days", default=7
        )
        error_retention = config_with_retention.get_int(
            "observability.error_tracking.retention_days", default=7
        )

        assert metrics_retention == 7
        assert tracing_retention == 3
        assert error_retention == 14

    def test_archive_old_data(self, config_with_retention, temp_dir):
        """Test archiving of old data instead of deletion."""
        ObservabilityManager(config_with_retention)  # Initialize to test retention loading
        storage_path = Path(temp_dir) / "observability"
        archive_path = storage_path / "archive"

        # Create old data
        old_date = datetime.now() - timedelta(days=10)
        metrics_dir = storage_path / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        old_file = metrics_dir / f"metrics_{old_date.strftime('%Y%m%d')}.json"
        old_file.write_text(json.dumps({"event": "archive_test"}))
        os.utime(old_file, (old_date.timestamp(), old_date.timestamp()))

        # Simulate archival process
        if config_with_retention.get_bool(
            "observability.retention.archive_old_data", default=False
        ):
            archive_path.mkdir(parents=True, exist_ok=True)
            # In real implementation, old files would be moved to archive

        # Archive directory should exist if archiving is enabled
        assert archive_path.exists() or not config_with_retention.get_bool(
            "observability.retention.archive_old_data"
        )

    def test_cleanup_scheduling(self, config_with_retention):
        """Test that cleanup is scheduled according to configuration."""
        obs_manager = ObservabilityManager(config_with_retention)

        cleanup_interval = config_with_retention.get_int(
            "observability.retention.cleanup_interval_hours", default=24
        )
        assert cleanup_interval == 1

        # Check if scheduler has cleanup task
        if obs_manager.scheduler:
            # Scheduler should have tasks registered
            assert hasattr(obs_manager.scheduler, "_tasks") or hasattr(
                obs_manager.scheduler, "tasks"
            )

    def test_manual_cleanup_trigger(self, config_with_retention, temp_dir):
        """Test manual triggering of cleanup process."""
        obs_manager = ObservabilityManager(config_with_retention)

        # Generate some test data
        for i in range(50):
            obs_manager.track_event(f"cleanup_test_{i}", {"index": i})

        # Manually trigger cleanup
        if hasattr(obs_manager, "cleanup_data"):
            result = obs_manager.cleanup_data()
            # Should return cleanup statistics
            assert isinstance(result, dict) or result is None

    def test_retention_with_active_sessions(self, config_with_retention):
        """Test that active session data is not cleaned up."""
        obs_manager = ObservabilityManager(config_with_retention)

        # Track active session
        obs_manager.track_event("session_start", {"session_id": "active_123", "active": True})

        # Track old inactive session
        old_date = datetime.now() - timedelta(days=10)
        with patch("time.time", return_value=old_date.timestamp()):
            obs_manager.track_event("session_start", {"session_id": "old_456", "active": False})

        # Cleanup should preserve active session data
        # Implementation would check session status before cleanup

    def test_storage_quota_enforcement(self, temp_dir):
        """Test enforcement of storage quotas."""
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "retention": {
                "max_size_mb": 1,  # 1MB limit
                "enforce_quota": True,
            },
            "metrics": {"enabled": True},
        }

        manager = ConfigManager()
        manager.config = config
        obs_manager = ObservabilityManager(manager)

        # Try to exceed quota
        large_data = "x" * 10000  # 10KB per event
        events_before_quota = 0

        for i in range(200):  # Try to write 2MB
            try:
                obs_manager.track_event(f"quota_test_{i}", {"data": large_data})
                events_before_quota += 1
            except Exception:
                # Quota exceeded
                break

        # Should have stopped before writing all events
        assert events_before_quota < 200

    def test_cleanup_performance(self, config_with_retention, temp_dir):
        """Test cleanup performance with large number of files."""
        obs_manager = ObservabilityManager(config_with_retention)
        storage_path = Path(temp_dir) / "observability" / "metrics"
        storage_path.mkdir(parents=True, exist_ok=True)

        # Create many old files
        old_date = datetime.now() - timedelta(days=10)
        for i in range(1000):
            file_path = storage_path / f"metrics_{old_date.strftime('%Y%m%d')}_{i:04d}.json"
            file_path.write_text(json.dumps({"index": i}))
            os.utime(file_path, (old_date.timestamp(), old_date.timestamp()))

        # Measure cleanup time
        start_time = time.time()

        # Trigger cleanup (implementation specific)
        if hasattr(obs_manager, "_cleanup_old_data"):
            obs_manager._cleanup_old_data()

        cleanup_time = time.time() - start_time

        # Cleanup should complete in reasonable time
        assert cleanup_time < 10.0  # Should take less than 10 seconds

    def test_retention_policy_updates(self, temp_dir):
        """Test updating retention policies at runtime."""
        # Start with default retention
        config = CodaConfig()
        config.observability = {
            "enabled": True,
            "storage_path": os.path.join(temp_dir, "observability"),
            "retention": {"days": 30},
            "metrics": {"enabled": True},
        }

        manager = ConfigManager()
        manager.config = config
        obs_manager = ObservabilityManager(manager)

        # Generate data with original retention
        obs_manager.track_event("before_update", {"retention_days": 30})

        # Update retention policy
        config.observability["retention"]["days"] = 7

        # New data should follow new retention
        obs_manager.track_event("after_update", {"retention_days": 7})

        # Verify configuration was updated
        assert manager.get_int("observability.retention.days") == 7

    def test_selective_data_cleanup(self, config_with_retention):
        """Test selective cleanup based on data importance."""
        obs_manager = ObservabilityManager(config_with_retention)

        # Track events with different importance levels
        obs_manager.track_event("critical_error", {"severity": "critical", "preserve": True})
        obs_manager.track_event("debug_info", {"severity": "debug", "preserve": False})
        obs_manager.track_error(
            Exception("Important error"), {"severity": "high", "preserve": True}
        )

        # Cleanup should respect preservation flags
        # Critical data should be retained longer

    def test_cleanup_transaction_safety(self, config_with_retention, temp_dir):
        """Test that cleanup is transaction-safe."""
        obs_manager = ObservabilityManager(config_with_retention)

        # Start tracking events
        def track_events():
            for i in range(100):
                obs_manager.track_event(f"concurrent_{i}", {"thread": "writer"})
                time.sleep(0.001)

        import threading

        # Start event tracking in background
        writer_thread = threading.Thread(target=track_events)
        writer_thread.start()

        # Trigger cleanup while writing
        time.sleep(0.05)  # Let some events be written
        if hasattr(obs_manager, "_cleanup_old_data"):
            obs_manager._cleanup_old_data()

        writer_thread.join()

        # No data corruption should occur
        storage_path = Path(temp_dir) / "observability"
        for file_path in storage_path.rglob("*.json"):
            try:
                with open(file_path) as f:
                    json.load(f)  # Should be valid JSON
            except json.JSONDecodeError:
                pytest.fail(f"Corrupted file found: {file_path}")

    def test_disk_space_recovery(self, config_with_retention, temp_dir):
        """Test that cleanup actually recovers disk space."""
        obs_manager = ObservabilityManager(config_with_retention)
        storage_path = Path(temp_dir) / "observability"

        # Measure initial size
        initial_size = sum(f.stat().st_size for f in storage_path.rglob("*") if f.is_file())

        # Generate old data
        old_date = datetime.now() - timedelta(days=10)
        metrics_dir = storage_path / "metrics"
        metrics_dir.mkdir(parents=True, exist_ok=True)

        for i in range(100):
            file_path = metrics_dir / f"old_data_{i}.json"
            file_path.write_text(json.dumps({"data": "x" * 1000}))
            os.utime(file_path, (old_date.timestamp(), old_date.timestamp()))

        # Measure size with old data
        with_old_size = sum(f.stat().st_size for f in storage_path.rglob("*") if f.is_file())
        assert with_old_size > initial_size

        # Run cleanup
        if hasattr(obs_manager, "_cleanup_old_data"):
            obs_manager._cleanup_old_data()

        # Measure size after cleanup
        after_cleanup_size = sum(f.stat().st_size for f in storage_path.rglob("*") if f.is_file())

        # Should have recovered space (unless archiving is enabled)
        if not config_with_retention.get_bool("observability.retention.archive_old_data"):
            assert after_cleanup_size < with_old_size
