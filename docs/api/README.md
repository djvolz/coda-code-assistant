# Coda API Reference

This directory contains API reference documentation for all Coda base modules.

## Base Modules

- [Config](config.md) - Configuration management
- [Theme](theme.md) - Terminal UI and formatting
- [Providers](providers.md) - AI provider abstraction
- [Session](session.md) - Conversation management
- [Search](search.md) - Semantic code search
- [Observability](observability.md) - Logging and metrics

## Using the API Documentation

Each module's documentation includes:

1. **Overview** - Module purpose and design
2. **Installation** - How to install the module
3. **Quick Start** - Basic usage examples
4. **API Reference** - Detailed class and method documentation
5. **Examples** - Code snippets and use cases
6. **Advanced Usage** - Complex scenarios and patterns

## Import Structure

All base modules can be imported from their respective packages:

```python
from coda.base.config import Config
from coda.base.theme import ThemeManager
from coda.base.providers import ProviderFactory, BaseProvider
from coda.base.session import SessionManager, Session
from coda.base.search import SearchManager
from coda.base.observability import Logger, Tracer
```

## Type Safety

All modules include comprehensive type hints. For type checking:

```bash
mypy your_code.py
```

## Version Compatibility

These APIs are stable as of version 1.0.0. Breaking changes will be documented in release notes.