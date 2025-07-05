# Coda Roadmap

## Project Vision
Build a multi-provider, CLI-focused code assistant that provides a unified interface for AI-powered development across Oracle OCI GenAI, Ollama, and other LiteLLM-supported providers.

## Current State & Priorities

✅ **Completed Phases**:
- **Phase 1**: Native OCI GenAI Integration (30+ models, streaming, dynamic discovery)
- **Phase 2**: Core Provider Architecture (LiteLLM, Ollama, provider registry)
- **Phase 3**: Enhanced CLI Experience (interactive shell, slash commands, developer modes)

✅ **Phase 4**: Session Management - COMPLETED (July 5, 2025) | 🚧 Enhancement 4.5 Pending
- SQLite persistence layer (stored in ~/.cache/coda/sessions.db)
- Session commands (/session save/load/list/branch/delete/info/search)
- Export commands (/export json/markdown/txt/html)
- Full-text search across sessions
- Context optimization for token limits
- MockProvider for deterministic testing

🚧 **Current Focus**: Phase 5 - Tool Integration (MCP) - Target: July 12

📅 **Upcoming**:
- Phase 6: Advanced Features - July 15
- Phase 7: Web UI (Streamlit)
- Phase 8: Additional features

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

## Phase 2: Core Provider Architecture ✅ COMPLETED (July 4, 2025)

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

## Phase 3: Enhanced CLI Experience ✅ COMPLETED (July 4, 2025)

### 3.1 Interactive Shell ✅ 
- [x] Rich prompt with syntax highlighting using prompt-toolkit
- [x] Multi-line input support (use \ at end of line)
- [x] Command history and search (with file-based persistence)
- [x] Auto-completion for commands and file paths (Tab-only)
- [x] Keyboard shortcuts (Ctrl+C, Ctrl+D, arrow keys)
- [x] Clean interrupt handling during AI responses

### 3.2 Slash Commands ✅ 
- [x] `/help` (`/h`, `/?`) - Show available commands and keyboard shortcuts
- [x] `/model` (`/m`) - Interactive model selection with search
- [x] `/provider` (`/p`) - Switch providers (OCI GenAI supported)
- [x] `/mode` - Change AI personality with 7 modes
- [x] `/clear` (`/cls`) - Clear conversation (placeholder)
- [x] `/exit` (`/quit`, `/q`) - Exit application

### 3.3 Developer Modes ✅ 
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

**⚠️ PARALLEL DEVELOPMENT NOTE**: Phase 4 and 5 are being developed in parallel on separate branches. To minimize merge conflicts:
- Phase 4 branch: `feature/session-management` (focuses on persistence layer)
- Phase 5 branch: `feature/mcp-tools` (focuses on tool execution)
- Integration points: Session schema will need `tool_invocations` table from Phase 5
- Merge strategy: Phase 4 merges first, then Phase 5 rebases and adds tool logging

### 4.1 Persistence Layer ✅ COMPLETED
- [x] SQLite database for sessions (stored in `~/.cache/coda/sessions.db`)
- [x] Message storage with metadata and provider/model tracking
- [x] Full-text search across sessions with FTS5
- [x] Session branching with parent-child relationships
- [x] Database initialization with schema creation
- [x] Tags and session metadata support

### 4.2 Session Commands ✅ COMPLETED
- [x] `/session` (`/s`) - Save/load/branch conversations
  - [x] `save [name]` - Save current conversation with optional name
  - [x] `load <id|name>` - Load a saved session by ID or name
  - [x] `list` - List all saved sessions with metadata
  - [x] `branch [name]` - Create a branch from current conversation
  - [x] `delete <id|name>` - Delete a saved session with confirmation
  - [x] `info [id]` - Show detailed session information
  - [x] `search <query>` - Full-text search across all sessions
- [x] `/export` (`/e`) - Export conversations
  - [x] `json` - Export as JSON with full metadata
  - [x] `markdown` (`md`) - Export as Markdown file
  - [x] `txt` (`text`) - Export as plain text
  - [x] `html` - Export as HTML with syntax highlighting

