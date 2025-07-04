# Coda Roadmap

## Project Vision
Build a multi-provider, CLI-focused code assistant that provides a unified interface for AI-powered development across Oracle OCI GenAI, Ollama, and other LiteLLM-supported providers.

## Reference Directories
Key directories for OCI GenAI implementation reference:
- **LangChain OCI Integration**: `/Users/danny/Developer/forks/litellm-oci-using-claude/langchain-community`
- **OCI Python SDK**: `/Users/danny/Developer/forks/litellm-oci-using-claude/oci-python-sdk`
- **LiteLLM Fork with OCI**: `/Users/danny/Developer/forks/litellm-oci-using-claude/litellm`


## Bugs & Fixes (Top Priority - Must be addressed before any phase work)

### Active Bugs
None currently - all bugs have been resolved!

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

### 1.5 Versioning
- [x] Version based on date/time
- [x] Automate CI versioning and release schedule

### 1.6 Branding
- [x] Project logo integration (terminal-themed design)
- [x] Logo variants for different contexts (PNG assets)

## Phase 2: Core Provider Architecture ✅ COMPLETED

### 2.1 Provider Interface Design
- [x] Create abstract base provider class (base.py)
- [x] Define standard methods: chat, chat_stream, list_models, get_model_info
- [x] Implement provider registry/factory pattern
- [x] Add provider configuration management

### 2.2 Additional Native Providers
- [x] **LiteLLM Provider** (Gateway to 100+ providers)
  - [x] Basic chat completion
  - [x] Streaming support
  - [x] Model discovery
  - [x] Error handling and retries
  
- [x] **Ollama Provider** (Local models)
  - [x] Direct API integration (no LiteLLM dependency)
  - [x] Model management (list, pull, delete)
  - [x] Streaming responses
  - [x] Health checks and auto-discovery

### 2.3 Unified Chat Interface
- [x] Create core chat engine
- [x] Message history management
- [x] System prompt handling
- [x] Token counting and limits
- [x] Response formatting

## Phase 3: Enhanced CLI Experience ✅ (Complete)

### 3.1 Interactive Shell ✅ (Complete)
- [x] Rich prompt with syntax highlighting using prompt-toolkit
- [x] Multi-line input support (use \ at end of line)
- [x] Command history and search (with file-based persistence)
- [x] Auto-completion for commands and file paths (Tab-only)
- [x] Keyboard shortcuts (Ctrl+C, Ctrl+D, arrow keys)
- [x] Clean interrupt handling during AI responses

### 3.2 Slash Commands ✅ (Complete for Phase 3)
- [x] `/help` (`/h`, `/?`) - Show available commands and keyboard shortcuts
- [x] `/model` (`/m`) - Interactive model selection with search
- [x] `/provider` (`/p`) - Switch providers (OCI GenAI supported)
- [x] `/mode` - Change AI personality with 7 modes
- [x] `/clear` (`/cls`) - Clear conversation (placeholder)
- [x] `/exit` (`/quit`, `/q`) - Exit application

### 3.3 Developer Modes ✅ (Complete)
- [x] **General Mode**: Default conversational AI assistant
- [x] **Code Mode**: Optimized for writing new code with best practices
- [x] **Debug Mode**: Focus on error analysis and debugging assistance
- [x] **Explain Mode**: Detailed code explanations and documentation
- [x] **Review Mode**: Security and code quality review
- [x] **Refactor Mode**: Code improvement and optimization suggestions
- [x] **Plan Mode**: Architecture planning and system design

### 3.4 Additional Features Implemented
- [x] Interactive vs Basic mode selection based on TTY detection
- [x] Model deduplication in selection UI
- [x] Multi-level tab completion for slash commands
- [x] Empty input validation to save API credits
- [x] Proper signal handling for clean exits

## Phase 4: Session Management

### 4.1 Persistence Layer
- [ ] SQLite database for sessions
- [ ] Message storage with metadata
- [ ] Full-text search across sessions
- [ ] Session branching and merging

### 4.2 Session Commands
- [ ] `/session` (`/s`) - Save/load/branch conversations
  - [ ] `save` - Save current conversation
  - [ ] `load` - Load a saved conversation
  - [ ] `list` - List all saved sessions
  - [ ] `branch` - Create a branch from current conversation
  - [ ] `delete` - Delete a saved session
