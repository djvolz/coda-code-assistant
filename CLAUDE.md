# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Coda is a multi-provider AI code assistant for terminal-based development workflows. It features a modular 3-layer architecture (Apps → Services → Base) with support for multiple AI providers including OCI GenAI, OpenAI, Anthropic, Ollama, and 100+ providers via LiteLLM.

## Essential Commands

### Development Setup
```bash
# Install dependencies (requires uv package manager)
make install

# Activate virtual environment
source .venv/bin/activate
```

### Running Tests
```bash
# Run all tests
make test

# Run specific test levels
make test-unit          # Unit tests only
make test-integration   # Integration tests only
make test-functional    # Functional tests only

# Run a single test
pytest tests/path/to/test_file.py::test_function_name -xvs

# Run tests with coverage
make test-coverage
```

### Code Quality
```bash
# Format code
make format

# Run linter
make lint

# Type checking (optional)
make typecheck

# Run all quality checks (format + lint + typecheck)
make quality
```

### Building and Running
```bash
# Run CLI
coda --help

# Build Docker image
make docker-build

# Run with Docker
make docker-run
```

## Architecture

### Layer Structure
1. **Apps Layer** (`coda/apps/`): User-facing applications
   - `cli/`: Command-line interface implementation
   - `web/`: Web UI implementation (FastAPI)

2. **Services Layer** (`coda/services/`): Business logic and orchestration
   - `agents/`: AI agent implementations and registry
   - `tools/`: Tool implementations (file operations, web search, etc.)
   - `integration/`: External service integrations

3. **Base Layer** (`coda/base/`): Core functionality
   - `config/`: Configuration management with schema validation
   - `providers/`: AI provider implementations
   - `session/`: Conversation persistence
   - `search/`: Tree-sitter based semantic code search
   - `observability/`: Logging, metrics, and tracing
   - `theme/`: Theme management for terminal colors and styles

### Key Design Patterns
- **Registry Pattern**: Used for providers, agents, and tools
- **Provider Interface**: All AI providers implement a common interface
- **Mock Provider**: Special provider for testing with predictable responses
- **Session Management**: Conversations are persisted in XDG-compliant directories

## Version Management

The project uses date-based versioning: `year.month.day.HHMM`

```bash
# Bump version (updates pyproject.toml)
./scripts/bump_version.sh

# Version is also available via CLI
coda --version
```

## Testing Guidelines

- Tests are organized by level: unit, integration, functional
- Use appropriate pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.functional`
- Mock external services in unit tests
- Integration tests may use the mock provider for predictable AI responses
- Functional tests verify end-to-end workflows

## Configuration

- User config: `~/.config/coda/config.yaml`
- Sessions stored in: `~/.local/share/coda/sessions/`
- Logs in: `~/.local/share/coda/logs/`
- All paths follow XDG Base Directory specification

## MCP Server Configuration

Coda supports Model Context Protocol (MCP) servers for extending functionality with external tools. 

### Configuration Files
MCP servers are configured via `mcp.json` files. Coda searches for configuration in this order:
1. Current working directory (`./mcp.json`)
2. Project directory (if specified)  
3. User config directory (`~/.config/coda/mcp.json`)

### Example Configuration
```json
{
  "mcpServers": {
    "serena": {
      "command": "uvx",
      "args": ["--from", "mcp-serena", "mcp-serena"],
      "env": {},
      "enabled": true
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/allowed/files"],
      "enabled": true
    },
    "remote-server": {
      "url": "http://localhost:8080/mcp",
      "auth_token": "your-token-here",
      "enabled": true
    }
  }
}
```

### Server Types
- **Subprocess servers**: Use `command` and `args` to launch local MCP servers
- **Remote servers**: Use `url` to connect to HTTP/WebSocket MCP servers  
- **Authentication**: Optional `auth_token` for remote servers
- **Environment**: Custom environment variables via `env` object


## Important Notes

- Always use the `uv` package manager (not pip directly)
- Follow the project's modular architecture when adding features
- Respect the layer boundaries (Apps → Services → Base)
- Use conventional commits for version management
- The mock provider is essential for testing - use it for predictable test scenarios
- Tree-sitter grammars are automatically downloaded as needed for code search
- When adding new features or documentation, also create corresponding wiki-style documentation in `docs/wiki-staging/`

## Change Verification

**CRITICAL**: All code changes must be verified before considering the work complete.

### Minimum Verification
```bash
# Always verify changes work by running the CLI help
uv run coda --help
```

### Recommended Verification
```bash
# Test full functionality with mock provider (best approach)
echo "hi" | uv run coda chat --provider mock --model mock-model

# Verify CLI starts properly (will show welcome screen)
uv run coda
# Press Ctrl+C to exit after seeing the welcome screen

# Test help functionality
uv run coda --help
```

### Additional Verification Steps
- Run relevant tests: `make test` or specific test suites
- Check code quality: `make quality` (format + lint + typecheck)
- For new features, test the specific functionality implemented
- For bug fixes, verify the issue is resolved

**Never mark work as complete without running at least `uv run coda` to ensure the application starts correctly.**

## Theme Usage Guidelines

- **NEVER use colors directly**: All colors must go through the theme module
- **Import theme components**: Use `from coda.base.theme import ThemeManager, ConsoleTheme`
- **Get colors from theme**: Access colors via theme objects, not hardcoded hex values
- **Examples of what NOT to do**:
  - ❌ `color="#1f77b4"` 
  - ❌ `style="fg:red bg:white"`
  - ❌ Direct RGB values like `rgb(255, 0, 0)`
- **Examples of correct usage**:
  - ✅ `theme.console.success` for success messages
  - ✅ `theme.console.error` for error messages
  - ✅ `theme.prompt.completion` for completion styling
- **Custom themes**: Use `ThemeManager.create_custom_theme()` for brand-specific colors
- **Theme persistence**: Themes are automatically loaded from user config

## Release Process

The project uses automated releases triggered by conventional commits on the main branch.

### Automatic Release Triggers
- `feat:` or `feature:` commits trigger a release with version bump
- `fix:` or `bugfix:` commits trigger a release 
- `perf:` or `refactor:` commits trigger a release
- Other commit types (docs, style, test, chore) do NOT trigger releases

### Version Format
- Date-based versioning: `year.month.day.HHMM` (e.g., 2025.7.12.0326)
- Version is automatically updated based on UTC timestamp
- No semantic versioning - each release gets a new timestamp

### Release Workflow
1. Push a conventional commit to main branch
2. GitHub Actions checks commit types
3. If release-worthy commits found:
   - Updates version via `scripts/update_version.py`
   - Runs ALL tests with `make test-all`
   - Builds package with `uv build`
   - Commits version bump
   - Creates GitHub release with changelog
   - Optionally uploads to PyPI (if token configured)

### Manual Release
- Use GitHub Actions workflow dispatch with "force_release" option
- Or run locally: `make version` then create release manually

### Skip Release
- Add `[skip ci]` or `[skip release]` to commit message

### Important: Merge Strategy
- **DO NOT SQUASH COMMITS** when merging PRs
- Use "Create a merge commit" to preserve individual commit messages
- The release workflow needs to see conventional commits to trigger releases
- Squashing would lose the commit type information (feat:, fix:, etc.)