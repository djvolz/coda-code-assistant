# OCI GenAI Integration Documentation

This document explains how the Oracle Cloud Infrastructure (OCI) Generative AI integration works in Coda, including the implementation details, streaming response handling, and comprehensive test suite.

## Table of Contents

1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Implementation Details](#implementation-details)
4. [Streaming Response Handling](#streaming-response-handling)
5. [Model Discovery](#model-discovery)
6. [Test Suite](#test-suite)
7. [Configuration](#configuration)
8. [Troubleshooting](#troubleshooting)

## Overview

The OCI GenAI integration provides native support for Oracle's Generative AI service, offering access to over 30 models from providers like Cohere, Meta, and xAI. This integration was the first provider implemented in Coda and serves as a reference implementation for future providers.

### Key Features

- **Native OCI SDK Integration**: Direct use of Oracle's Python SDK
- **Dynamic Model Discovery**: Automatically discovers available models
- **Multi-Format Streaming**: Handles different response formats per provider
- **Comprehensive Testing**: Unit, integration, and functional test coverage
- **Zero Configuration**: Works with existing OCI CLI configuration

## Architecture

### Provider Interface

The OCI GenAI provider implements the abstract `Provider` interface defined in `coda/core/provider.py`:

```python
class Provider(ABC):
    @abstractmethod
    async def chat(self, messages: List[Message], model: str, **kwargs) -> ChatCompletion:
        """Synchronous chat completion"""
        
    @abstractmethod
    async def stream_chat(self, messages: List[Message], model: str, **kwargs) -> AsyncIterator[ChatCompletionChunk]:
        """Streaming chat completion"""
        
    @abstractmethod
    def list_models(self) -> List[Model]:
        """List available models"""
```

### Class Structure

```
OCIGenAIProvider
├── __init__()              # Initialize OCI client and config
├── list_models()           # Discover available models
├── chat()                  # Synchronous chat completion
├── stream_chat()           # Streaming chat completion
├── _parse_streaming_chunk() # Parse SSE chunks
└── _validate_model()       # Validate model ID
```

## Implementation Details

### Initialization

The provider initializes with OCI configuration from `~/.oci/config`:

```python
def __init__(self, compartment_id: Optional[str] = None):
    self.config = oci.config.from_file()
    self.compartment_id = compartment_id or os.getenv("OCI_COMPARTMENT_ID")
    self.client = GenerativeAiInferenceClient(
        config=self.config,
        service_endpoint="https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
    )
```

### Model Discovery

Models are discovered dynamically from the OCI API:

```python
def list_models(self) -> List[Model]:
    """Discover all available models in the compartment"""
    models = []
    for endpoint in self.inference_endpoints:
        response = generative_ai_client.list_models(
            compartment_id=self.compartment_id,
            state="ACTIVE"
        )
        for model in response.data:
            models.append(Model(
                id=self._convert_to_model_id(model.display_name),
                name=model.display_name,
                provider="oci-genai",
                capabilities=model.capabilities
            ))
    return models
```

## Streaming Response Handling

The most complex part of the integration is handling different streaming response formats from various model providers.

### Response Format Discovery

Through debugging, we discovered three distinct response formats:

#### 1. xAI/Meta Format
```json
{
  "message": {
    "role": "ASSISTANT",
    "content": [
      {
        "type": "TEXT",
        "text": "Hello, world!"
      }
    ]
  }
}
```

#### 2. Cohere Format
```json
{
  "apiFormat": "COHERE",
  "text": "Hello from Cohere!",
  "finishReason": "stop"
}
```

#### 3. Legacy Chat Format
```json
{
  "chatResponse": {
    "choices": [
      {
        "delta": {
          "content": "Streaming text..."
        }
      }
    ]
  }
}
```

### Streaming Parser Implementation

The `_parse_streaming_chunk` method handles all formats:

```python
def _parse_streaming_chunk(self, chunk: str, model: str) -> Optional[ChatCompletionChunk]:
    """Parse SSE chunk based on provider format"""
    
    # Skip empty lines and SSE headers
    if not chunk or chunk.startswith(':'):
        return None
        
    # Extract JSON from SSE data
    if chunk.startswith('data: '):
        chunk = chunk[6:]
        
    try:
        data = json.loads(chunk)
        
        # Handle Cohere format
        if "cohere" in model.lower():
            if "text" in data and "finishReason" not in data:
                return ChatCompletionChunk(content=data.get("text", ""))
            elif "finishReason" in data:
                return ChatCompletionChunk(content="")  # Avoid duplication
                
        # Handle xAI/Meta format
        else:
            message = data.get("message", {})
            if message:
                content_list = message.get("content", [])
                if content_list and isinstance(content_list, list):
                    content = content_list[0].get("text", "")
                    return ChatCompletionChunk(content=content)
                    
        # Handle legacy format (kept for compatibility)
        if "chatResponse" in data:
            choices = data["chatResponse"].get("choices", [])
            if choices:
                delta = choices[0].get("delta", {})
                return ChatCompletionChunk(content=delta.get("content", ""))
                
    except json.JSONDecodeError:
        logger.warning(f"Failed to parse chunk: {chunk}")
        
    return None
```

### Streaming Flow

1. **Request Creation**: Build OCI chat request with messages
2. **Stream Initiation**: Call `chat_stream` with SSE details
3. **Event Processing**: Parse Server-Sent Events line by line
4. **Format Detection**: Identify provider format from response
5. **Content Extraction**: Extract text based on format
6. **Chunk Yielding**: Yield ChatCompletionChunk objects

## Test Suite

The test suite follows a layered approach for comprehensive coverage while maintaining fast CI/CD cycles.

### Test Categories

#### 1. Unit Tests (Fast, No Dependencies)

Located in `tests/unit/test_oci_parsing.py`:
- Test response parsing logic
- Model name conversion
- JSON handling edge cases
- No OCI SDK dependencies

Example:
```python
@pytest.mark.unit
def test_parse_xai_message_format():
    """Test parsing xAI/Meta message format"""
    response = {
        "message": {
            "content": [{"type": "TEXT", "text": "Hello"}]
        }
    }
    assert extract_content(response) == "Hello"
```

#### 2. Integration Tests (Real API Calls)

Located in `tests/integration/test_oci_genai_integration.py`:
- Test actual OCI API connectivity
- Model discovery validation
- Real chat completions
- Require OCI credentials

Example:
```python
@pytest.mark.integration
@pytest.mark.skipif(not os.getenv("OCI_COMPARTMENT_ID"), 
                    reason="No credentials")
def test_real_model_discovery(provider):
    """Test discovering models from OCI API"""
    models = provider.list_models()
    assert len(models) > 0
    assert any("cohere" in m.id for m in models)
```

#### 3. Functional Tests (End-to-End)

Located in `tests/functional/test_oci_genai_functional.py`:
- Test CLI interactive mode
- Concurrent requests
- Error handling
- Full user workflows

### CI/CD Integration

The GitHub Actions workflow runs tests in stages:

```yaml
# .github/workflows/test.yml
jobs:
  test:
    steps:
      # Always run unit tests (fast)
      - name: Run unit tests
        run: pytest tests/ -v -m "unit or not integration"
        
  integration-test:
    if: github.ref == 'refs/heads/main'
    steps:
      # Run integration tests on main branch
      - name: Run integration tests
        env:
          OCI_COMPARTMENT_ID: ${{ secrets.OCI_COMPARTMENT_ID }}
        run: pytest tests/ -v -m integration
```

### Running Tests Locally

```bash
# Unit tests only (fast, no credentials needed)
make test

# All tests including integration
make test-all

# Specific test category
make test-unit
make test-integration

# With coverage
make test-cov
```

## Configuration

### Environment Variables

```bash
# Required for OCI GenAI
export OCI_COMPARTMENT_ID="ocid1.compartment.oc1..xxxx"

# Optional overrides
export OCI_CONFIG_FILE="~/.oci/config"
export OCI_CONFIG_PROFILE="DEFAULT"
```

### Config File

```toml
# ~/.config/coda/config.toml
[providers.oci_genai]
compartment_id = "ocid1.compartment.oc1..xxxx"
region = "us-chicago-1"
```

## Troubleshooting

### Common Issues

#### 1. No Models Found
```
Error: No models available for provider oci-genai
```
**Solution**: Ensure OCI_COMPARTMENT_ID is set and you have access to GenAI models.

#### 2. Streaming Not Working
```
Error: EOF when reading a line
```
**Solution**: This was the original issue - update to latest version with streaming fixes.

#### 3. Authentication Errors
```
Error: Invalid private key
```
**Solution**: Check `~/.oci/config` and ensure key file exists and has correct permissions.

### Debug Mode

Enable debug logging to see detailed OCI requests:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

Or set environment variable:
```bash
export CODA_LOG_LEVEL=DEBUG
```

### Testing Response Formats

Use the debug script to test specific models:

```python
# tests/debug_streaming.py
async def test_model_format(model_id):
    provider = OCIGenAIProvider()
    async for chunk in provider.stream_chat(
        messages=[{"role": "user", "content": "Hi"}],
        model=model_id
    ):
        print(f"Chunk: {chunk.content}")
```

## Future Enhancements

1. **Response Caching**: Cache model discovery results
2. **Retry Logic**: Add exponential backoff for transient failures
3. **Token Counting**: Implement accurate token estimation
4. **Fine-tuning Support**: Add support for custom models
5. **Multi-Region**: Support multiple OCI regions
6. **Batch Inference**: Support batch chat completions

## Contributing

When adding new features to the OCI GenAI provider:

1. **Add Unit Tests First**: Test parsing logic without dependencies
2. **Mock OCI Calls**: Use mocks for complex OCI interactions
3. **Document Response Formats**: Add examples of new formats
4. **Update Integration Tests**: Add tests for new capabilities
5. **Follow Streaming Pattern**: Maintain consistency with existing code

## References

- [OCI GenAI Documentation](https://docs.oracle.com/en-us/iaas/Content/generative-ai/home.htm)
- [OCI Python SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/)
- [Server-Sent Events Spec](https://html.spec.whatwg.org/multipage/server-sent-events.html)
- [Coda Roadmap](../ROADMAP.md)