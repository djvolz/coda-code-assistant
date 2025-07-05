<div align="center">
  <img src="assets/logos/coda-terminal-logo.svg" alt="Coda Terminal Logo" width="400" height="280">
  
  # Coda - Code Assistant
  
  A powerful, multi-provider AI code assistant that brings the best of AI-powered development directly to your terminal.
</div>

---

Coda seamlessly integrates with multiple AI providers while maintaining a consistent, developer-friendly interface.

## ✨ What is Coda?

Coda is your AI pair programmer that:
- 🚀 **Lives in your terminal**: Works right where you code, integrated into your development workflow
- 🔌 **Connects to any AI**: Use Oracle OCI GenAI, local Ollama models, OpenAI, Anthropic, or any LiteLLM-supported provider
- 💻 **Thinks like a developer**: Specialized modes for writing, debugging, explaining, and reviewing code
- 🔄 **Remembers context**: Save and resume conversations, branch off interesting threads
- 🛠️ **Takes action**: Integrated tools for file operations, web searches, and more via Model Context Protocol (MCP)

## 🎯 Key Features

- 🌐 **Multi-Provider Support**: Oracle OCI GenAI, Ollama (local), OpenAI, Anthropic, Google, and 100+ more via LiteLLM
- 💻 **CLI-First Design**: Built for developers who live in the terminal
- 🧠 **[Smart Modes](docs/modes.md)**: Specialized AI personalities for different tasks (code, debug, explain, review)
- 💾 **Session Management**: Never lose a conversation - save, resume, and branch discussions
- 🎨 **Beautiful Interface**: Rich terminal UI with syntax highlighting and multiple themes
- ⚡ **Real-time Streaming**: See responses as they're generated
- 🔧 **Tool Integration**: File operations, web search, and custom tools via MCP
- 🌈 **Customizable**: Themes, key bindings, and behavior settings

## 📦 Installation

```bash
# Clone the repository
git clone https://github.com/djvolz/coda-code-assistant.git
cd coda-code-assistant

# Install with uv (recommended)
uv sync

# Run Coda
uv run coda
```

## 🚀 Quick Start

### Basic Usage

```bash
# Start interactive chat with OCI GenAI (auto-selects model)
uv run coda

# Use a specific model
uv run coda --model cohere.command-r-plus-08-2024

# One-shot command (no interaction needed)
uv run coda --one-shot "What is the capital of France?"

# Enable debug output
uv run coda --debug
```

### Provider Setup

#### 🏠 Ollama (Local, No API Key Required)
```bash
# Install Ollama from https://ollama.ai
ollama pull llama3.1
ollama serve  # Run in separate terminal
uv run coda --provider ollama
```

#### ☁️ Oracle OCI GenAI
```bash
# Set compartment ID via environment variable
export OCI_COMPARTMENT_ID="ocid1.compartment.oc1..."
uv run coda --provider oci_genai --model cohere.command-r-plus

# Or configure in ~/.config/coda/config.toml:
# [providers.oci_genai]
# compartment_id = "ocid1.compartment.oc1..."
```

#### 🤖 OpenAI
```bash
export OPENAI_API_KEY="sk-..."
uv run coda --provider openai --model gpt-4
```

## 💡 Usage Examples

### Developer Modes
```bash
# Start with a specific mode
uv run coda --mode code

# Switch modes during conversation
You: /mode debug
You: Why am I getting "undefined is not a function"?

You: /mode explain  
You: How does async/await work in JavaScript?

You: /mode review
You: Check this SQL query for security issues: SELECT * FROM users WHERE id = ${userId}
```

See the [Developer Modes Guide](docs/modes.md) for detailed information about each mode.

### Session Management
```bash
# Save your conversation
/sessions save my-feature-discussion

# List previous sessions
/sessions list

# Resume a session
/sessions load my-feature-discussion
```

### Customization
```bash
# Change theme
/theme dracula

# Export conversation
/export markdown conversation.md

# Configure settings
/config edit
```

## 🛠️ Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run black .
uv run ruff check --fix .

# Type checking
uv run mypy coda
```

## 🏗️ Architecture

Coda is built with a modular architecture:

```
coda/
├── core/       # Core chat engine and session management
├── providers/  # AI provider implementations
├── cli/        # Terminal interface and commands
├── tools/      # MCP tool integrations
├── config/     # Configuration management
└── utils/      # Shared utilities
```

## 📚 Documentation

- [Developer Modes Guide](docs/modes.md) - Complete guide to using specialized AI modes
- [Roadmap](ROADMAP.md) - Roadmap and technical architecture
- [OCI GenAI Integration](docs/oci-genai-integration.md) - Deep dive into Oracle Cloud integration
- [Test Suite Documentation](tests/README.md) - Testing strategy and guidelines
- [AI Assistant Guidelines](AGENTS.md) - Guidelines for AI-assisted development

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) and check out our [AGENTS.md](AGENTS.md) file for AI-assisted development guidelines.

### Commit Convention
We use [Conventional Commits](https://www.conventionalcommits.org/) for automated releases. Format:
```
feat(scope): add new feature
fix(scope): fix bug
```

## 🏷️ Versioning

Coda uses date-based versioning in the format: `year.month.day.HHMM`

- Example: `2025.1.3.1430` for January 3, 2025 at 14:30 UTC
- To update version: `make version`
- Version is automatically shown in CLI with `coda --version`

## 📝 License

MIT License - see [LICENSE](LICENSE) file for details

## 🙏 Acknowledgments

Built with:
- [LiteLLM](https://github.com/BerriAI/litellm) - Unified LLM API
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Advanced CLI interactions
- [Model Context Protocol](https://modelcontext.dev/) - Tool integration standard