# Coda Base Modules

The base layer provides the foundational building blocks for Coda applications. Each module is independent with zero dependencies on other base modules.

## Modules

### 🔧 [Config](config/)
Centralized configuration management with environment variable support, file loading, and type-safe access.

### 🤖 [Providers](providers/)
Unified interface for AI/LLM providers including OpenAI, Anthropic, Ollama, OCI GenAI, and 100+ more via LiteLLM.

### 💬 [Session](session/)
Conversation management with persistence, branching, and history tracking.

### 🔍 [Search](search/)
Semantic code search using vector embeddings for intelligent code discovery.

### 🎨 [Theme](theme/)
Terminal UI formatting, syntax highlighting, and visual components.

### 📊 [Observability](observability/)
Comprehensive logging, metrics, and tracing for monitoring and debugging.

## Design Principles

1. **Zero Dependencies**: Base modules don't depend on each other
2. **Provider Agnostic**: Work with any configuration or provider
3. **Extensible**: Easy to add new implementations
4. **Well-Tested**: Comprehensive test coverage
5. **Type-Safe**: Full type hints for better IDE support

## Usage

Each module can be used independently:

```python
# Use just what you need
from coda.base.config import Config
from coda.base.providers import ProviderFactory

config = Config()
factory = ProviderFactory(config.to_dict())
provider = factory.create("openai")
```

Or combine modules for more functionality:

```python
from coda.base.config import Config
from coda.base.providers import ProviderFactory
from coda.base.session import SessionManager
from coda.base.theme import ThemeManager

# Build your application with composable modules
config = Config()
theme = ThemeManager(config.to_dict())
session_manager = SessionManager(config.to_dict())
provider = ProviderFactory(config.to_dict()).create("openai")
```

## Module Documentation

- [Config API Reference](../../docs/api/config.md)
- [Providers API Reference](../../docs/api/providers.md)
- [Session API Reference](../../docs/api/session.md)
- [Search API Reference](../../docs/api/search.md)
- [Theme API Reference](../../docs/api/theme.md)
- [Observability API Reference](../../docs/api/observability.md)

## Examples

See the [examples directory](../../tests/examples/) for complete working examples:
- Simple Chatbot - Basic provider usage
- Session Manager - Persistent conversations
- Code Analyzer - Semantic search integration

## Contributing

When adding new base modules:
1. Ensure zero dependencies on other base modules
2. Include comprehensive tests
3. Add type hints to all public APIs
4. Create API documentation
5. Add usage examples

## Testing

Run tests for all base modules:

```bash
pytest coda/base/
```

Run tests for a specific module:

```bash
pytest coda/base/config/
pytest coda/base/providers/
```