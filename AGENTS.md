# Coda (Code Assistant)

## Project Overview

Coda is a multi-provider, CLI-focused code assistant that provides a unified interface for interacting with various Large Language Model (LLM) providers. Built with Python and designed to be UI-agnostic, Coda aims to be the ultimate developer companion for AI-assisted coding.

## Key Features

### ✅ Implemented
- **Native OCI GenAI Provider**: Complete integration with Oracle Cloud Infrastructure GenAI service
- **CLI-First Design**: Rich terminal interface with colorized output and interactive model selection
- **Provider Architecture**: Unified interface with abstract base class for extensibility
- **Dynamic Model Discovery**: Automatic model detection with 24-hour caching for performance
- **Streaming Support**: Real-time response streaming with proper terminal UI
- **Configuration Management**: Multi-source config (TOML files, environment variables, CLI parameters)
- **Comprehensive Error Handling**: Clear setup guidance and debugging support

### 🔄 In Development
- **Multi-Provider Support**: Ollama (local), OpenAI, Anthropic, and other LiteLLM-supported providers
- **Session Management**: Save, resume, and branch conversations with SQLite-backed persistence
- **Tool Integration**: Full support for Model Context Protocol (MCP) tools
- **Developer-Focused Modes**: Specialized modes for code generation, debugging, explaining, and reviewing
- **Enhanced CLI**: Slash commands, conversation branching, and advanced input handling

## Architecture

Coda is structured as a modular Python application:

- **Core**: Provider-agnostic chat engine and session management
- **Providers**: Unified interface for multiple LLM providers via LiteLLM
- **CLI**: Rich terminal interface with advanced input handling
- **Tools**: MCP tool integration for enhanced capabilities
- **Config**: Flexible configuration system supporting TOML files and environment variables

## Important: Read the Roadmap

**Before starting any development work, please read the [ROADMAP.md](ROADMAP.md) file.** This document contains:
- Detailed technical architecture and design decisions
- Current implementation status for each phase
- Planned features and their priority
- Technical requirements and dependencies
- Integration points and API designs

Understanding the roadmap will help you align your contributions with the project's vision and avoid duplicate work.

## Quick Start

```bash
# Install with uv
uv sync

# Run the CLI (interactive mode)
uv run coda

# One-shot mode
uv run coda --one-shot "Your prompt here"

# With specific model
uv run coda --model cohere.command-r-plus

# List available models
uv run coda --model list

# Debug mode
uv run coda --debug
```

### Configuration

First-time setup requires OCI configuration:
```bash
# Create config file
mkdir -p ~/.config/coda
echo '[oci]' > ~/.config/coda/config.toml
echo 'compartment_id = "your-compartment-id"' >> ~/.config/coda/config.toml

# Or use environment variable
export OCI_COMPARTMENT_ID="your-compartment-id"
```

## Development

This project uses:
- **uv**: For dependency management and virtual environments
- **Python 3.11+**: Modern Python features and type hints
- **OCI SDK**: Native Oracle Cloud Infrastructure integration
- **Rich**: Terminal formatting and UI components
- **Click**: CLI framework with decorator-based commands
- **Pydantic**: Data validation and type safety
- **httpx**: Async HTTP client for streaming support

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

Coda welcomes contributions! Current development priorities:

### Phase 2: Provider Architecture
- **LiteLLM Integration**: Add support for OpenAI, Anthropic, and other providers
- **Provider Management**: Dynamic provider loading and configuration
- **Model Standardization**: Unified model naming and capability detection

### Phase 3: Session Management
- **SQLite Backend**: Persistent conversation storage
- **Session Branching**: Fork conversations at any point
- **Import/Export**: Share and backup conversation history

### Phase 4: Enhanced CLI
- **Slash Commands**: `/help`, `/model`, `/session`, `/export`
- **Developer Modes**: Code generation, debugging, review workflows
- **Input Enhancements**: Multi-line input, file uploads, syntax highlighting

### Phase 5: Tool Integration
- **MCP Protocol**: Model Context Protocol tool support
- **Git Integration**: Repository analysis and commit assistance
- **Code Tools**: Linting, formatting, testing integration

### Git Commit Guidelines

When committing code that was generated or modified with AI assistance, please follow these guidelines:

1. **Include the user prompt** (scrubbed of PII) in the commit message
2. **List all AI tools used** during the implementation
3. **Do not squash commits** - preserve the development history and individual commit messages

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

MIT License - see [LICENSE](LICENSE) file for details

## Related Projects

Coda builds upon and integrates with:
- LiteLLM: Unified LLM API interface
- Model Context Protocol (MCP): Standardized tool integration
- Rich: Python terminal formatting library