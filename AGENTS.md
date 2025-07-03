# Coda (Code Assistant)

## Project Overview

Coda is a multi-provider, CLI-focused code assistant that provides a unified interface for interacting with various Large Language Model (LLM) providers. Built with Python and designed to be UI-agnostic, Coda aims to be the ultimate developer companion for AI-assisted coding.

## Key Features

- **Multi-Provider Support**: Seamlessly switch between Ollama (local), OpenAI, OCI GenAI, Anthropic, and other LiteLLM-supported providers
- **CLI-First Design**: Optimized for terminal workflows with rich formatting and intuitive commands
- **UI Agnostic**: Core functionality works independently of any specific UI framework
- **Developer-Focused**: Specialized modes for code generation, debugging, explaining, and reviewing
- **Session Management**: Save, resume, and branch conversations with SQLite-backed persistence
- **Tool Integration**: Full support for Model Context Protocol (MCP) tools
- **Extensible**: Plugin architecture for custom providers and tools

## Architecture

Coda is structured as a modular Python application:

- **Core**: Provider-agnostic chat engine and session management
- **Providers**: Unified interface for multiple LLM providers via LiteLLM
- **CLI**: Rich terminal interface with advanced input handling
- **Tools**: MCP tool integration for enhanced capabilities
- **Config**: Flexible configuration system supporting TOML files and environment variables

## Quick Start

```bash
# Install with uv
uv sync

# Run the CLI
uv run coda

# With specific provider
uv run coda --provider openai --model gpt-4

# List available models
uv run coda --model list
```

## Development

This project uses:
- **uv**: For dependency management and virtual environments
- **Python 3.11+**: Modern Python features and type hints
- **LiteLLM**: Unified LLM provider interface
- **Rich**: Terminal formatting and UI components
- **Prompt Toolkit**: Advanced CLI input handling

### Preferred Tools

When working on this project, please use these modern CLI tools:
- **`rg` (ripgrep)** instead of `grep` - Faster and more intuitive search
- **`fd`** instead of `find` - Simple, fast, and user-friendly file finding
- **`uv`** instead of `python`/`pip` - Modern Python package and project manager
- **`gh`** for GitHub management - Official GitHub CLI for PRs, issues, etc.

## Configuration

Coda follows the XDG Base Directory specification:
- User config: `~/.config/coda/config.toml`
- Project config: `.coda/config.toml`
- Sessions: `~/.local/share/coda/sessions/`
- Cache: `~/.cache/coda/`

## Project Goals

1. **Simplicity**: Easy to install, configure, and use
2. **Flexibility**: Support any LLM provider through a unified interface
3. **Performance**: Fast response times with streaming support
4. **Developer Experience**: Intuitive commands and helpful defaults
5. **Extensibility**: Easy to add new providers, tools, and features

## Contributing

Coda welcomes contributions! Key areas for improvement:
- Additional provider integrations
- Enhanced tool capabilities
- UI/UX improvements
- Documentation and examples
- Performance optimizations

### Git Commit Guidelines

When committing code that was generated or modified with AI assistance, please follow these guidelines:

1. **Include the user prompt** (scrubbed of PII) in the commit message
2. **List all AI tools used** during the implementation

Example commit format:
```
feat: add session management with SQLite

AI Prompt: "implement session management that saves conversations to a database"
AI Tools: Read, Write, Edit, Bash, Task

- Added SQLAlchemy models for sessions
- Implemented save/load functionality
- Added session branching support
```

If the AI agent modifies or summarizes the user prompt in any way, add "(edited by agent)" after the prompt:
```
AI Prompt: "implement session management that saves conversations" (edited by agent)
```

**Important**: Always scrub any personally identifiable information (PII) from prompts:
- Replace actual paths with generic ones (e.g., `/home/user/` instead of `/home/johndoe/`)
- Remove any API keys, tokens, or secrets
- Replace specific company/project names if sensitive
- Remove email addresses, usernames, or other identifying information

## License

[To be determined]

## Related Projects

Coda builds upon and integrates with:
- LiteLLM: Unified LLM API interface
- Model Context Protocol (MCP): Standardized tool integration
- Rich: Python terminal formatting library