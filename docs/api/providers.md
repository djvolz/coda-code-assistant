# Providers Module API Reference

## Overview

The Providers module provides a unified interface for interacting with various AI/LLM providers. It abstracts away provider-specific implementations while maintaining a consistent API.

## Installation

The Providers module is part of the base Coda package:

```bash
pip install coda-assistant
```

For specific providers, install their dependencies:

```bash
# For LiteLLM (100+ providers)
pip install coda-assistant[litellm]

# For Ollama
pip install coda-assistant[ollama]

# For OCI GenAI
pip install coda-assistant[oci]
```

## Quick Start

```python
from coda.base.providers import ProviderFactory

# Create factory with configuration
factory = ProviderFactory({"providers": {"openai": {"api_key": "sk-..."}}})

# Create a provider
provider = factory.create("openai")

# List available models
models = provider.list_models()

# Chat with the model
response = provider.chat(
    messages=[{"role": "user", "content": "Hello!"}],
    model="gpt-4"
)
print(response.content)
```

## API Reference

### ProviderFactory Class

```python
class ProviderFactory:
    """Factory for creating provider instances with configuration management."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize factory with global configuration.
        
        Args:
            config: Global configuration dictionary with provider settings
        """
```

#### Methods

##### create(provider_name: str, **kwargs) -> BaseProvider

Create a provider instance.

```python
# Create with factory config
provider = factory.create("openai")

# Override specific settings
provider = factory.create("anthropic", temperature=0.5)
```

##### list_available() -> list[str]

List available provider names.

```python
available = factory.list_available()
# Returns: ["mock", "litellm", "ollama", "oci_genai"]
```

### BaseProvider Abstract Class

All providers inherit from BaseProvider:

```python
class BaseProvider(ABC):
    """Abstract base class for all providers."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        
    @abstractmethod
    def list_models(self) -> list[Model]:
        """List available models."""
        
    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs
    ) -> ChatCompletion:
        """Generate a chat completion."""
```

### Data Classes

#### Message

```python
@dataclass
class Message:
    """A chat message."""
    role: Role  # "user", "assistant", "system", or "tool"
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None
```

#### ChatCompletion

```python
@dataclass
class ChatCompletion:
    """A chat completion response."""
    content: str
    model: str
    finish_reason: str
    tool_calls: list[ToolCall] | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
```

#### Model

```python
@dataclass
class Model:
    """Model information."""
    id: str
    name: str
    provider: str
    metadata: dict[str, Any] = field(default_factory=dict)
```

### Provider Implementations

#### LiteLLM Provider

Supports 100+ providers through LiteLLM:

```python
# Configure for OpenAI
factory = ProviderFactory({
    "providers": {
        "litellm": {
            "api_key": "sk-...",
            "default_model": "gpt-4"
        }
    }
})

provider = factory.create("litellm")

# Use any LiteLLM-supported model
response = provider.chat(
    messages=[{"role": "user", "content": "Hello"}],
    model="claude-3-opus-20240229"  # Anthropic via LiteLLM
)
```

#### Ollama Provider

For local models via Ollama:

```python
factory = ProviderFactory({
    "providers": {
        "ollama": {
            "base_url": "http://localhost:11434",
            "default_model": "llama2"
        }
    }
})

provider = factory.create("ollama")
models = provider.list_models()  # Lists installed Ollama models
```

#### OCI GenAI Provider

Oracle Cloud Infrastructure Generative AI:

```python
factory = ProviderFactory({
    "providers": {
        "oci_genai": {
            "compartment_id": "ocid1.compartment.oc1...",
            "region": "us-phoenix-1"
        }
    }
})

provider = factory.create("oci_genai")
```

#### Mock Provider

For testing without API calls:

```python
provider = factory.create("mock")

response = provider.chat(
    messages=[{"role": "user", "content": "test"}],
    model="mock-echo"
)
# Returns contextual mock responses
```

## Examples

### Basic Chat

```python
from coda.base.providers import ProviderFactory, Message, Role

factory = ProviderFactory(config)
provider = factory.create("openai")

messages = [
    Message(role=Role.SYSTEM, content="You are a helpful assistant."),
    Message(role=Role.USER, content="What is Python?")
]

response = provider.chat(messages=messages, model="gpt-4")
print(response.content)
```

### Streaming Responses

```python
# Stream response chunks
for chunk in provider.chat_stream(
    messages=messages,
    model="gpt-4"
):
    print(chunk.content, end="", flush=True)
```

### Using Tools/Functions

```python
from coda.base.providers import Tool

# Define a tool
get_weather = Tool(
    name="get_weather",
    description="Get current weather",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string"},
            "unit": {"type": "string", "enum": ["celsius", "fahrenheit"]}
        },
        "required": ["location"]
    }
)

# Chat with tools
response = provider.chat(
    messages=messages,
    model="gpt-4",
    tools=[get_weather]
)

# Check if tool was called
if response.tool_calls:
    for tool_call in response.tool_calls:
        print(f"Tool: {tool_call.name}")
        print(f"Args: {tool_call.arguments}")
```

### Multi-Provider Comparison

```python
providers = ["openai", "anthropic", "ollama"]
prompt = "Explain quantum computing in one paragraph"

for provider_name in providers:
    try:
        provider = factory.create(provider_name)
        response = provider.chat(
            messages=[Message(role=Role.USER, content=prompt)],
            model=provider.list_models()[0].id
        )
        print(f"\n{provider_name}:\n{response.content}")
    except Exception as e:
        print(f"{provider_name}: Error - {e}")
```

### Async Operations

