.PHONY: help test test-unit test-integration test-all test-cov test-fast lint format clean install-dev pre-commit version

# Default target
help:
	@echo "Coda Development Commands"
	@echo "========================"
	@echo "make test          - Run unit tests only (fast)"
	@echo "make test-all      - Run all tests including integration"
	@echo "make test-unit     - Run only unit tests"
	@echo "make test-integration - Run integration tests (needs credentials)"
	@echo "make test-cov      - Run tests with coverage report"
	@echo "make test-fast     - Run fast smoke tests"
	@echo "make lint          - Run linters (ruff, mypy)"
	@echo "make format        - Auto-format code"
	@echo "make clean         - Clean generated files"
	@echo "make install-dev   - Install development dependencies"
	@echo "make pre-commit    - Run checks before committing"
	@echo "make version       - Update version to current timestamp"

# Run unit tests only (default for CI)
test:
	uv run pytest tests/ -v -m "unit or not integration"

# Run all tests including integration
test-all:
	uv run pytest tests/ -v

# Run only unit tests
test-unit:
	uv run pytest tests/ -v -m unit

# Run only integration tests (requires credentials)
test-integration:
	RUN_INTEGRATION_TESTS=1 uv run pytest tests/ -v -m integration

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v -m "unit or not integration" \
		--cov=coda --cov-report=html --cov-report=term-missing

# Run fast smoke tests
test-fast:
	uv run pytest tests/test_smoke.py -v

# Lint code
lint:
	uv run ruff check .
	@echo "Ruff check passed ✓"

# Format code
format:
	uv run black .
	uv run ruff check --fix .
	@echo "Code formatted ✓"

# Type check (optional, may need configuration)
typecheck:
	uv run mypy coda/ || echo "Type checking needs configuration"

# Clean up
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf .mypy_cache/
	rm -rf .ruff_cache/
	@echo "Cleaned up generated files ✓"

# Install dev dependencies
install-dev:
	uv sync --all-extras
	@echo "Development dependencies installed ✓"

# Run quick checks before commit
pre-commit: format lint test-fast
	@echo "Pre-commit checks passed ✓"

# Update version to current timestamp
version:
	uv run python scripts/update_version.py