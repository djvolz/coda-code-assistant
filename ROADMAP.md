# Coda Roadmap

## Project Vision

Build a multi-provider, CLI-focused code assistant that provides a unified interface for AI-powered development across Oracle OCI GenAI, Ollama, and other LiteLLM-supported providers.

## Current State & Priorities

✅ **Completed Phases**:

- **Phase 1**: Native OCI GenAI Integration (30+ models, streaming, dynamic discovery)
- **Phase 2**: Core Provider Architecture (LiteLLM, Ollama, provider registry)
- **Phase 3**: Enhanced CLI Experience (interactive shell, slash commands, developer modes)

✅ **Phase 4**: Session Management - COMPLETED (July 5, 2025) | 🚧 Enhancements 4.5 & 4.6 Pending

- SQLite persistence layer (stored in ~/.cache/coda/sessions.db)
- Session commands (/session save/load/list/branch/delete/info/search)
- Export commands (/export json/markdown/txt/html)
- Full-text search across sessions
- Context optimization for token limits
- MockProvider for deterministic testing

🚧 **Current Focus**: Phase 4.6 - Code Quality Refactoring - Before Phase 5

📅 **Next**: Phase 5 - Tool Integration (MCP) - Target: July 12

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

**⚠️ PARALLEL DEVELOPMENT NOTE**: Phase 4 and 5 were developed in parallel. Phase 5 is now complete and merged.
- Phase 4 branch: `feature/session-management` (focuses on persistence layer)
- Phase 5 branch: `feature/mcp-tools` ✅ MERGED
- **Critical Integration**: Phase 4 must implement AI-to-tool integration for Phase 5 tools to work in conversation
- Session schema needs `tool_invocations` table for storing tool execution history

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

### 4.5 Automatic Session Saving (Enhancement) 🚧 DEFERRED

- [x] **Auto-Save by Default** ✅ COMPLETED
  - [x] Automatic session creation on first message
  - [x] Anonymous sessions with timestamp names (e.g., `auto-20250105-143022`)
  - [x] Zero configuration required - just start chatting
  - [🔄] Async saves to avoid blocking chat flow (DEFERRED)
- [🔄] **Rolling Window Management** (DEFERRED)
  - [🔄] Keep last 1000 messages per session
  - [🔄] Archive older messages to linked archive sessions
  - [🔄] Maintain parent-child relationships for full history
  - [🔄] Transparent access to archived content via search
- [x] **User Control Options** ✅ COMPLETED
  - [x] `/session rename` - Rename auto-created sessions
  - [x] `--no-save` CLI flag - Opt out for sensitive conversations
  - [x] Config option: `auto_save_enabled = true/false` (uses existing `autosave`)
  - [x] Bulk delete options for privacy (`/session delete-all [--auto-only]`)
- [x] **Additional Features** ✅ COMPLETED
  - [x] `/session last` - Load most recent session
  - [x] `--resume` CLI flag - Auto-load last session on startup
- [x] **Performance Optimizations** ✅ PARTIALLY COMPLETED
  - [🔄] Batch message inserts for efficiency (DEFERRED)
  - [🔄] Background save queue to prevent UI blocking (DEFERRED)
  - [x] Index on created_at for fast queries
  - [x] Additional indexes for name, accessed_at, parent_id, and tags
  - [🔄] Lazy loading of historical messages (DEFERRED)
- [x] **Privacy & Disclosure** ✅ MOSTLY COMPLETED
  - [x] Clear notification about auto-save on first run
  - [x] Easy bulk delete commands (`/session delete-all`)
  - [🔄] Optional encryption for stored sessions (DEFERRED)
  - [x] Respect XDG data directories (already implemented)

- [x] **Command System Refactoring** ✅ MOSTLY COMPLETED
  - [x] Centralized CommandRegistry for single source of truth
  - [x] Consistent autocomplete from registry definitions
  - [x] Dynamic help text generation from registry
  - [x] Updated help display to show implemented commands
  - [ ] Full command initialization from registry (lower priority)

### 4.6 Code Quality Refactoring (NEW) 🚧 PENDING

**Branch Strategy**: Create `feature/code-quality-refactor` from current feature branch

#### High Priority - Eliminate Hardcoded Values

- [ ] **Create `coda/constants.py` module** for centralized configuration
  - [ ] Path constants (`.coda`, `.config`, `sessions.db`, etc.)
  - [ ] Default query limits (50, 100, 1000)
  - [ ] File extensions and formats (`.toml`, `.txt`, etc.)
  - [ ] Environment variable names
  - [ ] Database table and schema constants
  - [ ] Cache durations (24-hour model cache)
  - [ ] Default temperature and context limits

