# Observability Module

The Observability module provides comprehensive logging, metrics, and tracing for monitoring and debugging Coda applications.

## Features

- 📊 **Structured Logging**: JSON and text formats with rich context
- 📈 **Metrics Collection**: Counters, gauges, histograms
- 🔍 **Distributed Tracing**: Track requests across components  
- 🚨 **Error Tracking**: Capture and analyze errors
- 📡 **Multiple Exporters**: Console, OTLP, Prometheus, CloudWatch

## Quick Start

```python
from coda.base.observability import Logger, Metrics, Tracer

# Logging
logger = Logger({"logging": {"level": "INFO"}})
logger.info("Application started", version="1.0.0")

# Metrics
metrics = Metrics({"metrics": {"enabled": True}})
metrics.increment("requests_total")
metrics.gauge("active_users", 42)

# Tracing  
tracer = Tracer({"tracing": {"service_name": "coda"}})
with tracer.span("process_request") as span:
    span.set_attribute("user_id", "123")
    # Process request
```

## Logging

### Basic Usage

```python
logger = Logger()

# Log levels
logger.debug("Detailed debug info")
logger.info("Informational message")  
logger.warning("Warning message")
logger.error("Error occurred", error=exception)
logger.critical("Critical system error")

# Structured logging
logger.info(
    "Request processed",
    method="POST",
    path="/api/chat",
    duration_ms=125,
    user_id="user_123"
)
```

### Context Management

```python
# Add persistent context
logger.set_context(
    environment="production",
    region="us-west-2"
)

# Create logger with additional context
request_logger = logger.with_context(
    request_id="req_123",
    user_id="user_456"
)
request_logger.info("Processing request")
```

### Error Logging

```python
try:
    risky_operation()
except Exception as e:
    logger.error(
        "Operation failed",
        error=e,
        operation="risky_operation",
        retry_count=3
    )
```

## Metrics

### Metric Types

```python
# Counter - always increasing
metrics.increment("requests_total")
metrics.increment("errors_total", labels={"type": "timeout"})

# Gauge - can go up or down
metrics.gauge("queue_size", 150)
metrics.gauge("memory_usage_mb", 512.5)

# Histogram - distribution of values
metrics.record_duration("response_time_seconds", 0.125)
metrics.record_duration("query_time", 0.045, labels={"db": "postgres"})
```

### Timing Operations

```python
# Using context manager
with metrics.timing("operation_duration"):
    perform_operation()

# Manual timing
start = time.time()
process_data()
duration = time.time() - start
metrics.record_duration("processing_time", duration)
```

## Tracing

### Creating Spans

```python
# Basic span
with tracer.span("fetch_user") as span:
    span.set_attribute("user_id", user_id)
    user = fetch_from_db(user_id)
    
# Nested spans
with tracer.span("handle_request") as parent:
    with tracer.span("validate", parent=parent):
        validate_request()
    
    with tracer.span("process", parent=parent):
        process_request()
```

### Span Attributes and Events

```python
with tracer.span("payment_processing") as span:
    # Set attributes
    span.set_attribute("payment.amount", 99.99)
    span.set_attribute("payment.currency", "USD")
    
    # Add events
    span.add_event("payment_validated")
    span.add_event("payment_charged", {
        "processor": "stripe",
        "transaction_id": "txn_123"
    })
    
    # Set status
    if success:
        span.set_status(StatusCode.OK)
    else:
        span.set_status(StatusCode.ERROR, "Payment failed")
```

## Advanced Features

### Error Tracking

```python
from coda.base.observability import ErrorTracker

tracker = ErrorTracker(logger, metrics)

@tracker.track_errors
def risky_function():
    # Automatically tracks and logs errors
    pass

# Manual error tracking
try:
    operation()
except Exception as e:
    tracker.capture_exception(
        e,
        context={"user_id": "123", "action": "upload"}
    )
```

### Health Checks

```python
from coda.base.observability import HealthCheck

health = HealthCheck()

# Register checks
health.register(
    "database",
    lambda: check_db_connection(),
    critical=True
)

health.register(
    "redis",
    lambda: check_redis(),
    critical=False
)

# Get health status
status = health.check_all()
```

### Performance Profiling

```python
from coda.base.observability import Profiler

profiler = Profiler()

@profiler.profile
def slow_function():
    # Function execution will be profiled
    pass

# Get profile results
stats = profiler.get_stats()
```

## Configuration

```toml
[logging]
# Log level: DEBUG, INFO, WARNING, ERROR, CRITICAL
level = "INFO"

# Output format: "json" or "text"  
format = "json"

# Output destination: "stdout", "stderr", or file path
output = "stdout"

# Include timestamp
include_timestamp = true

# Additional context fields
include_fields = ["hostname", "process_id"]

[metrics]
# Enable metrics collection
enabled = true

# Metric name prefix
prefix = "coda_"

# Export interval (seconds)
export_interval = 60

# Exporter: "console", "prometheus", "otlp"
exporter = "prometheus"

# Prometheus endpoint
prometheus_port = 9090

[tracing]
# Enable tracing
enabled = true

# Service name
service_name = "coda"

# Exporter: "console", "otlp", "jaeger"
exporter = "otlp"

# OTLP endpoint
otlp_endpoint = "http://localhost:4317"

# Sampling rate (0.0 to 1.0)
sampling_rate = 1.0
```

## Integration Examples

### FastAPI Integration

```python
from fastapi import FastAPI, Request
from coda.base.observability import Logger, Tracer, Metrics

app = FastAPI()
logger = Logger()
tracer = Tracer()
metrics = Metrics()

@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    with tracer.span("http_request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.path", request.url.path)
        
        metrics.increment("http_requests_total")
        
        try:
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            return response
        except Exception as e:
            logger.error("Request failed", error=e)
            span.set_status(StatusCode.ERROR)
            raise
```

### OpenTelemetry Export

```python
# Configure OTLP export
config = {
    "tracing": {
        "enabled": True,
        "exporter": "otlp",
        "otlp_endpoint": "http://localhost:4317"
    },
    "metrics": {
        "enabled": True,
        "exporter": "otlp",
        "otlp_endpoint": "http://localhost:4317"
    }
}

# Traces and metrics will be sent to OTLP collector
```

## API Documentation

For detailed API documentation, see [Observability API Reference](../../../docs/api/observability.md).

## Examples

- [Full Observability Example](./example.py) - Complete demonstration
- [FastAPI Integration](../../../tests/examples/fastapi_observable/) - Web app example
- [Observability Tests](../../../tests/base/observability/) - Test implementations

## Best Practices

1. **Structured Logging**: Always use key-value pairs for context
2. **Meaningful Metrics**: Use descriptive names and labels
3. **Trace Sampling**: Use sampling in production to reduce overhead
4. **Error Context**: Include relevant context when logging errors
5. **Span Attributes**: Add meaningful attributes for debugging
6. **Resource Usage**: Monitor the overhead of observability itself