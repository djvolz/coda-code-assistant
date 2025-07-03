# 🤖 Coda - Code Assistant

A powerful, multi-provider AI code assistant that brings the best of AI-powered development directly to your terminal. Coda seamlessly integrates with multiple AI providers while maintaining a consistent, developer-friendly interface.

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
- 🧠 **Smart Modes**: Specialized AI personalities for different tasks (code, debug, explain, review)
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
# Start interactive chat with default provider (Ollama)
uv run coda

# Use a specific provider
uv run coda --provider openai --model gpt-4
uv run coda --provider oci --model cohere.command-r-plus

# One-shot command
uv run coda --one-shot "explain this regex: ^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
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
export OCI_COMPARTMENT_ID="ocid1.compartment.oc1..."
uv run coda --provider oci --model cohere.command-r-plus
```

#### 🤖 OpenAI
```bash
export OPENAI_API_KEY="sk-..."
uv run coda --provider openai --model gpt-4
```

## 💡 Usage Examples

### Interactive Development
```bash
# Start a coding session
uv run coda

# In the chat:
You: /mode code
You: Write a Python function to parse JSON with error handling
You: /mode debug
You: Help me fix this TypeError in @main.py
You: /mode review
You: Review the security of @auth.py
```

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

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guidelines](CONTRIBUTING.md) and check out our [AGENTS.md](AGENTS.md) file for AI-assisted development guidelines.

## 📝 License

[To be determined]

## 🙏 Acknowledgments

Built with:
- [LiteLLM](https://github.com/BerriAI/litellm) - Unified LLM API
- [Rich](https://github.com/Textualize/rich) - Beautiful terminal formatting
- [Prompt Toolkit](https://github.com/prompt-toolkit/python-prompt-toolkit) - Advanced CLI interactions
- [Model Context Protocol](https://modelcontext.dev/) - Tool integration standard