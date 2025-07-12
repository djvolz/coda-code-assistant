# Observability Module API Reference

## Overview

The Observability module provides comprehensive logging, metrics, and tracing capabilities for Coda applications. It enables monitoring, debugging, and performance analysis of your AI-powered applications.

## Installation

The Observability module is part of the base Coda package:

```bash
pip install coda-assistant
```

For OpenTelemetry support:

```bash
pip install coda-assistant[telemetry]
```

## Quick Start

```python
from coda.base.observability import Logger, Tracer, Metrics

# Initialize logging
logger = Logger({"logging": {"level": "INFO"}})
logger.info("Application started")

# Use tracing
tracer = Tracer({"tracing": {"enabled": True}})
with tracer.span("process_request") as span:
    span.set_attribute("user_id", "123")
    # Process request
    logger.info("Processing request", extra={"span_id": span.span_id})

# Record metrics
metrics = Metrics({"metrics": {"enabled": True}})
metrics.increment("requests_total")
metrics.record_duration("request_duration", 0.125)
```

## API Reference

### Logger Class

```python
class Logger:
    """Structured logging with context support."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize logger.
        
        Args:
            config: Configuration with logging settings
        """
```

#### Logging Methods

##### debug(message: str, **kwargs) -> None

Log a debug message.

```python
logger.debug("Detailed information", user_id="123", action="login")
```

##### info(message: str, **kwargs) -> None

Log an informational message.

```python
logger.info("User logged in", user_id="123", ip="192.168.1.1")
```

##### warning(message: str, **kwargs) -> None

Log a warning message.

```python
logger.warning("Rate limit approaching", current=95, limit=100)
```

##### error(message: str, error: Exception | None = None, **kwargs) -> None

Log an error message.

```python
try:
    process_data()
except Exception as e:
    logger.error("Processing failed", error=e, data_id="456")
```

##### critical(message: str, **kwargs) -> None

Log a critical message.

```python
logger.critical("Database connection lost", retry_count=3)
```

#### Context Management

##### with_context(**kwargs) -> Logger

Create a logger with additional context.

```python
# Create logger with user context
user_logger = logger.with_context(user_id="123", session_id="abc")
user_logger.info("Action performed")  # Includes user context
```

##### set_context(**kwargs) -> None

Set global context for all logs.

```python
logger.set_context(
    environment="production",
    version="1.2.3"
)
```

### Tracer Class

```python
class Tracer:
    """Distributed tracing support."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize tracer.
        
        Args:
            config: Configuration with tracing settings
        """
```

#### Tracing Methods

##### span(name: str, kind: SpanKind = SpanKind.INTERNAL) -> Span

Create a new trace span.

```python
with tracer.span("process_request") as span:
    span.set_attribute("request_id", "789")
    # Process request
```

##### start_span(name: str, parent: Span | None = None) -> Span

Start a span manually.

```python
span = tracer.start_span("background_task")
try:
    # Do work
    span.set_status(StatusCode.OK)
finally:
    span.end()
```

#### Span Methods

##### set_attribute(key: str, value: Any) -> None

Add attribute to span.

```python
span.set_attribute("user_id", "123")
span.set_attribute("model", "gpt-4")
span.set_attribute("tokens", 150)
```

##### add_event(name: str, attributes: dict[str, Any] | None = None) -> None

Add event to span timeline.

```python
span.add_event("cache_hit", {"key": "user:123"})
span.add_event("retry_attempted", {"attempt": 1})
```

##### set_status(code: StatusCode, description: str | None = None) -> None

Set span status.

```python
from coda.base.observability import StatusCode

span.set_status(StatusCode.ERROR, "API rate limit exceeded")
```

### Metrics Class

```python
class Metrics:
    """Application metrics collection."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize metrics collector.
        
        Args:
            config: Configuration with metrics settings
        """
```

#### Metric Methods

##### increment(name: str, value: int = 1, labels: dict[str, str] | None = None) -> None

Increment a counter metric.

```python
metrics.increment("requests_total")
metrics.increment("errors_total", labels={"type": "timeout"})
```

##### gauge(name: str, value: float, labels: dict[str, str] | None = None) -> None

Set a gauge metric.

```python
metrics.gauge("active_sessions", 42)
metrics.gauge("memory_usage_mb", 256.5)
```

##### record_duration(name: str, duration: float, labels: dict[str, str] | None = None) -> None

Record a duration/histogram metric.

```python
metrics.record_duration("request_duration_seconds", 0.125)
metrics.record_duration("llm_call_duration", 2.5, labels={"model": "gpt-4"})
```

##### timing(name: str, labels: dict[str, str] | None = None) -> Timer

Context manager for timing operations.

```python
with metrics.timing("database_query_duration"):
    results = db.query("SELECT * FROM users")
```

## Examples

### Structured Logging