- [ ] **Create theme/styling configuration**
  - [ ] Extract all hardcoded colors from CLI modules
  - [ ] Create theme configuration system
  - [ ] Support for theme switching via `/theme` command
  - [ ] Consolidate prompt-toolkit styles

#### Medium Priority - Code Structure

- [ ] **Remove duplicate `commands_config.yaml`**
  - [ ] CommandRegistry in Python supersedes YAML
  - [ ] Delete unused YAML file
  - [ ] Update any references

- [ ] **Consolidate interactive CLI modules**
  - [ ] Merge `interactive.py` and `interactive_cli.py`
  - [ ] Remove duplicate command handling logic
  - [ ] Use InteractiveCLI class consistently

- [ ] **Remove unnecessary wrapper methods**
  - [ ] Direct calls to shared functions instead of wrappers
  - [ ] Eliminate `get_system_prompt()` wrappers

#### Configuration Updates

- [ ] **Update configuration module**
  - [ ] Use constants instead of hardcoded values
  - [ ] Make session limits configurable
  - [ ] Add theme configuration support
  - [ ] Document all configuration options

#### Testing

- [ ] Update tests to use constants
- [ ] Ensure no hardcoded values in test files
- [ ] Add tests for theme configuration

**Timeline**: Complete before merging Phase 5

### 4.7 Comparative Analysis of Agent Execution in Code Companions (Research)

**Note**: As we finish up Phase 4, conduct a thorough analysis of how other major open source code companions handle their agent execution:

- [ ] **Aider**
  - [ ] How does aider handle agent-based interactions?
  - [ ] Tool calling mechanisms and protocols
  - [ ] Context management for long conversations
  - [ ] Error handling and recovery strategies

- [ ] **Continue.dev**
  - [ ] Agent architecture and execution model
  - [ ] Integration with various LLM providers
  - [ ] Tool/action system implementation
  - [ ] Session and context persistence

- [ ] **Cursor**
  - [ ] Agent conversation flow (if open source components available)
  - [ ] Multi-turn interaction handling
  - [ ] Code modification strategies

- [ ] **Open Interpreter**
  - [ ] Code execution sandboxing approach
  - [ ] Agent safety mechanisms
  - [ ] Tool integration patterns

- [ ] **GPT Engineer**
  - [ ] Agent planning and execution phases
  - [ ] File system interaction patterns
  - [ ] Project structure understanding

- [ ] **Cody (Sourcegraph)**
  - [ ] Context fetching and management
  - [ ] Agent memory and persistence
  - [ ] Multi-file operation handling

- [ ] **Gemini CLI**
  - [ ] Token usage tracking and reporting
  - [ ] Conversation flow and state management
  - [ ] Multi-modal input handling
  - [ ] Cost tracking mechanisms

- [ ] **Cline**
  - [ ] VSCode extension architecture patterns
  - [ ] Agent-based file editing approach
  - [ ] Task planning and execution flow
  - [ ] User approval workflows

- [ ] **Codex CLI**
  - [ ] Command generation and execution patterns
  - [ ] Shell integration approaches
  - [ ] Safety mechanisms for command execution
  - [ ] Context awareness in terminal environments

**Key Areas to Analyze**:
- Agent conversation state management
- Tool/function calling implementations
- Error recovery and retry mechanisms
- Context window optimization strategies
- Security and sandboxing approaches
- Performance optimization techniques
- User interaction patterns (confirmations, interruptions, etc.)

**Deliverable**: Create a comparison document highlighting best practices and innovative approaches that could enhance our implementation

### 4.8 OpenRouter Integration for Enhanced Model Access

**Note**: While we have LiteLLM support that includes OpenRouter as one of its providers, direct OpenRouter integration offers unique advantages.

- [ ] **Native OpenRouter Provider Implementation**
  - [ ] Direct API integration without LiteLLM intermediary
  - [ ] Support for OpenRouter-specific features (model routing, fallbacks)
  - [ ] Cost tracking and budget management via OpenRouter API
  - [ ] Model preference and routing configuration
  - [ ] Access to exclusive models not available through standard LiteLLM

- [ ] **Enhanced Features**
  - [ ] Automatic model selection based on task complexity
  - [ ] Cost-optimized routing (balance performance vs price)
  - [ ] Fallback chains for reliability
  - [ ] Usage analytics and reporting
  - [ ] Custom model routing rules

- [ ] **Integration Benefits**
  - [ ] Access to 100+ models through single API key
  - [ ] Unified billing across all providers
  - [ ] Built-in rate limit handling across providers
  - [ ] Model comparison and A/B testing capabilities
  - [ ] Provider-agnostic tool calling support

**Timeline**: After Phase 4.7 comparative analysis completion

