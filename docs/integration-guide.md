# Coda Module Integration Guide

This guide demonstrates how to use Coda's modular components together to build applications.

## Quick Start

```python
from coda.base.providers import ProviderFactory
from coda.base.config import Config
from coda.base.session import SessionManager

# Initialize configuration
config = Config()

# Create a provider
factory = ProviderFactory(config.to_dict())
provider = factory.create("openai")

# Start a conversation
messages = []
response = provider.chat(messages, model="gpt-4", temperature=0.7)
```

## Common Integration Patterns

### 1. Provider + Config

The most basic integration combines configuration with a provider:

```python
config = Config()
factory = ProviderFactory(config.to_dict())
provider = factory.create("openai")
```

See [tests/examples/simple_chatbot](../tests/examples/simple_chatbot/) for a complete example.

### 2. Session + Provider

For persistent conversations with history:

```python
session_manager = SessionManager(config.to_dict())
session = session_manager.create_session("my-chat")
session.add_message({"role": "user", "content": "Hello"})
```

See [tests/examples/session_manager](../tests/examples/session_manager/) for persistent conversations.

### 3. Search + Provider

Combine semantic search with AI responses:

```python
from coda.base.search import SearchManager

search = SearchManager(config.to_dict())
results = await search.search("error handling")
# Use results as context for provider
```

See [tests/examples/code_analyzer](../tests/examples/code_analyzer/) for code intelligence.

## Module Dependencies

- **Config**: Foundation for all modules
- **Theme**: UI formatting (CLI apps)
- **Providers**: AI model integration
- **Session**: Conversation management
- **Search**: Semantic code search
- **Observability**: Logging and metrics

For comprehensive documentation, see the [wiki staging area](./wiki-staging/developer-guide/integration-guide.md).