```python
from coda.base.observability import Logger

# Initialize with configuration
logger = Logger({
    "logging": {
        "level": "INFO",
        "format": "json",
        "output": "stdout",
        "include_timestamp": True
    }
})

# Log with structured data
logger.info(
    "API request completed",
    method="POST",
    path="/api/chat",
    status_code=200,
    duration_ms=125,
    user_id="user_123"
)

# Output (JSON format):
# {
#   "timestamp": "2024-01-15T10:30:45.123Z",
#   "level": "INFO",
#   "message": "API request completed",
#   "method": "POST",
#   "path": "/api/chat",
#   "status_code": 200,
#   "duration_ms": 125,
#   "user_id": "user_123"
# }
```

### Request Tracing

```python
from coda.base.observability import Tracer, StatusCode

tracer = Tracer({"tracing": {"service_name": "coda-api"}})

async def handle_chat_request(request):
    """Handle chat API request with tracing."""
    
    with tracer.span("handle_chat_request") as span:
        # Extract request info
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.path", request.path)
        span.set_attribute("user.id", request.user_id)
        
        # Validate request
        with tracer.span("validate_request", parent=span):
            if not validate(request):
                span.set_status(StatusCode.ERROR, "Invalid request")
                return {"error": "Invalid request"}, 400
        
        # Call LLM
        with tracer.span("llm_call", parent=span) as llm_span:
            llm_span.set_attribute("llm.model", "gpt-4")
            llm_span.set_attribute("llm.temperature", 0.7)
            
            try:
                response = await call_llm(request.messages)
                llm_span.set_attribute("llm.tokens", response.tokens)
                llm_span.add_event("response_received")
            except RateLimitError as e:
                llm_span.set_status(StatusCode.ERROR, str(e))
                raise
        
        span.set_status(StatusCode.OK)
        return {"response": response.content}, 200
```

### Metrics Collection

```python
from coda.base.observability import Metrics
import time

metrics = Metrics({
    "metrics": {
        "prefix": "coda_",
        "export_interval": 60
    }
})

class ChatService:
    """Chat service with metrics."""
    
    def __init__(self):
        self.metrics = metrics
    
    async def process_message(self, message: str, model: str):
        """Process chat message with metrics."""
        
        # Increment request counter
        self.metrics.increment(
            "chat_requests_total",
            labels={"model": model}
        )
        
        # Time the processing
        start_time = time.time()
        
        try:
            # Process message
            response = await self._process(message, model)
            
            # Record success
            self.metrics.increment(
                "chat_requests_success",
                labels={"model": model}
            )
            
            return response
            
        except Exception as e:
            # Record error
            self.metrics.increment(
                "chat_requests_errors",
                labels={
                    "model": model,
                    "error_type": type(e).__name__
                }
            )
            raise
        
        finally:
            # Record duration
            duration = time.time() - start_time
            self.metrics.record_duration(
                "chat_request_duration_seconds",
                duration,
                labels={"model": model}
            )
```

### Integrated Observability

```python
class ObservableApp:
    """Application with full observability."""
    
    def __init__(self, config: dict):
        self.logger = Logger(config)
        self.tracer = Tracer(config)
        self.metrics = Metrics(config)
    
    async def handle_request(self, request):
        """Handle request with full observability."""
        
        # Create trace
        with self.tracer.span("handle_request") as span:
            # Log request
            self.logger.info(
                "Request received",
                span_id=span.span_id,
                method=request.method,
                path=request.path
            )
            
            # Update metrics
            self.metrics.increment("requests_total")
            self.metrics.gauge("active_requests", self.active_count)
            
            try:
                # Process with timing
                with self.metrics.timing("request_processing_time"):
                    result = await self.process(request)
                
                # Log success
                self.logger.info(
                    "Request completed",
                    span_id=span.span_id,
                    status="success"
                )
                
                span.set_status(StatusCode.OK)
                return result
                
            except Exception as e:
                # Log error with full context
                self.logger.error(
                    "Request failed",
                    error=e,
                    span_id=span.span_id,
                    request_id=request.id
                )
                
                # Update error metrics
                self.metrics.increment(
                    "errors_total",
                    labels={"type": type(e).__name__}
                )
                
                span.set_status(StatusCode.ERROR, str(e))
                raise
```

### Custom Metrics Exporter

```python
class PrometheusExporter:
    """Export metrics in Prometheus format."""
    
    def __init__(self, metrics: Metrics):
        self.metrics = metrics
    
    def export(self) -> str:
        """Export metrics as Prometheus text."""
        lines = []
        
        for metric in self.metrics.get_all():
            # Add metric help
            lines.append(f"# HELP {metric.name} {metric.description}")
            lines.append(f"# TYPE {metric.name} {metric.type}")
            
            # Add metric values
            for value in metric.values:
                labels = self._format_labels(value.labels)
                lines.append(f"{metric.name}{labels} {value.value}")
        
        return "\n".join(lines)
    
    def _format_labels(self, labels: dict) -> str:
        """Format labels for Prometheus."""
        if not labels:
            return ""
        
        pairs = [f'{k}="{v}"' for k, v in labels.items()]
        return "{" + ",".join(pairs) + "}"

# Use exporter
exporter = PrometheusExporter(metrics)
prometheus_data = exporter.export()
```

