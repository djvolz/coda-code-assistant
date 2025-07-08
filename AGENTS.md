# Coda Development Guide

**Coda** is a multi-provider CLI code assistant providing a unified interface for LLMs (OCI GenAI, OpenAI, Anthropic, Ollama). Built for developers who prefer terminal workflows.

**Core Principles**: Simplicity, Flexibility, Performance, Developer Experience, Extensibility

IMPORTANT: Read [ROADMAP.md](ROADMAP.md) first for architecture and planned features.

## Quick Commands

```bash
# Development
uv sync --all-extras          # Install all dependencies
uv run coda                   # Run interactive CLI
uv run coda --one-shot "..."  # One-shot mode
make test                     # Run unit tests
make test-cov                 # Run tests with coverage
make format                   # Format code
make version                  # Update version timestamp

# Git workflow
gh pr create                  # Create PR (use conventional commits)
gh pr checks                  # Check CI status
git commit -m "type(scope): message"  # Conventional commit format
```

## Core Files & Structure

```
coda/
├── __version__.py         # Version management (year.month.day.HHMM)
├── cli/main.py           # CLI entry point and commands
├── providers/
│   ├── base.py          # Abstract provider interface
│   └── oci_genai.py     # OCI GenAI implementation
└── config.py            # Configuration management

tests/                    # Comprehensive test suite
scripts/                  # Utility scripts
examples/                 # Usage examples
```

## Code Style

IMPORTANT: Follow these patterns exactly:
- Use type hints for ALL functions
- Prefer async/await for I/O operations
- Use Pydantic for data validation
- Follow existing import patterns
- Add docstrings to public APIs only
- Keep functions under 50 lines

## Testing Requirements

ALWAYS run tests before committing:
- New features need unit tests
- Use pytest markers: `@pytest.mark.unit`, `@pytest.mark.integration`
- Mock external services (OCI, APIs)
- Aim for >80% coverage on new code

### Mock Provider for Testing

**IMPORTANT**: Use `MockProvider` for all tests requiring AI responses. Never use real providers in tests.

```python
from coda.providers import MockProvider, Message, Role

# Use MockProvider for predictable, offline testing
provider = MockProvider()
response = provider.chat(messages, "mock-echo")
```

**Key Benefits**:
- ✅ No API keys or network required
- ✅ Predictable, deterministic responses
- ✅ Context-aware conversation memory
- ✅ Perfect for session management testing

**Reference**: See [docs/mock_provider_reference.md](docs/mock_provider_reference.md) for complete behavior patterns and testing examples.

## Provider Implementation

When adding new providers:
1. Inherit from `BaseProvider` in `providers/base.py`
2. Implement all abstract methods
3. Add model discovery/caching
4. Handle streaming responses
5. Map provider-specific errors
6. Add comprehensive tests

## Configuration Priority

1. CLI parameters (highest)
2. Environment variables
3. Project config: `.coda/config.toml`
4. User config: `~/.config/coda/config.toml`
5. Defaults (lowest)

XDG directories:
- Config: `~/.config/coda/`
- Sessions: `~/.local/share/coda/sessions/`
- Cache: `~/.cache/coda/`

## Commit Guidelines

IMPORTANT: Use the standardized commit template for all commits:
```bash
git config --local commit.template .gitmessage
```

The template includes:
- Conventional commit format with release triggers
- AI metadata sections (Prompt, Tools, Implementation details)
- PII scrubbing reminders
- Examples and guidelines

See [`.gitmessage`](.gitmessage) for the complete template.

## Pull Request Requirements

IMPORTANT: Use the standardized PR template for all pull requests.

The GitHub PR template automatically includes:
- AI Development Summary section
- Conventional commit type indicators
- Testing and code quality checklists
- PII scrubbing reminders
- Breaking change documentation

See [`.github/pull_request_template.md`](.github/pull_request_template.md) for the complete template.

**Key Requirements:**
- Never squash commits - preserve AI development history
- All CI checks must pass before merge
- Include test results and coverage information

## Current State & Priorities

✅ Completed:
- OCI GenAI provider (30+ models)
- Date-based versioning
- Automated releases
- CLI with streaming

🚧 Next Up (Phase 2 - July 5):
- Abstract provider interface
- LiteLLM integration
- Ollama support

## Gotchas & Warnings

- OCI requires compartment_id configuration
- Version updates only happen during releases
- Tests use `python -m pytest` (not direct pytest)
- Always use absolute paths in file operations
- Provider model names use dot notation: `provider.model-name`

## Preferred Tools

- `rg` instead of grep
- `fd` instead of find
- `uv` instead of pip
- `gh` for GitHub operations
- Use Task tool for complex searches across multiple files
- Batch multiple tool calls for better performance

## General Workflow

1. **Explore** - Read AGENTS.md and understand the codebase structure
2. **Plan** - Use TodoWrite to break down complex tasks
3. **Code** - Implement changes following project conventions
4. **Test** - Run tests and linting as specified above
5. **Commit** - Use conventional commits as documented

## Important Reminders

- Never create documentation files unless explicitly requested
- Always prefer editing existing files over creating new ones
- Never commit changes unless explicitly asked
- Follow security best practices - never expose secrets or credentials

## Release Process

Automatic releases triggered by:
- `feat:` - New features
- `fix:` - Bug fixes
- `perf:` - Performance improvements
- `refactor:` - Code refactoring

Skip release: add `[skip ci]` or `[skip release]` to commit message

## Environment Setup

```bash
# First time setup
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone <repo>
cd coda-code-assistant
uv sync --all-extras
```

## Debugging Tips

- Use `--debug` flag for verbose output
- Check `~/.cache/coda/` for cached models
- OCI errors usually mean config issues
- Streaming issues: check httpx timeout settings