- [ ] `/export` (`/e`) - Export conversations
  - [ ] `markdown` - Export as Markdown file
  - [ ] `json` - Export as JSON with metadata
  - [ ] `txt` - Export as plain text
  - [ ] `html` - Export as HTML with syntax highlighting

### 4.3 Context Management
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

### 5.2 Tool Commands
- [ ] `/tools` (`/t`) - Manage MCP tools
  - [ ] `list` - List available MCP tools
  - [ ] `enable` - Enable specific tools
  - [ ] `disable` - Disable specific tools
  - [ ] `config` - Configure tool settings
  - [ ] `status` - Show tool status

### 5.3 MCP Protocol
- [ ] MCP server implementation
- [ ] Tool discovery and registration
- [ ] Permission management
- [ ] Custom tool development SDK

## Phase 6: Advanced Features

### 6.1 Multi-Modal Support
- [ ] Image understanding (for providers that support it)
- [ ] Code screenshot analysis
- [ ] Important documents to support
    - [ ] PDF support
    - [ ] Microsoft Word doc support
    - [ ] Microsoft Powerpoint support
    - [ ] Microsoft Excel support
- [ ] Diagram generation
- [ ] Use [diagram-renderer](https://github.com/djvolz/diagram-renderer)

### 6.2 Project Intelligence
- [ ] Automatic project type detection
- [ ] Specifically handle multiple version control systems beyond just git. Very important.
- [ ] Language-specific optimizations
- [ ] Dependency awareness
- [ ] Test generation
- [ ] Support for external projects (work on codebases outside current directory)
- [ ] Multi-project management (handle multiple projects simultaneously)

### 6.3 UI Customization
- [ ] `/theme` - Change UI theme
  - [ ] `default` - Default color scheme
  - [ ] `dark` - Dark mode optimized
  - [ ] `light` - Light terminal theme
  - [ ] `minimal` - Minimal colors
  - [ ] `vibrant` - High contrast colors
- [ ] **Enhanced Response Rendering**
  - [ ] Live markdown rendering during streaming
  - [ ] Syntax highlighting for code blocks
  - [ ] Proper handling of tables and lists
  - [ ] Toggle between raw and formatted view
  - [ ] Preserve terminal scrollback while rendering

### 6.4 Collaboration Features
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
- [ ] Session management UI

## Phase 8: Other. Too be categorized
- [ ] Opentelemetry support
    - [ ] Metrics for daily active users and other telemetry
- [ ] Pyroscope for debugging
- [ ] Containerize coda and package ollama by default
- [ ] Compacting conversation to automatically handle context
- [ ] Repo mapping like [aider](https://aider.chat/docs/repomap.html)
    - [ ] tree-sitter using [aider ts implementation](https://github.com/Aider-AI/aider/tree/main/aider/queries)
        - [ ] Make sure to support documentation, function, class, struct, etc (not just ref and def like aider does)
- [ ] Our own wiki update checker
- [ ] Changelog detecter
- [ ] Given any two points in the code (hash to hash but make this VCS agnostic) generate a changelog
- [ ] Review code helper


## Technical Decisions

### Architecture
- **Async First**: Use asyncio throughout for better performance
- **Plugin System**: Providers and tools as plugins
- ** Modularity **: We want to make this code as modular as possible so other projects can use self-contained pieces as APIs (without the need for our UI)
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

### Versioning & Release Strategy
- Date-based versioning: `year.month.day.HHMM`
- Automated releases via conventional commits
- Continuous delivery on main branch
- No manual version management required

## Development Workflow

### Branch Strategy & Release Pipeline
- `main`: Stable releases (production-ready)
- `develop`: Integration branch (staging)
- `feature/*`: Feature branches (development)
- `fix/*`: Bug fixes

**Future Enhancement**: Implement dev → staging → stable pipeline
- Automated testing gates between stages
- Staging environment for pre-release validation
- Stable releases with semantic versioning

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

### 2025.7.2 - OCI Foundation ✅ COMPLETED
- ✅ Native OCI GenAI provider implementation
- ✅ Basic chat completion support
- ✅ Streaming responses
- ✅ Functional CLI with interactive and one-shot modes
- ✅ Dynamic model discovery (30+ models)
- ✅ Configuration file support

### 2025.7.3 - Versioning & Release Automation ✅ COMPLETED
- ✅ Date-based versioning (year.month.day.HHMM format)
- ✅ Automated release workflow with GitHub Actions
- ✅ Conventional commits support
- ✅ Automatic changelog generation
- ✅ Version display in CLI (--version flag and banner)
- ✅ Release documentation and contributing guidelines
- ✅ PyPI upload preparation
- ✅ Git commit message template

### 2025.7.5 - Provider Architecture ✅ COMPLETED
- ✅ Abstract provider interface with BaseProvider class
- ✅ Provider registry and factory pattern
- ✅ LiteLLM integration (100+ providers)
- ✅ Ollama native support with streaming
- ✅ Configuration management system
- ✅ Multi-source config priority (CLI > env > project > user > defaults)

### 2025.7.4 - Enhanced CLI ✅ COMPLETED
- ✅ Interactive shell with prompt-toolkit
- ✅ Slash commands (/help, /model, /mode, etc.)
- ✅ 7 Developer modes (general, code, debug, explain, review, refactor, plan)
- ✅ Rich UI features (tab completion, history, keyboard shortcuts)
- ✅ Model deduplication and interactive selection
- ✅ Improved error handling and user experience
- ✅ **Phase 2 & 3 Integration** (July 4):
  - ✅ Merged provider factory pattern with interactive CLI
  - ✅ All providers work seamlessly in interactive mode
  - ✅ Refactored code for better maintainability
  - ✅ Added integration tests and configuration externalization

### 2025.7.10 - Persistence (Target: July 10)
- Session management
- Context handling
- Search functionality

### 2025.7.12 - Tools (Target: July 12)
- MCP integration
- Core tool set
- Custom tools

### 2025.7.15 - Production Ready (Target: July 15)
- Full test coverage
- Documentation
- Performance optimized
- Stable API

## Next Steps

**Current Status**: Phase 3 complete with Phase 2 integration. Ready for PR to main branch.

1. **Immediate**: Create pull request for Phase 3 (Enhanced CLI Experience)
   - Merge feature/enhanced-cli-experience into main
   - Includes all interactive CLI features and provider integration
   
2. Begin Phase 4: Session Management
   - SQLite database for sessions
   - Message persistence with metadata
   - Session branching and search
   - Full-text search across sessions
   
3. Implement MCP (Model Context Protocol) integration
   - Core tools for file operations
   - Shell command execution
   - Web search and fetch capabilities
   
4. Add multi-modal support
   - Image understanding for supported providers
   - Code screenshot analysis
   - PDF and document support

## Notes

- Priority on developer experience
- Keep CLI as primary interface
- Web UI is optional/secondary
- Focus on reliability and performance
- Maintain compatibility with existing LiteLLM code

## Completed Items

### Project Branding (2025.7.3)
- [x] Extract logo assets from `/tmp/logo.html` 
- [x] Create `assets/logos/` directory structure
- [x] Generate logo files in multiple formats:
  - [x] SVG (scalable, main format)
  - [x] PNG (64x64, 128x128, 256x256, 512x512, 1024x1024)
  - [x] ICO (favicon)
- [x] Integrate logos into:
  - [x] README.md header
  - [x] Add all three logo variants from original design
  - [ ] Documentation (when created)
  - [ ] Future web UI  
  - [ ] GitHub social preview
- [x] Add logo usage guidelines to documentation

### Bugs Fixed (2025.7.3)
- [x] **Fix CI pipeline** - Resolved version extraction error by using portable grep syntax instead of -P flag
- [x] **Fix uv sync bug on other machine** - Identified as VPN/proxy interference, added general troubleshooting guide
- [x] **Add Python 3.13 support** - Updated test matrices, Black configuration, and documentation
- [x] **Remove dedicated flag for compartment-id** - Removed provider-specific CLI flag; now uses env var or config file

### Phase 2: Provider Architecture (2025.7.4)
- [x] **Abstract Provider Interface** - Created BaseProvider ABC with standard methods
- [x] **Provider Registry/Factory** - Dynamic provider registration and instantiation
- [x] **Configuration Management** - Multi-source config with priority hierarchy
- [x] **LiteLLM Provider** - Access to 100+ LLM providers via unified API
- [x] **Ollama Provider** - Native integration for local model execution
- [x] **CLI Updates** - Support for all providers with model selection
- [x] **Comprehensive Tests** - Unit and integration tests for all components