### 4.3 Context Management ✅ COMPLETED
- [x] Intelligent context windowing based on model limits
- [x] Context optimization with token counting
- [x] Message prioritization (system > recent > historical)
- [x] Conversation memory preserved across save/load cycles

### 4.4 Testing Infrastructure ✅ COMPLETED
- [x] MockProvider for deterministic, offline testing
- [x] Comprehensive test coverage (51 conversation tests)
- [x] Tests for all CLI commands and developer modes
- [x] Session workflow end-to-end tests
- [x] Edge case and error handling tests

### 4.5 Automatic Session Saving (Enhancement)
- [x] **Auto-Save by Default** ✅ COMPLETED
  - [x] Automatic session creation on first message
  - [x] Anonymous sessions with timestamp names (e.g., `auto-20250105-143022`)
  - [x] Zero configuration required - just start chatting
  - [ ] Async saves to avoid blocking chat flow
  
- [ ] **Rolling Window Management** (Option 1 - Recommended)
  - [ ] Keep last 1000 messages per session
  - [ ] Archive older messages to linked archive sessions
  - [ ] Maintain parent-child relationships for full history
  - [ ] Transparent access to archived content via search
  
- [x] **User Control Options** ✅ COMPLETED
  - [x] `/session rename` - Rename auto-created sessions
  - [x] `--no-save` CLI flag - Opt out for sensitive conversations
  - [x] Config option: `auto_save_enabled = true/false` (uses existing `autosave`)
  - [x] Bulk delete options for privacy (`/session delete-all [--auto-only]`)
  
- [x] **Additional Features** ✅ COMPLETED
  - [x] `/session last` - Load most recent session
  - [x] `--resume` CLI flag - Auto-load last session on startup
  
- [x] **Performance Optimizations** ✅ PARTIALLY COMPLETED
  - [ ] Batch message inserts for efficiency
  - [ ] Background save queue to prevent UI blocking
  - [x] Index on created_at for fast queries
  - [x] Additional indexes for name, accessed_at, parent_id, and tags
  - [ ] Lazy loading of historical messages
  
- [x] **Privacy & Disclosure** ✅ MOSTLY COMPLETED
  - [x] Clear notification about auto-save on first run
  - [x] Easy bulk delete commands (`/session delete-all`)
  - [ ] Optional encryption for stored sessions
  - [x] Respect XDG data directories (already implemented)

- [x] **Command System Refactoring** ✅ MOSTLY COMPLETED
  - [x] Centralized CommandRegistry for single source of truth
  - [x] Consistent autocomplete from registry definitions
  - [x] Dynamic help text generation from registry
  - [x] Updated help display to show implemented commands
  - [ ] Full command initialization from registry (lower priority)

## Phase 5: Tool Integration (MCP)

**⚠️ PARALLEL DEVELOPMENT NOTE**: Being developed in parallel with Phase 4. Key considerations:
- Work on branch: `feature/mcp-tools`
- Mock the session storage API during development
- Plan for adding `tool_invocations` to session schema after merge
- Avoid modifying core files that Phase 4 is likely to change (cli/main.py, config.py)
- Focus on creating new files: `tools/`, `mcp/` directories

### 5.1 Core Tools
- [ ] File operations (read, write, edit)
- [ ] Shell command execution
- [ ] Web search and fetch
- [ ] Git operations
- [ ] **Tool Result Storage**: Design format for session integration

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

### 2025.7.4 - Provider Architecture & Enhanced CLI ✅ COMPLETED
**Phase 2 - Provider Architecture**:
- ✅ Abstract provider interface with BaseProvider class
- ✅ Provider registry and factory pattern
- ✅ LiteLLM integration (100+ providers)
- ✅ Ollama native support with streaming
- ✅ Configuration management system
- ✅ Multi-source config priority (CLI > env > project > user > defaults)

