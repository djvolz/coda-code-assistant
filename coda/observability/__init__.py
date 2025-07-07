"""Observability package for Coda.

This package provides comprehensive observability features including:
- OpenTelemetry integration for metrics, traces, and logs
- Provider health monitoring
- Session and performance analytics
- Error tracking and alerting
"""

from .manager import ObservabilityManager
from .metrics import MetricsCollector
from .tracing import TracingManager
from .health import HealthMonitor

__all__ = [
    "ObservabilityManager",
    "MetricsCollector", 
    "TracingManager",
    "HealthMonitor",
]