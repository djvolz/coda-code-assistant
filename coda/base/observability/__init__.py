"""🔧 BASE MODULE
Observability package for Coda.

This package provides comprehensive observability features including:
- OpenTelemetry integration for metrics, traces, and logs
- Provider health monitoring
- Session and performance analytics
- Error tracking and alerting

This module has zero Coda dependencies and can be copy-pasted to any project.
"""

from .health import HealthMonitor
from .manager import ObservabilityManager
from .metrics import MetricsCollector
from .tracing import TracingManager

__all__ = [
    "ObservabilityManager",
    "MetricsCollector",
    "TracingManager",
    "HealthMonitor",
]
