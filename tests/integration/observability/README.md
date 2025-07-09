# Observability Integration Tests

This directory contains comprehensive integration tests for the Coda observability system, implementing Phase 11.2 of the roadmap.

## Test Coverage

### 1. Provider-Specific Command Tests
- **test_mock_provider_commands.py** - Tests all observability commands with MockProvider
- **test_ollama_provider_commands.py** - Tests all observability commands with Ollama provider

### 2. Configuration State Tests  
- **test_enabled_disabled_states.py** - Tests observability behavior when fully enabled/disabled
- **test_component_configurations.py** - Tests individual component enable/disable configurations

### 3. Data Export Tests
- **test_export_formats.py** - Tests JSON, CSV, HTML export formats with various data scenarios

### 4. Error Handling Tests
- **test_error_scenarios.py** - Tests error scenarios and recovery mechanisms

### 5. Advanced Testing
- **test_retention_policies.py** - Tests data retention and cleanup policies
- **test_memory_limits.py** - Tests memory management and eviction policies
- **test_load_testing.py** - Load testing with high-volume metrics
- **test_thread_safety.py** - Concurrent access and thread safety tests

## Test Categories Implemented

### ✅ Completed (High Priority)
1. **Test every observability command option with mock provider**
   - Status, metrics, health, traces, export, errors, performance commands
   - Various command options and flags
   - Edge cases and invalid inputs

2. **Test every observability command option with ollama provider**  
   - All commands with Ollama-specific scenarios
   - Model switching and streaming metrics
   - Connection failure handling

3. **Test all components with observability.enabled=true**
   - Full system integration
   - All tracking methods functional
   - Data persistence and retrieval

4. **Test all components with observability.enabled=false**
   - Graceful degradation
   - No-op behavior for tracking methods
   - Minimal performance impact

5. **Test error scenarios and recovery**
   - Storage permission errors
   - Disk full simulation
   - Corrupted storage files
   - Component initialization failures
   - Concurrent access conflicts

### ✅ Completed (Medium Priority)
6. **Test individual component enable/disable configurations**
   - Selective component enabling (metrics only, tracing only, etc.)
   - Mixed configurations
   - Component interaction testing

7. **Verify no performance impact when observability is disabled**
   - Performance comparison tests
   - Overhead measurement
   - Storage behavior validation

8. **Test data export formats**
   - JSON format with full data validation
   - Summary format testing
   - CSV and HTML format placeholders
   - Special characters and large datasets
   - Empty data handling

9. **Test retention policies and data cleanup**
   - Age-based cleanup policies
   - Size-based cleanup triggers
   - Component-specific retention periods
   - Archive vs delete options
   - Cleanup scheduling and manual triggers

10. **Test memory limits and eviction policies**
    - Memory limit enforcement
    - Buffer size restrictions
    - LRU eviction policy
    - High/low water mark eviction
    - Flush to disk under pressure

### ✅ Completed (Lower Priority)
11. **Load testing with high-volume metrics**
    - Throughput testing (>1000 events/sec)
    - Concurrent load from multiple threads
    - Sustained load testing
    - Burst load handling
    - Mixed workload scenarios
    - Resource utilization monitoring

12. **Concurrent access testing for thread safety**
    - Concurrent event tracking
    - Thread-safe trace operations
    - Race condition prevention
    - Deadlock prevention
    - Thread-local storage
    - Atomic operations
    - Chaos testing

## Running the Tests

### Run all observability integration tests:
```bash
uv run pytest tests/integration/observability/ -v --run-integration
```

### Run specific test file:
```bash
uv run pytest tests/integration/observability/test_mock_provider_commands.py -v --run-integration
```

### Run with coverage:
```bash
uv run pytest tests/integration/observability/ -v --run-integration --cov=coda.observability
```

## Test Structure

Each test file follows this pattern:
1. **Fixtures** - Set up test environment (temp directories, configs, managers)
2. **Helper Methods** - Output capture, config creation utilities
3. **Test Methods** - Individual test cases for specific scenarios

## Key Testing Patterns

### Configuration Setup
Tests create custom `CodaConfig` objects with specific observability settings:
```python
config = CodaConfig()
config.observability = {
    "enabled": True,
    "storage_path": "/path/to/storage",
    "metrics": {"enabled": True},
    # ... other components
}
```

### Output Validation
Tests capture CLI output and validate expected content:
```python
output = self.capture_output(cli._cmd_observability, "status")
assert "Observability Status" in output
assert "Enabled: True" in output
```

### Error Simulation
Tests simulate various error conditions:
- Permission errors (read-only directories)
- Storage failures (disk full)
- Network errors (invalid paths)
- Component failures (initialization errors)

## Notes

- Tests use `InteractiveCLI` directly to test command handling
- Mock providers avoid external dependencies
- Temporary directories ensure test isolation
- Thread safety tests verify concurrent operation handling