## Advanced Usage

### Correlation IDs

```python
import uuid
from contextvars import ContextVar

correlation_id = ContextVar("correlation_id", default=None)

class CorrelatedLogger(Logger):
    """Logger that includes correlation IDs."""
    
    def _log(self, level: str, message: str, **kwargs):
        """Add correlation ID to all logs."""
        if cid := correlation_id.get():
            kwargs["correlation_id"] = cid
        
        super()._log(level, message, **kwargs)

# Use correlation
async def handle_request(request):
    # Set correlation ID for request
    cid = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))
    correlation_id.set(cid)
    
    logger.info("Processing request")  # Includes correlation_id
```

### Performance Profiling

```python
class PerformanceTracer(Tracer):
    """Tracer with performance profiling."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.slow_span_threshold = config.get("slow_span_threshold", 1.0)
    
    def span(self, name: str, **kwargs):
        """Create span with performance monitoring."""
        span = super().span(name, **kwargs)
        
        # Add performance monitoring
        original_end = span.end
        
        def end_with_monitoring():
            duration = span.duration_seconds
            
            if duration > self.slow_span_threshold:
                self.logger.warning(
                    f"Slow span detected: {name}",
                    duration=duration,
                    span_id=span.span_id
                )
                
                # Record slow span metric
                self.metrics.increment(
                    "slow_spans_total",
                    labels={"operation": name}
                )
            
            original_end()
        
        span.end = end_with_monitoring
        return span
```

### Log Aggregation

```python
class LogBuffer:
    """Buffer logs for batch processing."""
    
    def __init__(self, logger: Logger, batch_size: int = 100):
        self.logger = logger
        self.batch_size = batch_size
        self.buffer = []
    
    def log(self, level: str, message: str, **kwargs):
        """Add log to buffer."""
        self.buffer.append({
            "level": level,
            "message": message,
            "timestamp": datetime.now(),
            **kwargs
        })
        
        if len(self.buffer) >= self.batch_size:
            self.flush()
    
    def flush(self):
        """Send buffered logs."""
        if not self.buffer:
            return
        
        # Send to aggregation service
        self._send_batch(self.buffer)
        self.buffer.clear()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.flush()
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

# Include timestamp in logs
include_timestamp = true

# Additional fields to include
include_fields = ["hostname", "process_id"]

[tracing]
# Enable tracing
enabled = true

# Service name for traces
service_name = "coda"

# Trace exporter: "console", "otlp", "jaeger"
exporter = "otlp"

# OTLP endpoint
otlp_endpoint = "http://localhost:4317"

# Sampling rate (0.0 to 1.0)
sampling_rate = 1.0

[metrics]
# Enable metrics
enabled = true

# Metric prefix
prefix = "coda_"

# Export interval in seconds
export_interval = 60

# Exporter: "console", "prometheus", "otlp"
exporter = "prometheus"

# Prometheus port
prometheus_port = 9090
```

## Integration with External Systems

### OpenTelemetry

```python
from opentelemetry import trace, metrics
from opentelemetry.exporter.otlp.proto.grpc import (
    trace_exporter,
    metrics_exporter
)

# Configure OTLP exporters
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(
        trace_exporter.OTLPSpanExporter(
            endpoint="http://localhost:4317"
        )
    )
)
```

### CloudWatch

```python
import boto3

class CloudWatchLogger(Logger):
    """Logger that sends to AWS CloudWatch."""
    
    def __init__(self, config: dict):
        super().__init__(config)
        self.client = boto3.client("logs")
        self.log_group = config.get("cloudwatch_log_group")
        self.log_stream = config.get("cloudwatch_log_stream")
```

## Best Practices

1. **Use Structured Logging**: Include relevant context as fields
2. **Correlate Logs and Traces**: Use trace/span IDs in logs
3. **Set Appropriate Levels**: Use DEBUG sparingly in production
4. **Add Context**: Include user IDs, request IDs, etc.
5. **Monitor Key Metrics**: Track error rates, latencies, throughput
6. **Sample Traces**: Use sampling in high-volume environments
7. **Secure Sensitive Data**: Don't log passwords, tokens, PII

## See Also

- [Integration Guide](../integration-guide.md) - Using observability with other modules
- [Monitoring Guide](../guides/monitoring.md) - Setting up monitoring
- [OpenTelemetry Docs](https://opentelemetry.io/docs/) - OpenTelemetry documentation
- [Debugging Guide](../guides/debugging.md) - Using logs and traces for debugging