### 4.4 AI-to-Tool Integration (Critical for Phase 5 tools)
- [x] Function calling protocol for OCI provider (Cohere models support this) ✅
- [x] Parse AI responses for tool requests ✅
- [x] Execute tools based on AI instructions ✅
- [x] Include tool results in conversation context ✅
- [ ] Store tool invocations in session database
- [x] Handle tool errors gracefully in conversation flow ✅
- [ ] **Extend tool support to additional providers:**
  - [ ] Ollama - implement native tool calling support
  - [ ] xAI (Grok) models - tool calling protocol implementation needed
  - [ ] Meta (Llama) models - tool calling protocol implementation needed
  - [ ] Other OCI GenAI providers beyond Cohere
  - [ ] Ensure LiteLLM properly passes through tool calls to supported providers

## Phase 5: Tool Integration (MCP) ✅ COMPLETED (July 5, 2025)

**⚠️ PARALLEL DEVELOPMENT NOTE**: Developed in parallel with Phase 4 and is now complete.

- Work on branch: `feature/mcp-tools` ✅ MERGED
- Created new files: `tools/`, `mcp/` directories
- Full integration with AI conversation pending Phase 4 completion

### 5.1 Core Tools ✅ COMPLETED

- [x] File operations (read, write, edit, list directory)
- [x] Shell command execution with safety controls
- [x] Web search and fetch capabilities
- [x] Git operations (status, log, diff, branch)
- [x] **Tool Result Storage**: Designed format for session integration

### 5.2 Tool Commands ✅ COMPLETED

- [x] `/tools` (`/t`) - Manage MCP tools
  - [x] `list` - List all available tools
  - [x] `info` - Show detailed tool information
  - [x] `categories` - Show all tool categories
  - [x] `stats` - Show tool statistics
  - [x] `help` - Show detailed tools help

### 5.3 MCP Protocol 🚧 PARTIALLY COMPLETED

- [x] Base tool architecture with MCP compatibility
- [x] Tool discovery and registration
- [x] Permission management for dangerous tools
- [x] Parameter validation and error handling
- [ ] External MCP server implementation (deferred)
- [ ] Custom tool development SDK (deferred)

## Phase 6: Advanced Features 📅 CURRENT PHASE

**Status**: Ready to begin - Phase 5 is being handled by another developer.

**Priority Organization for Phase 6**:

1. **Immediate Priority**: Add Rich Panel around input prompt (simple visual improvement)
2. **High Priority**: Enhanced Response Rendering (immediate user experience improvement)
3. **Medium Priority**: Multi-Modal Support (image understanding, document support)
4. **Lower Priority**: Project Intelligence (longer-term features)

### 6.0 Input Prompt Panel Enhancement ✅ COMPLETED (July 7, 2025)

- [x] **Add mode title display** - Clean mode title without separator lines
- [x] **Keep existing prompt-toolkit functionality** - Preserved all current features (multiline, history, autocomplete, shortcuts)
- [x] **Mode-specific styling integration** - Mode titles with colors and emojis matching theme system
- [x] **Clean visual hierarchy** - Minimal 30-char separator after input for subtle visual break
- [x] **Maintain performance** - No impact on input responsiveness or async behavior

**Implementation Details**:

- Removed decorative separator lines for cleaner interface
- Mode title displays with mode-specific colors and emojis
- Left-aligned minimal separator after user input
- Maximum width of 60 chars to prevent stretching
- Professional, uncluttered appearance that focuses on content

### 6.1 Enhanced Response Rendering (🔥 HIGH PRIORITY)

- [ ] **Live markdown rendering during streaming** - Real-time formatting as AI responds
- [ ] **Syntax highlighting for code blocks** - Better code readability in terminal
- [ ] **Proper handling of tables and lists** - Structured data display
- [ ] **Toggle between raw and formatted view** - User preference for output style
- [ ] **Preserve terminal scrollback while rendering** - Maintain terminal history

### 6.2 Multi-Modal Support

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

- [x] `/theme` - Change UI theme ✅ COMPLETED in Phase 4.6
  - [x] `default` - Default color scheme
  - [x] `dark` - Dark mode optimized
  - [x] `light` - Light terminal theme
  - [x] `minimal` - Minimal colors
  - [x] `vibrant` - High contrast colors
  - [x] Additional themes: `monokai_dark/light`, `dracula_dark/light`, `gruvbox_dark/light`

### 6.4 Collaboration Features (DEFERRED)

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

## Phase 8: Vector Embedding & Semantic Search

### 8.1 Embedding Providers

- [ ] **OCI Embedding Service Integration**
  - [ ] OCI GenAI embedding models (multilingual-e5, cohere-embed-multilingual-v3.0)
  - [ ] Batch embedding support for large datasets
  - [ ] Authentication and configuration management
  - [ ] Cost optimization and caching strategies

