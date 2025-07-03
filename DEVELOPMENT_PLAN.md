# Coda Development Plan

## Project Vision
Build a multi-provider, CLI-focused code assistant that provides a unified interface for AI-powered development across Oracle OCI GenAI, Ollama, and other LiteLLM-supported providers.

## Reference Directories
Key directories for OCI GenAI implementation reference:
- **LangChain OCI Integration**: `/Users/danny/Developer/forks/litellm-oci-using-claude/langchain-community`
- **OCI Python SDK**: `/Users/danny/Developer/forks/litellm-oci-using-claude/oci-python-sdk`
- **LiteLLM Fork with OCI**: `/Users/danny/Developer/forks/litellm-oci-using-claude/litellm`

## Phase 1: Native OCI GenAI Integration (Current Priority)

### 1.1 Study Reference Implementations
- [x] Review LangChain OCI integration patterns
- [x] Understand OCI Python SDK usage for GenAI
- [x] Analyze LiteLLM fork's OCI implementation
- [x] Document key learnings and patterns

**Key Findings:**
- Authentication: 4 methods (API_KEY, SECURITY_TOKEN, INSTANCE_PRINCIPAL, RESOURCE_PRINCIPAL)
- Service endpoint: `https://inference.generativeai.{region}.oci.oraclecloud.com`
- Model naming: `provider.model-name-version` format
- Message format varies by provider (Cohere vs Meta)
- Streaming uses SSE format with custom iterator
- Comprehensive error mapping required

### 1.2 OCI Provider Implementation
- [x] **Setup & Configuration**
  - [x] Add OCI SDK dependency
  - [x] Create OCI config reader (support ~/.oci/config)
  - [x] Handle compartment ID configuration
  - [x] Region detection and endpoint construction

- [x] **Core Integration**
  - [x] Create OCIGenAIProvider class
  - [x] Implement authentication using OCI config
  - [x] Add chat completion method
  - [x] Add streaming support
  - [x] Handle OCI-specific parameters (temperature, max_tokens, etc.)

- [x] **Model Support**
  - [x] Cohere Command models (command-r-plus, command-r, command-a-03-2025, etc.)
  - [x] Meta Llama models (llama-3.1, llama-3.3, llama-4, etc.)
  - [x] xAI Grok models (grok-3, grok-3-fast, grok-3-mini, etc.)
  - [x] Dynamic model discovery via OCI GenAI API
  - [x] Model caching for performance (24-hour cache)
  - [x] Automatic mapping between friendly names and OCI model IDs
  - [x] Model-specific parameter validation

- [x] **Error Handling**
  - [x] OCI service errors
  - [x] Authentication failures
  - [x] Rate limiting
  - [x] Network errors

### 1.3 Testing & Validation
- [x] Unit tests with mocked OCI responses (created test_oci_provider.py)
- [x] Integration tests (with real OCI if available)
- [ ] Performance benchmarks
- [x] Example scripts (created demo_oci.py)

### 1.4 CLI Integration
- [x] **Functional CLI Entry Point**
  - [x] Interactive chat mode with model selection
  - [x] One-shot execution mode
  - [x] Streaming response display
  - [x] Rich terminal UI with colors and formatting
  - [x] Debug mode support

- [x] **Configuration Management**
  - [x] Config file support (~/.config/coda/config.toml)
  - [x] Environment variable fallback
  - [x] Command-line parameter override
  - [x] Multi-source configuration priority

- [x] **User Experience**
  - [x] Model selection interface (top 10 models)
  - [x] Auto-selection for one-shot mode
  - [x] Clear error messages and setup guidance
  - [x] Exit/clear commands in interactive mode

## Phase 2: Core Provider Architecture

### 2.1 Provider Interface Design
- [x] Create abstract base provider class (base.py)
- [x] Define standard methods: chat, chat_stream, list_models, get_model_info
- [ ] Implement provider registry/factory pattern
- [ ] Add provider configuration management

### 2.2 Additional Native Providers
- [ ] **LiteLLM Provider** (Gateway to 100+ providers)
  - [ ] Basic chat completion
  - [ ] Streaming support
  - [ ] Model discovery
  - [ ] Error handling and retries
  
- [ ] **Ollama Provider** (Local models)
  - [ ] Direct API integration (no LiteLLM dependency)
  - [ ] Model management (list, pull, delete)
  - [ ] Streaming responses
  - [ ] Health checks and auto-discovery

### 2.3 Unified Chat Interface
- [ ] Create core chat engine
- [ ] Message history management
- [ ] System prompt handling
- [ ] Token counting and limits
- [ ] Response formatting

## Phase 3: Enhanced CLI Experience

### 3.1 Interactive Shell
- [ ] Rich prompt with syntax highlighting
- [ ] Multi-line input support
- [ ] Command history and search
- [ ] Auto-completion for commands and file paths

### 3.2 Slash Commands
- [ ] `/help` - Context-aware help
- [ ] `/model` - Switch models on the fly
- [ ] `/provider` - Switch providers
- [ ] `/mode` - Change AI personality (code, debug, explain, review)
- [ ] `/session` - Save/load/branch conversations
- [ ] `/theme` - Change UI theme
- [ ] `/export` - Export conversations
- [ ] `/tools` - Manage MCP tools

