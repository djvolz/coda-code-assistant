# Contributing to Coda

Thank you for your interest in contributing to Coda! This guide will help you get started.

## Development Setup

1. Fork and clone the repository
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `uv sync --all-extras`
4. Run tests: `make test`

## Commit Guidelines

We use [Conventional Commits](https://www.conventionalcommits.org/) for clear and automated release management.

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature (triggers release)
- `fix`: Bug fix (triggers release)
- `perf`: Performance improvement (triggers release)
- `refactor`: Code refactoring (triggers release)
- `docs`: Documentation changes
- `style`: Code style changes
- `test`: Test changes
- `chore`: Build/tooling changes

### Examples
```bash
feat(cli): add interactive mode for model selection
fix(oci): handle authentication timeout gracefully
docs: update installation instructions
```

### Git Commit Template
Set up the commit template locally:
```bash
git config --local commit.template .gitmessage
```

## Pull Request Process

1. Create a feature branch from `main`
2. Make your changes following the coding standards
3. Add tests for new functionality
4. Ensure all tests pass: `make test`
5. Update documentation as needed
6. Submit a pull request with a clear description

## Coding Standards

- Follow PEP 8 style guide
- Use type hints for all functions
- Write docstrings for public APIs
- Keep functions focused and small
- Add unit tests for new code

## Testing

Run tests locally before submitting:
```bash
# Run all tests
make test

# Run specific test file
uv run python -m pytest tests/test_specific.py -v

# Run with coverage
make test-cov
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions/classes
- Update AGENTS.md for AI-related guidelines
- Document breaking changes clearly

## Release Process

Releases are automated based on conventional commits:
- `feat:`, `fix:`, `perf:`, and `refactor:` commits trigger releases
- Each release gets a new timestamp-based version (year.month.day.HHMM)
- No semantic versioning - versions are date-based

See [Release Documentation](docs/RELEASE.md) for details.

## Questions?

- Open an issue for bugs or feature requests
- Start a discussion for questions or ideas
- Check existing issues before creating new ones

Thank you for contributing!