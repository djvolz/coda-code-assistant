# Providers Module

The Providers module provides a unified interface for interacting with various AI/LLM providers.

## Features

- 🌐 **Multi-Provider Support**: OpenAI, Anthropic, Ollama, OCI GenAI, and 100+ via LiteLLM
- 🔌 **Pluggable Architecture**: Easy to add new providers
- 🎯 **Consistent API**: Same interface regardless of provider
- 🔄 **Streaming Support**: Real-time response streaming
- 🛠️ **Tool/Function Calling**: Unified tool interface across providers

## Quick Start

```python
from coda.base.providers import ProviderFactory

# Create factory with configuration
factory = ProviderFactory({
    "providers": {
        "openai": {"api_key": "sk-..."}
    }
})

# Create provider instance
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

## Available Providers

### LiteLLM (100+ providers)
```python
provider = factory.create("litellm")
# Supports OpenAI, Anthropic, Google, Cohere, and many more
```

### Ollama (Local models)
```python
provider = factory.create("ollama")
# Run models locally with Ollama
```

### OCI GenAI (Oracle Cloud)
```python
provider = factory.create("oci_genai")
# Oracle's enterprise AI service
```

### Mock (Testing)
```python
provider = factory.create("mock")
# For testing without API calls
```

## Configuration

```toml
[providers.litellm]
api_key = "${OPENAI_API_KEY}"
default_model = "gpt-4"

[providers.ollama]
base_url = "http://localhost:11434"
default_model = "llama2"

[providers.oci_genai]
compartment_id = "${OCI_COMPARTMENT_ID}"
region = "us-phoenix-1"
```

## Advanced Usage

### Streaming Responses

```python
for chunk in provider.chat_stream(
    messages=[{"role": "user", "content": "Tell me a story"}],
    model="gpt-4"
):
    print(chunk.content, end="", flush=True)
```

### Tool/Function Calling

```python
from coda.base.providers import Tool

weather_tool = Tool(
    name="get_weather",
    description="Get current weather",
    parameters={
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        },
        "required": ["location"]
    }
)

response = provider.chat(
    messages=messages,
    model="gpt-4",
    tools=[weather_tool]
)

if response.tool_calls:
    for call in response.tool_calls:
        print(f"Tool: {call.name}, Args: {call.arguments}")
```

### Custom Provider Implementation

```python
from coda.base.providers import BaseProvider, ChatCompletion

class MyProvider(BaseProvider):
    def chat(self, messages, model, **kwargs) -> ChatCompletion:
        # Your implementation
        pass
    
    def list_models(self) -> list[Model]:
        # Return available models
        pass

# Register your provider
from coda.base.providers import ProviderRegistry
ProviderRegistry.register("my_provider", MyProvider)
```

## Testing

The module includes a mock provider for testing:

```python
provider = factory.create("mock")
# Returns contextual mock responses without API calls
```

## API Documentation

For detailed API documentation, see [Providers API Reference](../../../docs/api/providers.md).

## Examples

- [Simple Chatbot](../../../tests/examples/simple_chatbot/) - Basic usage
- [Multi-Provider Comparison](../../../tests/examples/multi_provider/) - Compare providers
- [Provider Tests](../../../tests/base/providers/) - Test implementations