```python
import asyncio

async def chat_async():
    provider = factory.create("openai")
    
    response = await provider.achat(
        messages=[Message(role=Role.USER, content="Hello!")],
        model="gpt-4"
    )
    
    return response.content

# Run async
result = asyncio.run(chat_async())
```

### Error Handling

```python
from coda.base.providers import ProviderError

try:
    provider = factory.create("openai")
    response = provider.chat(messages=messages, model="gpt-4")
except ProviderError as e:
    print(f"Provider error: {e}")
    # Handle rate limits, auth errors, etc.
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Advanced Usage

### Custom Provider Implementation

```python
from coda.base.providers import BaseProvider, ChatCompletion, Model

class CustomProvider(BaseProvider):
    """Custom provider implementation."""
    
    def __init__(self, api_key: str, **kwargs):
        super().__init__(**kwargs)
        self.api_key = api_key
    
    @property
    def name(self) -> str:
        return "custom"
    
    def list_models(self) -> list[Model]:
        return [
            Model(
                id="custom-model-v1",
                name="Custom Model v1",
                provider="custom"
            )
        ]
    
    def chat(self, messages, model, **kwargs) -> ChatCompletion:
        # Implement your API call here
        response_text = self._call_api(messages, model, **kwargs)
        
        return ChatCompletion(
            content=response_text,
            model=model,
            finish_reason="stop"
        )

# Register the provider
from coda.base.providers import ProviderRegistry
ProviderRegistry.register("custom", CustomProvider)
```

### Provider Middleware

```python
class LoggingProvider:
    """Wrapper that logs all provider calls."""
    
    def __init__(self, provider: BaseProvider, logger):
        self.provider = provider
        self.logger = logger
    
    def chat(self, messages, model, **kwargs):
        self.logger.info(f"Chat request to {model}")
        start_time = time.time()
        
        try:
            response = self.provider.chat(messages, model, **kwargs)
            self.logger.info(f"Chat completed in {time.time() - start_time:.2f}s")
            return response
        except Exception as e:
            self.logger.error(f"Chat failed: {e}")
            raise

# Usage
base_provider = factory.create("openai")
provider = LoggingProvider(base_provider, logger)
```

### Provider Pooling

```python
class ProviderPool:
    """Manage multiple providers for load balancing."""
    
    def __init__(self, providers: list[BaseProvider]):
        self.providers = providers
        self._index = 0
    
    def get_next(self) -> BaseProvider:
        """Get next provider (round-robin)."""
        provider = self.providers[self._index]
        self._index = (self._index + 1) % len(self.providers)
        return provider
    
    def chat(self, messages, model, **kwargs):
        """Chat using next available provider."""
        provider = self.get_next()
        return provider.chat(messages, model, **kwargs)

# Create pool
pool = ProviderPool([
    factory.create("openai"),
    factory.create("anthropic"),
    factory.create("ollama")
])
```

### Retry Logic

```python
from tenacity import retry, stop_after_attempt, wait_exponential

class RobustProvider:
    """Provider with automatic retry logic."""
    
    def __init__(self, provider: BaseProvider):
        self.provider = provider
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    def chat(self, messages, model, **kwargs):
        return self.provider.chat(messages, model, **kwargs)
```

## Configuration Examples

### Environment Variables

```bash
# OpenAI via LiteLLM
export CODA_PROVIDERS_LITELLM_API_KEY="sk-..."
export CODA_PROVIDERS_LITELLM_DEFAULT_MODEL="gpt-4"

# Ollama
export CODA_PROVIDERS_OLLAMA_BASE_URL="http://localhost:11434"

# OCI GenAI
export CODA_PROVIDERS_OCI_GENAI_COMPARTMENT_ID="ocid1.compartment..."
export CODA_PROVIDERS_OCI_GENAI_REGION="us-phoenix-1"
```

### Configuration File

```toml
[providers.litellm]
api_key = "${OPENAI_API_KEY}"
default_model = "gpt-4"
temperature = 0.7

[providers.ollama]
base_url = "http://localhost:11434"
default_model = "llama2"
timeout = 120

[providers.oci_genai]
compartment_id = "${OCI_COMPARTMENT_ID}"
region = "us-phoenix-1"
service_endpoint = "https://generativeai.aiservice.us-phoenix-1.oci.oraclecloud.com"
```

## Testing with Mock Provider

```python
def test_chat_function():
    # Use mock provider for testing
    factory = ProviderFactory()
    provider = factory.create("mock")
    
    response = provider.chat(
        messages=[
            Message(role=Role.USER, content="What is Python?")
        ],
        model="mock-echo"
    )
    
    assert "Python" in response.content
    assert response.model == "mock-echo"
    assert response.finish_reason == "stop"
```

## Performance Considerations

1. **Connection Pooling**: Providers maintain connection pools when possible
2. **Streaming**: Use `chat_stream()` for long responses
3. **Async**: Use `achat()` for concurrent operations
4. **Caching**: Consider caching responses for identical requests

## Error Types

- `ProviderError`: Base exception for provider errors
- `AuthenticationError`: Invalid API key or credentials
- `RateLimitError`: Rate limit exceeded
- `ModelNotFoundError`: Requested model not available
- `ProviderNotAvailableError`: Provider service unavailable

## See Also

- [Integration Guide](../integration-guide.md) - Using providers with other modules
- [Example: Multi-Provider](../../tests/examples/multi_provider/) - Provider comparison example
- [LiteLLM Documentation](https://docs.litellm.ai/) - Supported providers
- [Provider Configuration](../reference/providers.md) - Detailed provider setup