- [ ] **Open Source Embedding Services**
  - [ ] Local sentence-transformers integration
  - [ ] Ollama embedding models support
  - [ ] HuggingFace embedding models
  - [ ] Custom embedding model support

### 8.2 Vector Storage Backends

- [ ] **Oracle Vector Database**
  - [ ] Oracle Database 23ai vector support
  - [ ] Vector similarity search queries
  - [ ] Hybrid search (vector + traditional SQL)
  - [ ] Connection pooling and optimization

- [ ] **In-Memory FAISS**
  - [ ] Local FAISS index management
  - [ ] Persistent index storage
  - [ ] Multiple index types (flat, IVF, HNSW)
  - [ ] Memory usage optimization

- [ ] **Additional Vector Stores**
  - [ ] ChromaDB integration
  - [ ] Pinecone support (optional)
  - [ ] Local SQLite vector extension

### 8.3 Semantic Search Features

- [ ] **Content Indexing**
  - [ ] Code file embedding and indexing
  - [ ] Documentation and comment extraction
  - [ ] Session history semantic search
  - [ ] Multi-modal content support (code + docs)
  - [ ] **Intelligent Chunking Strategies**
    - [ ] Hybrid chunking approach with configurable size/overlap
    - [ ] Tree-sitter integration for code-aware chunking
    - [ ] Semantic boundary detection (functions, classes, blocks)
    - [ ] Sub-function chunking for large methods
    - [ ] Configurable chunk size (300-400 tokens) with overlap (50-100 tokens)
    - [ ] Support for different chunking strategies per file type
    - [ ] Preserve context across chunk boundaries

- [ ] **Search Interface**
  - [ ] `/search semantic <query>` - Semantic similarity search
  - [ ] `/search code <query>` - Code-specific semantic search
  - [ ] `/search similar` - Find similar code patterns
  - [ ] Hybrid search combining keyword and semantic

- [ ] **Integration with Existing Features**
  - [ ] Enhance session search with semantic capabilities
  - [ ] Context-aware code suggestions
  - [ ] Related code discovery
  - [ ] Intelligent context selection for AI prompts

## Phase 9: Codebase Intelligence

### 9.1 Repository Analysis 🚧 IN PROGRESS (July 7, 2025)

