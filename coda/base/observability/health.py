"""Health monitoring for Coda providers and components.

This module provides health checks and monitoring for:
- Provider availability and response times
- Database connectivity and performance
- System resource usage
- Component status monitoring
"""

import json
import time
from collections import defaultdict, deque
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from ..config import ConfigManager
from .base import ObservabilityComponent
from .constants import ENV_PREFIX


@dataclass
class HealthCheck:
    """A single health check result."""

    name: str
    status: str  # healthy, degraded, unhealthy
    response_time_ms: float
    timestamp: datetime
    message: str | None = None
    metadata: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "response_time_ms": self.response_time_ms,
            "timestamp": self.timestamp.isoformat(),
            "message": self.message,
            "metadata": self.metadata or {},
        }


@dataclass
class ComponentHealth:
    """Health status for a component."""

    name: str
    status: str  # healthy, degraded, unhealthy
    last_check: datetime
    checks: list[HealthCheck]
    uptime_percentage: float = 100.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "name": self.name,
            "status": self.status,
            "last_check": self.last_check.isoformat(),
            "uptime_percentage": self.uptime_percentage,
            "checks": [check.to_dict() for check in self.checks],
        }


class HealthMonitor(ObservabilityComponent):
    """Monitors health of Coda components and providers."""

    def __init__(
        self,
        export_directory: Path,
        config_manager: ConfigManager,
        storage_backend=None,
        scheduler=None,
    ):
        """Initialize the health monitor.

        Args:
            export_directory: Directory to export health data
            config_manager: Configuration manager instance
            storage_backend: Optional storage backend
            scheduler: Optional shared scheduler
        """
        super().__init__(export_directory, config_manager, storage_backend, scheduler)

        # Health check storage
        self.component_health: dict[str, ComponentHealth] = {}
        self.check_history: dict[str, deque] = defaultdict(lambda: deque(maxlen=1000))

        # Configuration
        self.unhealthy_threshold = config_manager.get_int(
            "observability.health.unhealthy_threshold",
            default=3,  # 3 consecutive failures
            env_var=f"{ENV_PREFIX}HEALTH_UNHEALTHY_THRESHOLD",
        )

        self.degraded_threshold = config_manager.get_float(
            "observability.health.degraded_threshold",
            default=5000.0,  # 5 seconds response time
            env_var=f"{ENV_PREFIX}HEALTH_DEGRADED_THRESHOLD",
        )

        # Health check functions
        self.health_checkers: dict[str, Callable[[], HealthCheck]] = {}

        # Health data file
        self.health_file = self.export_directory / "health_status.json"

        # Register default health checks
        self._register_default_checks()

    def get_component_name(self) -> str:
        """Return the component name for logging."""
        return "HealthMonitor"

    def get_flush_interval(self) -> int:
        """Return the flush interval in seconds."""
        return self.config_manager.get_int(
            "observability.health.check_interval",
            default=30,  # 30 seconds
            env_var=f"{ENV_PREFIX}HEALTH_CHECK_INTERVAL",
        )

    def _flush_data(self) -> None:
        """Run health checks as part of the flush cycle."""
        self._run_health_checks()
        self._save_health_data()

    def _run_health_checks(self):
        """Run all registered health checks."""
        with self._lock:
            for name, checker in self.health_checkers.items():
                try:
                    result = checker()
                    self._record_health_check(result)
                except Exception as e:
                    # Create a failed health check
                    result = HealthCheck(
                        name=name,
                        status="unhealthy",
                        response_time_ms=0.0,
                        timestamp=datetime.now(UTC),
                        message=f"Health check failed: {e}",
                    )
                    self._record_health_check(result)

    def _record_health_check(self, result: HealthCheck):
        """Record a health check result."""
        with self._lock:
            # Add to history
            self.check_history[result.name].append(result)

            # Update component health
            if result.name not in self.component_health:
                self.component_health[result.name] = ComponentHealth(
                    name=result.name, status="healthy", last_check=result.timestamp, checks=[]
                )

            component = self.component_health[result.name]
            component.last_check = result.timestamp
            component.checks.append(result)

            # Keep only recent checks (last 100)
            if len(component.checks) > 100:
                component.checks = component.checks[-100:]

            # Update component status based on recent checks
            component.status = self._calculate_component_status(result.name)
            component.uptime_percentage = self._calculate_uptime(result.name)

    def _calculate_component_status(self, component_name: str) -> str:
        """Calculate overall status for a component."""
        if component_name not in self.component_health:
            return "unknown"

        component = self.component_health[component_name]
        if not component.checks:
            return "unknown"

        # Get recent checks (last 10)
        recent_checks = component.checks[-10:]

        # Count consecutive failures
        consecutive_failures = 0
        for check in reversed(recent_checks):
            if check.status == "unhealthy":
                consecutive_failures += 1
            else:
                break

        # Determine status
        if consecutive_failures >= self.unhealthy_threshold:
            return "unhealthy"

        # Check if any recent checks are degraded
        for check in recent_checks:
            if check.status == "degraded" or check.response_time_ms > self.degraded_threshold:
                return "degraded"

        return "healthy"

    def _calculate_uptime(self, component_name: str) -> float:
        """Calculate uptime percentage for a component."""
        if component_name not in self.check_history:
            return 100.0

        history = list(self.check_history[component_name])
        if not history:
            return 100.0

        # Calculate uptime over the last 24 hours
        now = datetime.now(UTC)
        cutoff_time = now - timedelta(hours=24)

        recent_checks = [check for check in history if check.timestamp >= cutoff_time]
        if not recent_checks:
            return 100.0

        healthy_checks = len([check for check in recent_checks if check.status == "healthy"])
        total_checks = len(recent_checks)

        return (healthy_checks / total_checks) * 100.0

    def register_health_check(self, name: str, checker: Callable[[], HealthCheck]):
        """Register a new health check function.

        Args:
            name: Name of the health check
            checker: Function that returns a HealthCheck result
        """
        with self._lock:
            self.health_checkers[name] = checker

    def _register_default_checks(self):
        """Register default health checks."""
        # Database connectivity check
        self.register_health_check("database", self._check_database_health)

        # File system check
        self.register_health_check("filesystem", self._check_filesystem_health)

        # Configuration check
        self.register_health_check("configuration", self._check_configuration_health)

    def register_provider_health_check(self, provider_name: str, provider_instance):
        """Register a health check for a specific provider.

        Args:
            provider_name: Name of the provider
            provider_instance: Provider instance for health checking
        """

        def provider_health_checker() -> HealthCheck:
            return self._check_provider_health(provider_name, provider_instance)

        self.register_health_check(f"provider_{provider_name}", provider_health_checker)

    def _check_provider_health(self, provider_name: str, provider_instance) -> HealthCheck:
        """Check health of a specific provider.

        Args:
            provider_name: Name of the provider
            provider_instance: Provider instance to check

        Returns:
            HealthCheck result
        """
        start_time = time.time()

        try:
            # Check if provider has a health check method
            if hasattr(provider_instance, "health_check"):
                result = provider_instance.health_check()
                response_time = (time.time() - start_time) * 1000

                return HealthCheck(
                    name=f"provider_{provider_name}",
                    status=result.get("status", "unknown"),
                    response_time_ms=response_time,
                    timestamp=datetime.now(UTC),
                    message=result.get("message", f"Provider {provider_name} health check"),
                    metadata=result.get("metadata", {}),
                )

            # Basic provider availability check
            if hasattr(provider_instance, "list_models"):
                try:
                    # Try to list models as a basic connectivity test
                    models = provider_instance.list_models()
                    response_time = (time.time() - start_time) * 1000

                    if models and len(models) > 0:
                        return HealthCheck(
                            name=f"provider_{provider_name}",
                            status="healthy",
                            response_time_ms=response_time,
                            timestamp=datetime.now(UTC),
                            message=f"Provider {provider_name} available ({len(models)} models)",
                            metadata={"model_count": len(models)},
                        )
                    else:
                        return HealthCheck(
                            name=f"provider_{provider_name}",
                            status="degraded",
                            response_time_ms=response_time,
                            timestamp=datetime.now(UTC),
                            message=f"Provider {provider_name} available but no models found",
                        )

                except Exception as e:
                    response_time = (time.time() - start_time) * 1000
                    return HealthCheck(
                        name=f"provider_{provider_name}",
                        status="unhealthy",
                        response_time_ms=response_time,
                        timestamp=datetime.now(UTC),
                        message=f"Provider {provider_name} connectivity failed: {e}",
                    )

            # If no health check or list_models method, just check if provider exists
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name=f"provider_{provider_name}",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now(UTC),
                message=f"Provider {provider_name} instance available",
                metadata={"type": type(provider_instance).__name__},
            )

        except Exception as e:
            response_time = (time.time() - start_time) * 1000
            return HealthCheck(
                name=f"provider_{provider_name}",
                status="unhealthy",
                response_time_ms=response_time,
                timestamp=datetime.now(UTC),
                message=f"Provider {provider_name} health check failed: {e}",
            )

    def _check_database_health(self) -> HealthCheck:
        """Check database connectivity and performance."""
        start_time = time.time()

        try:
            # Check if the database file exists
            # Get session DB path from config if available
            if self.config_manager:
                session_db_path = self.config_manager.get_data_dir() / "sessions.db"
                db_exists = session_db_path.exists()
                message = f"Database {'exists' if db_exists else 'not found'} at {session_db_path}"
            else:
                message = "Database check pending (config manager not available)"

            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                name="database",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now(UTC),
                message=message,
            )

        except Exception as e:
            return HealthCheck(
                name="database",
                status="unhealthy",
                response_time_ms=0.0,
                timestamp=datetime.now(UTC),
                message=f"Database check failed: {e}",
            )

    def _check_filesystem_health(self) -> HealthCheck:
        """Check file system access and permissions."""
        start_time = time.time()

        try:
            # Get directories from config module if available
            directories = []
            if self.config_manager:
                directories = [
                    self.config_manager.get_config_dir(),
                    self.config_manager.get_data_dir(),
                    self.config_manager.get_cache_dir(),
                ]

            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)

                # Test write access
                test_file = directory / ".health_check"
                test_file.write_text("test")
                test_file.unlink()

            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                name="filesystem",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now(UTC),
                message="File system accessible",
            )

        except Exception as e:
            return HealthCheck(
                name="filesystem",
                status="unhealthy",
                response_time_ms=0.0,
                timestamp=datetime.now(UTC),
                message=f"File system check failed: {e}",
            )

    def _check_configuration_health(self) -> HealthCheck:
        """Check configuration loading and validation."""
        start_time = time.time()

        try:
            # Try to load configuration
            config = self.config_manager.get_config()

            # Basic validation
            if not isinstance(config, dict):
                raise ValueError("Configuration is not a valid dictionary")

            response_time = (time.time() - start_time) * 1000

            return HealthCheck(
                name="configuration",
                status="healthy",
                response_time_ms=response_time,
                timestamp=datetime.now(UTC),
                message="Configuration loaded successfully",
            )

        except Exception as e:
            return HealthCheck(
                name="configuration",
                status="unhealthy",
                response_time_ms=0.0,
                timestamp=datetime.now(UTC),
                message=f"Configuration check failed: {e}",
            )

    def get_overall_health(self) -> dict[str, Any]:
        """Get overall health status."""
        with self._lock:
            if not self.component_health:
                return {"status": "unknown", "message": "No health checks have been performed yet"}

            # Determine overall status
            unhealthy_count = len(
                [c for c in self.component_health.values() if c.status == "unhealthy"]
            )
            degraded_count = len(
                [c for c in self.component_health.values() if c.status == "degraded"]
            )

            if unhealthy_count > 0:
                overall_status = "unhealthy"
                message = f"{unhealthy_count} component(s) unhealthy"
            elif degraded_count > 0:
                overall_status = "degraded"
                message = f"{degraded_count} component(s) degraded"
            else:
                overall_status = "healthy"
                message = "All components healthy"

            return {
                "status": overall_status,
                "message": message,
                "timestamp": datetime.now(UTC).isoformat(),
                "component_count": len(self.component_health),
                "healthy_count": len(
                    [c for c in self.component_health.values() if c.status == "healthy"]
                ),
                "degraded_count": degraded_count,
                "unhealthy_count": unhealthy_count,
            }

    def get_component_health(self, component_name: str | None = None) -> dict[str, Any]:
        """Get health status for a specific component or all components."""
        with self._lock:
            if component_name:
                if component_name not in self.component_health:
                    return {"error": f"Component '{component_name}' not found"}
                return self.component_health[component_name].to_dict()
            else:
                return {
                    name: component.to_dict() for name, component in self.component_health.items()
                }

    def get_health_summary(self) -> dict[str, Any]:
        """Get a summary of health status."""
        with self._lock:
            summary = self.get_overall_health()
            summary["components"] = {}

            for name, component in self.component_health.items():
                summary["components"][name] = {
                    "status": component.status,
                    "uptime_percentage": component.uptime_percentage,
                    "last_check": component.last_check.isoformat(),
                    "recent_checks": len(component.checks),
                }

            return summary

    def get_status(self) -> dict[str, Any]:
        """Get current status of the health monitor."""
        with self._lock:
            return {
                "running": self._running,
                "check_interval": self.get_flush_interval(),
                "unhealthy_threshold": self.unhealthy_threshold,
                "degraded_threshold": self.degraded_threshold,
                "registered_checks": list(self.health_checkers.keys()),
                "component_count": len(self.component_health),
            }

    def _save_health_data(self):
        """Save health data to file."""
        try:
            health_data = {
                "overall_health": self.get_overall_health(),
                "components": {
                    name: component.to_dict() for name, component in self.component_health.items()
                },
                "last_updated": datetime.now(UTC).isoformat(),
            }

            # Write to temp file first, then atomic rename
            temp_file = self.health_file.with_suffix(".tmp")
            with open(temp_file, "w") as f:
                json.dump(health_data, f, indent=2)

            temp_file.replace(self.health_file)

        except Exception as e:
            print(f"Warning: Failed to save health data: {e}")
