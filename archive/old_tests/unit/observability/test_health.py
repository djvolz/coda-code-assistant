"""Unit tests for health monitor."""

import tempfile
from enum import Enum
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from coda.configuration import ConfigManager
from coda.observability.health import HealthMonitor


class HealthStatus(Enum):
    """Health status values used in tests."""

    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class TestHealthStatus:
    """Test the HealthStatus enum."""

    def test_health_status_values(self):
        """Test health status enum values."""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.DEGRADED.value == "degraded"
        assert HealthStatus.UNHEALTHY.value == "unhealthy"
        assert HealthStatus.UNKNOWN.value == "unknown"


class TestHealthMonitor:
    """Test the HealthMonitor class."""

    @pytest.fixture
    def config_manager(self):
        """Create a mock config manager."""
        config = Mock(spec=ConfigManager)
        config.get_int.side_effect = lambda key, default=0: {
            "observability.health.check_interval": 30,
            "observability.health.failure_threshold": 3,
        }.get(key, default)
        config.get_string.return_value = ""
        return config

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_initialization(self, temp_dir, config_manager):
        """Test HealthMonitor initialization."""
        monitor = HealthMonitor(temp_dir, config_manager)

        assert monitor.base_dir == temp_dir
        assert monitor.config_manager == config_manager
        assert hasattr(monitor, "_provider_health")
        assert hasattr(monitor, "_component_health")
        assert hasattr(monitor, "_system_health")
        assert monitor._start_time > 0

    def test_check_provider_health_success(self, temp_dir, config_manager):
        """Test successful provider health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # Mock successful provider check
        with patch(
            "coda.observability.health.HealthMonitor._check_provider_availability"
        ) as mock_check:
            mock_check.return_value = True

            result = monitor.check_provider_health("openai")

            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["available"] is True
            assert result["consecutive_failures"] == 0
            assert "last_check" in result

    def test_check_provider_health_failure(self, temp_dir, config_manager):
        """Test failed provider health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        with patch(
            "coda.observability.health.HealthMonitor._check_provider_availability"
        ) as mock_check:
            mock_check.return_value = False

            # First failure
            result = monitor.check_provider_health("openai")
            assert result["status"] == HealthStatus.HEALTHY.value  # Still healthy after 1 failure
            assert result["consecutive_failures"] == 1

            # Second failure
            result = monitor.check_provider_health("openai")
            assert result["status"] == HealthStatus.DEGRADED.value
            assert result["consecutive_failures"] == 2

            # Third failure (reaches threshold)
            result = monitor.check_provider_health("openai")
            assert result["status"] == HealthStatus.UNHEALTHY.value
            assert result["consecutive_failures"] == 3

    def test_check_provider_health_recovery(self, temp_dir, config_manager):
        """Test provider health recovery."""
        monitor = HealthMonitor(temp_dir, config_manager)

        with patch(
            "coda.observability.health.HealthMonitor._check_provider_availability"
        ) as mock_check:
            # Fail checks
            mock_check.return_value = False
            for _ in range(3):
                monitor.check_provider_health("openai")

            # Verify unhealthy
            assert monitor._provider_health["openai"]["status"] == HealthStatus.UNHEALTHY

            # Recover
            mock_check.return_value = True
            result = monitor.check_provider_health("openai")

            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["consecutive_failures"] == 0

    def test_check_database_health_success(self, temp_dir, config_manager):
        """Test successful database health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        with patch(
            "coda.observability.health.HealthMonitor._check_database_connectivity"
        ) as mock_check:
            mock_check.return_value = (True, 50.0)  # Connected, 50ms latency

            result = monitor.check_database_health()

            assert result["status"] == HealthStatus.HEALTHY.value
            assert result["connected"] is True
            assert result["latency_ms"] == 50.0

    def test_check_database_health_failure(self, temp_dir, config_manager):
        """Test failed database health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        with patch(
            "coda.observability.health.HealthMonitor._check_database_connectivity"
        ) as mock_check:
            mock_check.return_value = (False, None)

            result = monitor.check_database_health()

            assert result["status"] == HealthStatus.UNHEALTHY.value
            assert result["connected"] is False
            assert result["latency_ms"] is None

    def test_check_filesystem_health(self, temp_dir, config_manager):
        """Test filesystem health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        result = monitor.check_filesystem_health()

        assert result["status"] == HealthStatus.HEALTHY.value
        assert result["writable"] is True
        assert result["space_available_gb"] > 0
        assert "last_check" in result

    @patch("shutil.disk_usage")
    def test_check_filesystem_health_low_space(self, mock_disk_usage, temp_dir, config_manager):
        """Test filesystem health with low disk space."""
        # Mock low disk space (500MB available)
        mock_disk_usage.return_value = MagicMock(
            total=100 * 1024**3,  # 100GB
            used=99.5 * 1024**3,  # 99.5GB
            free=0.5 * 1024**3,  # 0.5GB
        )

        monitor = HealthMonitor(temp_dir, config_manager)
        result = monitor.check_filesystem_health()

        assert result["status"] == HealthStatus.DEGRADED.value
        assert result["space_available_gb"] < 1.0

    def test_check_configuration_health(self, temp_dir, config_manager):
        """Test configuration health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        result = monitor.check_configuration_health()

        assert result["status"] == HealthStatus.HEALTHY.value
        assert result["valid"] is True
        assert result["issues"] == []

    def test_check_component_health(self, temp_dir, config_manager):
        """Test component health check."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # Register a healthy component
        monitor.update_component_health("metrics", HealthStatus.HEALTHY, {"info": "test"})

        result = monitor.check_component_health("metrics")

        assert result["status"] == HealthStatus.HEALTHY.value
        assert result["details"]["info"] == "test"
        assert "last_update" in result

    def test_check_component_health_unknown(self, temp_dir, config_manager):
        """Test checking health of unknown component."""
        monitor = HealthMonitor(temp_dir, config_manager)

        result = monitor.check_component_health("unknown_component")

        assert result["status"] == HealthStatus.UNKNOWN.value

    def test_update_component_health(self, temp_dir, config_manager):
        """Test updating component health."""
        monitor = HealthMonitor(temp_dir, config_manager)

        monitor.update_component_health("tracing", HealthStatus.DEGRADED, {"reason": "high memory"})

        assert "tracing" in monitor._component_health
        assert monitor._component_health["tracing"]["status"] == HealthStatus.DEGRADED
        assert monitor._component_health["tracing"]["details"]["reason"] == "high memory"

    def test_get_status(self, temp_dir, config_manager):
        """Test getting overall health status."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # Set up various health states
        monitor.update_component_health("metrics", HealthStatus.HEALTHY)
        monitor.update_component_health("tracing", HealthStatus.DEGRADED)

        with patch(
            "coda.observability.health.HealthMonitor._check_provider_availability"
        ) as mock_check:
            mock_check.return_value = True
            monitor.check_provider_health("openai")

        status = monitor.get_status()

        assert "overall_status" in status
        assert "providers" in status
        assert "components" in status
        assert "system" in status
        assert "uptime_seconds" in status
        assert status["uptime_seconds"] >= 0

    def test_get_provider_statuses(self, temp_dir, config_manager):
        """Test getting all provider statuses."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # Check multiple providers
        with patch(
            "coda.observability.health.HealthMonitor._check_provider_availability"
        ) as mock_check:
            mock_check.side_effect = [True, False, True]

            monitor.check_provider_health("openai")
            monitor.check_provider_health("anthropic")
            monitor.check_provider_health("google")

        statuses = monitor.get_provider_statuses()

        assert len(statuses) == 3
        assert statuses["openai"]["status"] == HealthStatus.HEALTHY.value
        assert statuses["anthropic"]["status"] == HealthStatus.HEALTHY.value  # 1 failure
        assert statuses["google"]["status"] == HealthStatus.HEALTHY.value

    def test_get_component_statuses(self, temp_dir, config_manager):
        """Test getting all component statuses."""
        monitor = HealthMonitor(temp_dir, config_manager)

        monitor.update_component_health("metrics", HealthStatus.HEALTHY)
        monitor.update_component_health("tracing", HealthStatus.DEGRADED)
        monitor.update_component_health("error_tracking", HealthStatus.UNHEALTHY)

        statuses = monitor.get_component_statuses()

        assert len(statuses) == 3
        assert statuses["metrics"]["status"] == HealthStatus.HEALTHY.value
        assert statuses["tracing"]["status"] == HealthStatus.DEGRADED.value
        assert statuses["error_tracking"]["status"] == HealthStatus.UNHEALTHY.value

    def test_overall_status_calculation(self, temp_dir, config_manager):
        """Test overall status calculation logic."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # All healthy
        monitor.update_component_health("comp1", HealthStatus.HEALTHY)
        monitor.update_component_health("comp2", HealthStatus.HEALTHY)
        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.HEALTHY.value

        # One degraded
        monitor.update_component_health("comp2", HealthStatus.DEGRADED)
        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.DEGRADED.value

        # One unhealthy
        monitor.update_component_health("comp1", HealthStatus.UNHEALTHY)
        status = monitor.get_status()
        assert status["overall_status"] == HealthStatus.UNHEALTHY.value

    def test_run_all_checks(self, temp_dir, config_manager):
        """Test running all health checks."""
        monitor = HealthMonitor(temp_dir, config_manager)

        with patch(
            "coda.observability.health.HealthMonitor._check_provider_availability"
        ) as mock_provider:
            with patch(
                "coda.observability.health.HealthMonitor._check_database_connectivity"
            ) as mock_db:
                mock_provider.return_value = True
                mock_db.return_value = (True, 50.0)

                # Set provider list
                with patch.object(
                    monitor, "_get_configured_providers", return_value=["openai", "anthropic"]
                ):
                    monitor.run_all_checks()

        # Should have checked all systems
        assert "database" in monitor._system_health
        assert "filesystem" in monitor._system_health
        assert "configuration" in monitor._system_health
        assert "openai" in monitor._provider_health
        assert "anthropic" in monitor._provider_health

    def test_flush_data(self, temp_dir, config_manager):
        """Test flushing health data."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # Add some health data
        monitor.update_component_health("test", HealthStatus.HEALTHY)
        monitor.check_provider_health("openai")

        monitor._flush_data()

        # Check data was saved
        health_file = temp_dir / "health_status.json"
        assert health_file.exists()

    def test_thread_safety(self, temp_dir, config_manager):
        """Test thread safety of health operations."""
        import threading

        monitor = HealthMonitor(temp_dir, config_manager)
        errors = []

        def worker(thread_id):
            try:
                for _ in range(50):
                    # Update various health statuses
                    monitor.update_component_health(f"comp_{thread_id}", HealthStatus.HEALTHY)
                    monitor.check_provider_health(f"provider_{thread_id}")
                    monitor.check_filesystem_health()
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

    def test_export_format(self, temp_dir, config_manager):
        """Test export data format."""
        monitor = HealthMonitor(temp_dir, config_manager)

        # Set up various health states
        monitor.update_component_health("metrics", HealthStatus.HEALTHY)
        monitor.check_provider_health("openai")
        monitor.check_filesystem_health()

        export_data = monitor.get_export_data()

        assert "current_status" in export_data
        assert "health_history" in export_data
        assert "uptime_seconds" in export_data