- [x] **Repo Mapping** ✅ COMPLETED
  - [x] Repo mapping like [aider](https://aider.chat/docs/repomap.html)
    - see local checkout: /Users/danny/Developer/forks/aider-fork/aider-using-claude
  - [x] Tree-sitter integration using [aider ts implementation](https://github.com/Aider-AI/aider/tree/main/aider/queries)
    - Implemented using tree-sitter query language (.scm files)
    - Copied 30 query files from aider for multiple languages
    - Using grep-ast and tree-sitter-language-pack
  - [x] Support for documentation, function, class, struct, etc (beyond aider's ref/def approach)
  - [x] Multi-language code structure analysis (30+ languages)
  - [x] Dependency graph generation with circular dependency detection

**Implementation Details**:
- Created `/intel` CLI command with 7 subcommands (analyze, map, scan, stats, find, deps, graph)
- Tree-sitter query-based extraction using .scm files
- Support for Python, JavaScript, TypeScript, Rust, Go, Java, C/C++, Ruby, and 20+ more languages
- Comprehensive test suite with 138 tests (including integration tests)
- Progress indicators for long-running operations
- MockProvider integration for AI-enhanced development

**Enhancements TODO**:
- [ ] **Intelligence as Tools** - Make intel commands available as AI tools
  - [ ] Register intel commands with MCP tool system
  - [ ] Enable AI to analyze code structure during conversations
  - [ ] Allow AI to find definitions and dependencies automatically
  - [ ] Provide semantic code search capabilities to AI

- [ ] **Self-Contained API Module** - Make intelligence module fully independent
  - [ ] Extract intelligence module as standalone Python package
  - [ ] Create public API interface for external usage
  - [ ] Document API methods and usage examples
  - [ ] Support both CLI and programmatic access
  - [ ] Ensure zero dependencies on Coda-specific code
  - [ ] Publish as separate package (coda-intelligence)

### 9.2 Context Management

- [ ] **Intelligent Context Handling**
  - [ ] Automatic conversation compacting for long sessions
  - [ ] Smart context window management based on codebase structure
  - [ ] Context relevance scoring for code snippets (enhanced by semantic search)
  - [ ] Token usage optimization with semantic understanding

### 9.3 Code Understanding

- [ ] **Semantic Analysis**
  - [ ] Function and class relationship mapping
  - [ ] Call graph generation
  - [ ] Import/dependency tracking
  - [ ] Code pattern recognition (enhanced by embeddings)
  - [ ] Documentation extraction and indexing

- [ ] **Review & Analysis Tools**
  - [ ] AI-powered code review helper
  - [ ] Security vulnerability detection
  - [ ] Code quality assessment
  - [ ] Performance bottleneck identification

## Phase 10: Help Mode Integration

### 10.1 Wiki-Based Help System

- [ ] **Wiki Integration**
  - [ ] GitHub wiki API client for fetching content from https://github.com/djvolz/coda-code-assistant/wiki/
  - [ ] Local caching of wiki pages for offline access
  - [ ] Automatic wiki content updates and sync
  - [ ] Search functionality across wiki content (enhanced by semantic search)
- [ ] **Help Commands**
  - [ ] `/help wiki` - Interactive wiki search and navigation
  - [ ] `/help search <query>` - Search wiki for specific topics
  - [ ] `/help topics` - List available help topics from wiki
  - [ ] `/help refresh` - Force refresh of cached wiki content
- [ ] **Context-Aware Help**
  - [ ] Analyze user questions to suggest relevant wiki pages
  - [ ] Auto-suggest help topics based on current conversation context
  - [ ] Integration with existing `/help` command to include wiki results
  - [ ] Smart routing: CLI help vs wiki help based on query type

- [ ] **Enhanced Help Experience**
  - [ ] Formatted display of wiki content in terminal
  - [ ] Markdown rendering for wiki pages
  - [ ] Link resolution between wiki pages
  - [ ] Breadcrumb navigation for wiki sections

### 10.2 Implementation Details

- [ ] **Wiki Content Processing**
  - [ ] Parse GitHub wiki markdown format
  - [ ] Extract and index searchable content
  - [ ] Handle wiki page relationships and cross-references
  - [ ] Support for code examples and syntax highlighting in help

- [ ] **Caching Strategy**
  - [ ] Store wiki content in `~/.cache/coda/wiki/`
  - [ ] Implement cache expiration and refresh logic
  - [ ] Offline mode fallback to cached content
  - [ ] Delta updates for modified wiki pages

## Phase 11: Observability & Performance

### 11.1 Real OpenTelemetry Integration 🚧 PENDING

**Current State**: OpenTelemetry dependencies are included but not used. The current implementation uses a custom file-based solution.

#### 11.1.1 OpenTelemetry SDK Integration

- [ ] **Replace Custom Tracing with OpenTelemetry**
  - [ ] Replace custom `Span` class with `opentelemetry.trace.Span`
  - [ ] Replace `TracingManager` with `opentelemetry.trace.Tracer`
  - [ ] Use OpenTelemetry context propagation
  - [ ] Implement proper span attributes following semantic conventions
  - [ ] Add span events and links support
  - [ ] Implement baggage for cross-cutting concerns

- [ ] **Replace Custom Metrics with OpenTelemetry**
  - [ ] Replace `MetricsCollector` with OpenTelemetry metrics API
  - [ ] Use proper metric instruments (Counter, Histogram, Gauge)
  - [ ] Follow OpenTelemetry semantic conventions for metric names
  - [ ] Implement metric views and aggregations
  - [ ] Add exemplar support for metrics-to-traces correlation

- [ ] **Implement OpenTelemetry Logging**
  - [ ] Integrate Python logging with OpenTelemetry
  - [ ] Add trace context to log records
  - [ ] Implement log correlation with traces
  - [ ] Support structured logging with attributes

#### 11.1.2 OTLP Exporter Configuration

- [ ] **OTLP Export Support**
  - [ ] Configure OTLP/gRPC exporter for traces
  - [ ] Configure OTLP/HTTP exporter option
  - [ ] Add authentication support (headers, certificates)
  - [ ] Implement retry and backoff policies
  - [ ] Add batch processing configuration
  - [ ] Support multiple export endpoints

- [ ] **Configuration Management**
  - [ ] Add OTLP endpoint configuration to settings
  - [ ] Environment variable support (OTEL_EXPORTER_OTLP_ENDPOINT, etc.)
  - [ ] Service name and resource attributes configuration
  - [ ] Sampling configuration (TraceIdRatioBased, ParentBased)
  - [ ] Export timeout and batch size settings

#### 11.1.3 Backend Integrations

- [ ] **Popular Observability Platforms**
  - [ ] Jaeger integration guide and testing
  - [ ] Zipkin compatibility testing
  - [ ] Grafana Tempo configuration
  - [ ] Datadog APM integration
  - [ ] New Relic integration
  - [ ] AWS X-Ray support via ADOT
  - [ ] Google Cloud Trace integration
  - [ ] Azure Monitor integration

- [ ] **Local Development Support**
  - [ ] Docker Compose setup with Jaeger
  - [ ] Local Grafana stack (Tempo + Prometheus + Loki)
  - [ ] OpenTelemetry Collector configuration
  - [ ] Development environment documentation

- [ ] **Grafana Docker Container Setup**
  - [ ] Deploy Grafana with OpenTelemetry data source
  - [ ] Pre-configured dashboards for Coda metrics
  - [ ] Integration with Coda's OTLP exporter
  - [ ] Docker Compose configuration for observability stack
  - [ ] Prometheus backend for metrics storage
  - [ ] Jaeger/Tempo integration for distributed tracing
  - [ ] Custom Coda performance dashboards

#### 11.1.4 Instrumentation Libraries

- [ ] **Auto-Instrumentation**
  - [ ] SQLAlchemy instrumentation for database queries
  - [ ] HTTPX instrumentation for API calls
  - [ ] aiohttp instrumentation for async HTTP
  - [ ] Rich console instrumentation for CLI operations
  - [ ] Custom instrumentation for AI provider calls

- [ ] **Manual Instrumentation**
  - [ ] Instrument all provider methods with proper spans
  - [ ] Add metrics for token usage and costs
  - [ ] Trace tool execution with detailed attributes
  - [ ] Session operations tracing
  - [ ] Add custom business metrics

#### 11.1.5 Observability Standards

- [ ] **Semantic Conventions**
  - [ ] Follow OpenTelemetry semantic conventions for:
    - [ ] HTTP requests (http.method, http.status_code, etc.)
    - [ ] Database operations (db.system, db.operation, etc.)
    - [ ] AI/ML operations (create custom conventions)
    - [ ] Tool executions (custom conventions)
  - [ ] Document custom attributes and conventions

- [ ] **Resource Detection**
  - [ ] Automatic service name detection
  - [ ] Version information in resource attributes
  - [ ] Deployment environment detection
  - [ ] Container/K8s resource attributes
  - [ ] Cloud provider resource detection

#### 11.1.6 Migration Strategy

- [ ] **Backward Compatibility**
  - [ ] Keep file-based export as fallback option
  - [ ] Configuration flag to switch between implementations
  - [ ] Gradual migration path for existing users
  - [ ] Data migration tools for historical data

- [ ] **Feature Parity**
  - [ ] Ensure all current observability features work with OpenTelemetry
  - [ ] Maintain CLI commands functionality
  - [ ] Update tests for OpenTelemetry implementation
  - [ ] Performance comparison and optimization

### 11.2 Enhanced Observability Features

- [ ] **Distributed Tracing**
  - [ ] Trace context propagation between services
  - [ ] Parent-child span relationships
  - [ ] Cross-service dependency mapping
  - [ ] Trace sampling strategies
  - [ ] Long-running operation tracking

- [ ] **Advanced Metrics**
  - [ ] Percentile calculations (p50, p95, p99)
  - [ ] Rate and throughput calculations
  - [ ] Custom metric aggregations
  - [ ] Service Level Indicators (SLIs)
  - [ ] Cost tracking metrics

- [ ] **Debugging & Profiling**
  - [ ] Continuous profiling integration
  - [ ] Memory profiling with traces
  - [ ] CPU profiling correlation
  - [ ] Goroutine/thread analysis
  - [ ] Heap dump integration
  - [ ] Pyroscope integration for performance profiling
  - [ ] Debug mode enhancements
  - [ ] Memory usage tracking
  - [ ] Bottleneck identification
  - [ ] Performance analysis tools integration

### 11.3 Observability Testing ✅ COMPLETED (July 8, 2025)

- [x] **Comprehensive Integration Testing**
  - [x] Test every observability command option with mock provider
  - [x] Test every observability command option with ollama provider
  - [x] Test all components with observability.enabled=true
  - [x] Test all components with observability.enabled=false
  - [x] Test individual component enable/disable configurations
  - [x] Verify no performance impact when observability is disabled
  - [x] Test data export formats (JSON, CSV, HTML)
  - [x] Test retention policies and data cleanup
  - [x] Test memory limits and eviction policies
  - [x] Test error scenarios and recovery
  - [x] Load testing with high-volume metrics
  - [x] Concurrent access testing for thread safety

**Test Suite Created**:
- 10 comprehensive test files covering all aspects
- 200+ individual test cases
- Mock provider and Ollama provider integration tests
- Configuration state tests (enabled/disabled/partial)
- Export format tests (JSON, CSV, HTML)
- Error handling and recovery tests
- Retention policy and cleanup tests
- Memory management and eviction tests
- Load testing with throughput benchmarks
- Thread safety and concurrent access tests

## Phase 12: DevOps & Automation

### 12.1 Deployment & Distribution

- [ ] **Containerization**
  - [ ] Containerize coda with ollama bundled by default
  - [ ] Docker compose setup for development
  - [ ] Multi-architecture container builds
  - [ ] Container optimization for size and performance
  - [ ] **Observability Stack Integration**
    - [ ] Docker Compose profile for full observability stack
    - [ ] Grafana + Prometheus + Jaeger containers
    - [ ] Pre-configured data sources and dashboards
    - [ ] Integration with Phase 11 OpenTelemetry features
    - [ ] Development and production configurations
    - [ ] Pre-configured Grafana instance for monitoring
    - [ ] Dashboards for metrics, traces, errors, and health
    - [ ] Prometheus or OpenTelemetry collector integration
    - [ ] Automated datasource configuration
    - [ ] Sample alerts and monitoring rules
    - [ ] **Pyroscope Profiling Container**
      - [ ] Deploy Pyroscope for continuous performance profiling
      - [ ] Integration with Coda application for flame graphs
      - [ ] Memory and CPU profiling dashboards
      - [ ] Automatic profiling data retention policies
      - [ ] Docker Compose profile for profiling stack

### 12.2 Development Workflow

- [ ] **Version Control Integration**
  - [ ] Wiki update checker and notification system
  - [ ] Changelog generator (VCS-agnostic, hash-to-hash)
  - [ ] Automated changelog detection from commits
  - [ ] Git workflow optimization tools

## Phase 13: Plugin System Architecture

### 13.1 Core Plugin Infrastructure

**Inspiration**: Implement a plugin system similar to [simonw/llm](https://github.com/simonw/llm) for maximum extensibility.

- [ ] **Plugin Discovery & Loading**
  - [ ] Entry point-based plugin discovery (using Python entry points)
  - [ ] Dynamic plugin loading at runtime
  - [ ] Plugin dependency resolution
  - [ ] Version compatibility checking
  - [ ] Hot-reload support for development

- [ ] **Plugin Types**
  - [ ] **Provider Plugins**: Add new LLM providers
  - [ ] **Tool Plugins**: Add new MCP tools and capabilities
  - [ ] **Mode Plugins**: Add custom developer modes
  - [ ] **Export Plugins**: Add new export formats
  - [ ] **Storage Plugins**: Alternative session storage backends
  - [ ] **Theme Plugins**: Custom UI themes and styles

### 13.2 Plugin Development Kit

- [ ] **Plugin Template & Scaffolding**
  - [ ] Cookiecutter template for new plugins
  - [ ] Example plugins for each type
  - [ ] Plugin development guide
  - [ ] Testing utilities for plugin developers

- [ ] **Plugin API**
  - [ ] Well-defined plugin interfaces (ABCs)
  - [ ] Hook system for extending core functionality
  - [ ] Event system for plugin communication
  - [ ] Configuration management for plugins
  - [ ] Resource access controls

### 13.3 Plugin Management

- [ ] **CLI Commands**
  - [ ] `coda plugins list` - List installed plugins
  - [ ] `coda plugins install <name>` - Install from PyPI
  - [ ] `coda plugins uninstall <name>` - Remove plugin
  - [ ] `coda plugins enable/disable <name>` - Toggle plugins
  - [ ] `coda plugins info <name>` - Show plugin details
  - [ ] `coda plugins search <query>` - Search available plugins

- [ ] **Plugin Registry**
  - [ ] Central plugin registry (similar to npm/pypi)
  - [ ] Plugin metadata and descriptions
  - [ ] Compatibility matrix with coda versions
  - [ ] Download statistics and ratings
  - [ ] Security scanning for plugins

### 13.4 Plugin Examples

- [ ] **Example Provider Plugin**: Anthropic Claude direct integration
- [ ] **Example Tool Plugin**: Database query tool
- [ ] **Example Mode Plugin**: SQL-specific assistant mode
- [ ] **Example Export Plugin**: Jupyter notebook export
- [ ] **Example Storage Plugin**: PostgreSQL session backend
- [ ] **Example Theme Plugin**: High contrast accessibility theme

### 13.5 Security & Isolation

- [ ] **Plugin Sandboxing**
  - [ ] Resource usage limits
  - [ ] File system access controls
  - [ ] Network request filtering
  - [ ] API rate limiting per plugin

- [ ] **Plugin Verification**
  - [ ] Code signing for official plugins
  - [ ] Security audit requirements
  - [ ] Automated vulnerability scanning
  - [ ] User permission system for plugin capabilities

**Benefits**:
- Community can extend Coda without modifying core
- Easy distribution of custom functionality
- Maintains clean separation of concerns
- Enables domain-specific extensions
- Facilitates experimentation with new features

**Timeline**: After Phase 12, as this provides the foundation for future extensibility

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

### 2025.7.12 - Tool Integration / MCP ✅ COMPLETED (July 5, 2025)

- ✅ Core tools implemented (12 tools across 4 categories)
  - ✅ File operations (read, write, edit, list directory)
  - ✅ Shell command execution with safety controls
  - ✅ Web search and fetch capabilities
  - ✅ Git operations (status, log, diff, branch)
- ✅ Tool commands (/tools list/info/categories/stats/help)
- ✅ Base tool architecture with MCP compatibility
- ✅ Parameter validation and error handling
- ✅ Permission management for dangerous tools
- ✅ Comprehensive test suite (30+ tests)
- ✅ CLI integration (both interactive and basic modes)
- ⏸️ External MCP server implementation (deferred)
- ⏸️ Advanced permission system (deferred)

**Phase 4.6 Achievements**:

- ✅ Centralized constants system (`coda/constants.py`)
- ✅ Comprehensive theme system with 11 pre-defined themes
- ✅ Complete `/theme` command implementation
- ✅ Code quality refactoring across 57 files
- ✅ Enhanced test coverage (25 new theme-related tests)
- ✅ Backward compatibility maintained

**Agent Integration ✅ COMPLETED (July 7, 2025)**:
- ✅ Full AI-to-tool integration via Agent system
- ✅ Agent-based chat with streaming support (`run_async_streaming`)
- ✅ Intelligent tool usage - agents only use tools when necessary
- ✅ Enhanced agent instructions for balanced tool usage
- ✅ Real-time streaming responses while maintaining tool functionality
- ✅ Cohere models now fully support streaming with tool capabilities
- ✅ Agent can handle both tool-based and non-tool requests appropriately

**Tools Support for Additional Providers 🚧 PENDING**:
- [ ] **Ollama Provider** - Add native tool calling support (currently not supported)
- [ ] **OCI GenAI Provider**:
  - [ ] Add tools support for Meta (Llama) models
  - [ ] Add tools support for xAI (Grok) models
  - [ ] Add tools support for any other non-Cohere models
- [ ] **LiteLLM Provider** - Ensure tool calling works for all supported underlying providers:
  - [x] OpenAI models ✅ (already supported)
  - [x] Google Gemini models ✅ (already supported)
  - [x] Cohere models ✅ (already supported)
  - [x] Mistral models ✅ (already supported)
  - [ ] Anthropic Claude models (currently not supported by LiteLLM)
- [ ] **MockProvider** - Already supports tools ✅ (for testing)
- [ ] Implement provider-specific tool calling formats and protocols
- [ ] Add comprehensive tests for tool functionality across all providers
- [ ] Update documentation to clearly indicate which providers/models support tools

**MCP Configuration Support 🚧 PENDING**:
- [ ] Support for `mcp.json` configuration files
- [ ] Global MCP config in `~/.config/coda/mcp.json`
- [ ] Local project MCP config in `.coda/mcp.json` or `mcp.json`
- [ ] MCP server discovery and registration from config files
- [ ] Tool loading from external MCP servers specified in config
- [ ] Priority: local project config > global config > built-in tools

**Phase 6.0 Achievement**:

- ✅ Clean mode title display without decorative lines
- ✅ Minimal separator after input (30 chars, left-aligned)
- ✅ Mode-specific colors and emojis
- ✅ Preserved all prompt-toolkit functionality
- ✅ Professional, uncluttered interface

### 2025.7.15 - Advanced Features (Target: July 15)

- Multi-modal support (image understanding)
- Document support (PDF, Word, PowerPoint, Excel)
- Enhanced response rendering (live markdown)
- Project intelligence (VCS support, language optimizations)
- UI customization (/theme command)

## Next Steps

**Current Status**: Phases 1, 2, 3, 4, 5, and Agent Integration are complete. Phase 4.6 (Code Quality Refactoring) pending.

1. **Pending - Phase 4.6**: Code Quality Refactoring
   - Create `coda/constants.py` for centralized configuration
   - Create theme/styling configuration system
   - Remove duplicate code and unnecessary wrappers
   - Consolidate interactive CLI modules
   
2. **Next - Phase 6**: Advanced Features (Target: July 15)
   - Multi-modal support (image understanding)
   - Code screenshot analysis
   - Document support (PDF, Word, PowerPoint, Excel)
   - Enhanced response rendering with live markdown
   
3. **Future Phases**:
   - Phase 7: Web UI with Streamlit
   - Phase 8: Vector Embedding & Semantic Search
   - Phase 9: Codebase Intelligence
   - Phase 10: Help Mode Integration
   - Phase 11: Observability & Performance
   - Phase 12: DevOps & Automation

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
