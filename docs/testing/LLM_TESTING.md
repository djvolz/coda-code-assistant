# LLM Testing with Ollama

This document describes how to run automated tests with real language models using Ollama.

## Overview

We use Ollama containers to provide consistent, offline LLM testing for:

- **End-to-end validation** - Test complete request/response cycles
- **Provider compatibility** - Verify provider implementations work correctly  
- **Performance testing** - Measure response times and throughput
- **Regression testing** - Catch breaking changes in LLM integrations
- **Cost-free testing** - No API costs for comprehensive test coverage

## Test Categories

### Unit Tests (Fast)
```bash
make test-unit
```
- Mock providers only
- No network dependencies
- <1 minute execution time

### LLM Tests (Medium)
```bash
make test-llm
```
- Real Ollama models
- Requires local Ollama service
- 2-5 minute execution time

### Integration Tests (Slow)  
```bash
make test-integration
```
- Cloud provider APIs (OCI, OpenAI, etc.)
- Requires API credentials
- Variable execution time

## Local LLM Testing

### Prerequisites

1. **Install Ollama**:
   ```bash
   curl -fsSL https://ollama.com/install.sh | sh
   ```

2. **Start Ollama service**:
   ```bash
   ollama serve
   ```

3. **Pull test model** (optional - tests will auto-pull):
   ```bash
   ollama pull tinyllama:1.1b
   ```

### Running LLM Tests

**Simple command**:
```bash
make test-llm
```

**With custom configuration**:
```bash
OLLAMA_HOST=http://localhost:11434 \
CODA_TEST_MODEL=tinyllama:1.1b \
RUN_LLM_TESTS=1 \
uv run pytest tests/llm/ -v
```

**Using the test script**:
```bash
./scripts/test_with_ollama.sh
```

## Docker-based LLM Testing

For isolated testing environments:

```bash
# Test with Docker Ollama (isolated environment)
make docker-test-llm

# Or manually with docker-compose
docker-compose -f docker-compose.test.yml up -d ollama-test
make test-llm OLLAMA_HOST=http://localhost:11435
docker-compose -f docker-compose.test.yml down
```

## CI/CD Integration

### GitHub Actions

The `.github/workflows/test-with-ollama.yml` workflow:

1. **Starts Ollama service** in GitHub Actions
2. **Pulls lightweight model** (tinyllama:1.1b ~1GB)
3. **Runs LLM test suite** with real model responses
4. **Cleans up resources** automatically

**Trigger conditions**:
- Push to `main` or `develop` 
- Pull requests to `main`
- Manual workflow dispatch

### Local CI Simulation

```bash
# Simulate CI environment locally
docker run --rm -d -p 11434:11434 ollama/ollama:latest
./scripts/test_with_ollama.sh
```

## Test Models

### Default: TinyLlama (1.1B parameters)
- **Size**: ~1GB download
- **Speed**: Fast inference (~1-2s response)  
- **Quality**: Basic but consistent responses
- **Use case**: Functional testing

### Alternative Models
```bash
# Faster but lower quality
export CODA_TEST_MODEL="phi3:mini"

# Larger but higher quality  
export CODA_TEST_MODEL="llama3.2:3b"

# Very small for quick tests
export CODA_TEST_MODEL="qwen2.5:0.5b"
```

## Test Structure

### LLM Test Files

- `tests/llm/test_real_llm_responses.py` - Core LLM functionality
- `tests/integration/test_ollama_integration.py` - Ollama provider tests
- `tests/providers/test_*_provider_*` - Provider-specific tests

### Test Markers

```python
@pytest.mark.llm          # Requires real LLM
@pytest.mark.ollama        # Requires Ollama service  
@pytest.mark.slow          # Long-running test
@pytest.mark.integration   # Requires external services
```

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `RUN_LLM_TESTS` | `false` | Enable LLM tests |
| `OLLAMA_HOST` | `http://localhost:11434` | Ollama server URL |
| `CODA_TEST_MODEL` | `tinyllama:1.1b` | Model for testing |
| `CODA_TEST_PROVIDER` | `ollama` | Provider to test |
| `OLLAMA_TIMEOUT` | `300` | Timeout for model operations |

## Performance Expectations

### Test Times
- **Unit tests**: 10-30 seconds
- **LLM tests**: 2-5 minutes  
- **Full test suite**: 5-10 minutes

### Resource Usage
- **Memory**: 2-4GB for TinyLlama
- **Disk**: 1-2GB for model storage
- **CPU**: Significant during inference

### Response Times
- **TinyLlama**: 1-3 seconds per response
- **Llama 3.2 3B**: 3-10 seconds per response
- **Streaming**: First token in <1 second

## Troubleshooting

### Common Issues

**Ollama not responding**:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/health

# Restart Ollama
pkill ollama && ollama serve
```

**Model not found**:
```bash
# List available models
ollama list

# Pull missing model
ollama pull tinyllama:1.1b
```

**Out of memory**:
```bash
# Use smaller model
export CODA_TEST_MODEL="qwen2.5:0.5b"

# Or increase system memory
```

**Timeout errors**:
```bash
# Increase timeout
export OLLAMA_TIMEOUT=600

# Use faster model
export CODA_TEST_MODEL="phi3:mini"
```

### Debug Commands

```bash
# Check Ollama status
curl -s http://localhost:11434/api/health | jq

# List models
curl -s http://localhost:11434/api/tags | jq

# Test model directly
curl -X POST http://localhost:11434/api/generate \
  -H "Content-Type: application/json" \
  -d '{"model": "tinyllama:1.1b", "prompt": "Hello"}'

# Monitor Ollama logs
ollama logs
```

## Best Practices

### For Development
- Use `make test-llm` for quick validation
- Keep TinyLlama for consistent fast tests  
- Test with multiple models before releases

### For CI/CD
- Always use Docker containers for consistency
- Set appropriate timeouts for model downloads
- Cache models between runs when possible
- Monitor test execution times and costs

### For Quality Assurance
- Include LLM tests in release validation
- Test edge cases with different model sizes
- Verify streaming and non-streaming responses
- Test error handling with invalid inputs

## Future Enhancements

- **Model caching** - Persistent model storage across runs
- **Performance benchmarks** - Track response time regressions  
- **Quality scoring** - Automated response quality metrics
- **Multi-model testing** - Test compatibility across model families
- **Load testing** - Concurrent request handling
- **Resource monitoring** - Memory and CPU usage tracking