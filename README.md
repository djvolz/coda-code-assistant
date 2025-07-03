# Coda - Code Assistant

A multi-provider, CLI-focused code assistant for AI-assisted development.

## Features

- > **Multi-Provider Support**: Ollama, OpenAI, Anthropic, OCI GenAI, and more
- =» **CLI-First**: Optimized for terminal workflows
- =' **Developer Tools**: Code generation, debugging, explaining, and reviewing
- =¾ **Session Management**: Save and resume conversations
- <¨ **Rich UI**: Beautiful terminal interface with themes

## Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/coda-code-assistant.git
cd coda-code-assistant

# Install with uv
uv sync

# Run Coda
uv run coda
```

## Quick Start

```bash
# Basic usage
uv run coda

# With specific provider
uv run coda --provider openai --model gpt-4

# Enable debug output
uv run coda --debug
```

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check --fix .
```

## License

[To be determined]