**Phase 3 - Enhanced CLI Experience**:
- ✅ Interactive shell with prompt-toolkit
- ✅ Slash commands (/help, /model, /mode, etc.)
- ✅ 7 Developer modes (general, code, debug, explain, review, refactor, plan)
- ✅ Rich UI features (tab completion, history, keyboard shortcuts)
- ✅ Model deduplication and interactive selection
- ✅ Improved error handling and user experience

**Integration Notes**:
- ✅ Successfully merged concurrent Phase 2 & 3 development
- ✅ Resolved conflicts in 4 files during integration
- ✅ All Phase 3 CLI features work with Phase 2 provider system
- ✅ Multi-provider support in interactive mode (OCI GenAI, LiteLLM, Ollama)
- ✅ Code refactoring: 220-line function split into focused helpers
- ✅ Comprehensive test coverage for slash commands

### 2025.7.5 - Session Management ✅ COMPLETED (Phase 4)
**Session Infrastructure**:
- ✅ SQLAlchemy-based session database with automatic migrations
- ✅ Full session management system (create, save, load, branch, delete)
- ✅ Message persistence with provider/model metadata tracking
- ✅ Full-text search across all sessions using SQLite FTS5
- ✅ Session branching for exploring alternate conversation paths
- ✅ Export functionality (JSON, Markdown, TXT, HTML)

**MockProvider Implementation**:
- ✅ Deterministic mock provider for offline testing
- ✅ Context-aware responses for Python, decorators, JavaScript
- ✅ Conversation memory tracking ("what were we discussing?")
- ✅ Two models: mock-echo (4K) and mock-smart (8K)
- ✅ Full streaming support

**Comprehensive Testing**:
- ✅ 51 tests for MockProvider conversations
- ✅ Tests for all 7 developer modes
- ✅ Tests for both mock models (echo/smart)
- ✅ Tests for all CLI commands
- ✅ End-to-end session workflow tests
- ✅ Edge case and error handling coverage

**CLI Integration**:
- ✅ /session command with 7 subcommands
- ✅ /export command with 4 formats
- ✅ Seamless integration with existing interactive shell
- ✅ Conversation continuity across save/load cycles


### 2025.7.12 - Tool Integration / MCP (Target: July 12)
- MCP server implementation
- Core tools (file ops, shell, web search, git)
- Tool commands (/tools list/enable/disable/config/status)
- Permission management
- Custom tool SDK

### 2025.7.15 - Advanced Features (Target: July 15)
- Multi-modal support (image understanding)
- Document support (PDF, Word, PowerPoint, Excel)
- Enhanced response rendering (live markdown)
- Project intelligence (VCS support, language optimizations)
- UI customization (/theme command)

## Next Steps

**Current Status**: Phases 1, 2, 3, and 4 are complete. Phase 4.5 (Auto-Save Enhancement) pending. Ready to begin Phase 5.

1. **Completed - Phase 4**: Session Management ✅
   - SQLite database stored in `~/.cache/coda/sessions.db`
   - Message persistence with provider/model metadata
   - Session branching with parent-child relationships
   - Full-text search using SQLite FTS5
   - Complete implementation of `/session` and `/export` commands
   - MockProvider for deterministic testing
   - 100+ tests covering all session functionality
   
2. **Next - Phase 5**: Tool Integration (MCP) (Target: July 12)
   - Core tools for file operations
   - Shell command execution
   - Web search and fetch capabilities
   - Git operations
   - Implementation of `/tools` command
   
3. **Following - Phase 6**: Advanced Features (Target: July 15)
   - Multi-modal support (image understanding)
   - Code screenshot analysis
   - Document support (PDF, Word, PowerPoint, Excel)
   - Enhanced response rendering with live markdown
   
4. **Future Phases**:
   - Phase 7: Web UI with Streamlit
   - Phase 8: Additional features (containerization, repo mapping, telemetry)

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