### 3.3 Developer Modes
- [ ] **Code Mode**: Optimized for writing new code
- [ ] **Debug Mode**: Focus on error analysis and fixes
- [ ] **Explain Mode**: Code explanation and documentation
- [ ] **Review Mode**: Security and best practices review
- [ ] **Refactor Mode**: Code improvement suggestions

## Phase 4: Session Management

### 4.1 Persistence Layer
- [ ] SQLite database for sessions
- [ ] Message storage with metadata
- [ ] Full-text search across sessions
- [ ] Session branching and merging

### 4.2 Context Management
- [ ] Intelligent context windowing
- [ ] File reference tracking (@mentions)
- [ ] Context summarization for long sessions
- [ ] Project-aware context

## Phase 5: Tool Integration (MCP)

### 5.1 Core Tools
- [ ] File operations (read, write, edit)
- [ ] Shell command execution
- [ ] Web search and fetch
- [ ] Git operations

### 5.2 MCP Protocol
- [ ] MCP server implementation
- [ ] Tool discovery and registration
- [ ] Permission management
- [ ] Custom tool development SDK

## Phase 6: Advanced Features

### 6.1 Multi-Modal Support
- [ ] Image understanding (for providers that support it)
- [ ] Code screenshot analysis
- [ ] Diagram generation

### 6.2 Project Intelligence
- [ ] Automatic project type detection
    - [ ] Specifically handle multiple version control systems beyond just git. Very important.
- [ ] Language-specific optimizations
- [ ] Dependency awareness
- [ ] Test generation

### 6.3 Collaboration Features
- [ ] Session sharing via URLs
- [ ] Team knowledge base
- [ ] Shared prompt library

## Phase 7: Web UI (Streamlit)

### 7.1 Dashboard
- [ ] Provider status and health
- [ ] Model selection and comparison
- [ ] Usage statistics
    - [ ] Add the token usage stats on session end like [gemini cli](https://github.com/google-gemini/gemini-cli)
- [ ] Cost tracking (for paid providers)

### 7.2 Chat Interface
- [ ] Web-based chat UI
- [ ] Code highlighting
- [ ] File upload/download
    - [ ] PDF and image support
- [ ] Session management UI

## Phase 8: Other. Too be categorized
- [ ] Set up github pipeline
- [ ] Opentelemetry support
    - [ ] Metrics for daily active users and other telemetry
- [ ] Pyroscope for debugging
- [ ] Containerize coda and package ollama by default
- [ ] Compacting conversation to automatically handle context
- [ ] Repo mapping like [aider](https://aider.chat/docs/repomap.html)
    - [ ] tree-sitter using [aider ts implementation](https://github.com/Aider-AI/aider/tree/main/aider/queries)
        - [ ] Make sure to support documentation, function, class, struct, etc (not just ref and def like aider does)
- [ ] Wiki update checker
- [ ] Changelog detecter
- [ ] Review code helper
- [ ] Ability to add external projects
- [ ] Ability to add multiple projects


## Technical Decisions

### Architecture
- **Async First**: Use asyncio throughout for better performance
- **Plugin System**: Providers and tools as plugins
- **Type Safety**: Full type hints and mypy compliance
- **Testing**: Comprehensive test suite with mocked providers

### Dependencies
- **Core**: litellm, httpx, pydantic
- **CLI**: rich, prompt-toolkit, click
- **Storage**: sqlalchemy, aiosqlite
- **Web**: streamlit (optional)

### Configuration
- Follow XDG Base Directory spec
- TOML configuration files
- Environment variable overrides
- Per-project settings

## Development Workflow

### Branch Strategy
- `main`: Stable releases
- `develop`: Integration branch
- `feature/*`: Feature branches
- `fix/*`: Bug fixes

### Testing Strategy
- Unit tests for each provider
- Integration tests for CLI commands
- Mock providers for testing
- Performance benchmarks

### Documentation
- API documentation (Sphinx)
- User guide with examples
- Provider setup guides
- Contributing guidelines

## Milestones

### v0.1.0 - OCI Foundation (Week 1-2) ✅ COMPLETED
- ✅ Native OCI GenAI provider implementation
- ✅ Basic chat completion support
- ✅ Streaming responses
- ✅ Functional CLI with interactive and one-shot modes
- ✅ Dynamic model discovery (30+ models)
- ✅ Configuration file support

### v0.2.0 - Provider Architecture (Week 3-4)
- Abstract provider interface
- Provider registry
- LiteLLM integration
- Ollama native support

### v0.3.0 - Enhanced CLI (Week 5-6)
- Slash commands
- Developer modes
- Rich UI features

### v0.4.0 - Persistence (Week 7-8)
- Session management
- Context handling
- Search functionality

### v0.5.0 - Tools (Week 9-10)
- MCP integration
- Core tool set
- Custom tools

### v1.0.0 - Production Ready
- Full test coverage
- Documentation
- Performance optimized
- Stable API

## Next Steps

1. Create feature branch for native OCI integration
2. Study reference implementations in provided directories
3. Set up OCI SDK dependency
4. Implement OCIGenAIProvider class
5. Create basic test script for OCI chat completion
6. Build streaming support
7. Add comprehensive error handling

## Notes

- Priority on developer experience
- Keep CLI as primary interface
- Web UI is optional/secondary
- Focus on reliability and performance
- Maintain compatibility with existing LiteLLM code
