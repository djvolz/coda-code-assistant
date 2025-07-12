.PHONY: help test test-unit test-integration test-all test-cov test-fast lint format clean install-dev pre-commit version
.PHONY: docker-build docker-run docker-dev docker-dev-up docker-dev-down docker-test docker-clean docker-push

# Default target
help:
	@echo "Coda Development Commands"
	@echo "========================"
	@echo "make test          - Run unit tests only (fast)"
	@echo "make test-all      - Run all tests including integration"
	@echo "make test-unit     - Run only unit tests"
	@echo "make test-integration - Run integration tests (needs credentials)"
	@echo "make test-llm      - Run LLM tests with Ollama"
	@echo "make test-cov      - Run tests with coverage report"
	@echo "make test-fast     - Run fast smoke tests"
	@echo "make test-new      - Run all new tests added for container automation"
	@echo "make test-cli-input - Run CLI input handling tests"
	@echo "make test-completion - Run CLI completion tests"
	@echo "make test-interrupt - Run CLI interrupt handling tests"
	@echo "make test-docker   - Run Docker entrypoint tests"
	@echo "make test-shell    - Run shell script tests"
	@echo "make test-workflows - Run functional CLI workflow tests"
	@echo "make test-compose  - Run Docker Compose tests"
	@echo "make lint          - Run linters (ruff, mypy)"
	@echo "make format        - Auto-format code"
	@echo "make clean         - Clean generated files"
	@echo "make install-dev   - Install development dependencies"
	@echo "make pre-commit    - Run checks before committing"
	@echo "make version       - Update version to current timestamp"
	@echo ""
	@echo "Docker Commands"
	@echo "==============="
	@echo "make docker-build       - Build production Docker image (with Ollama)"
	@echo "make docker-build-oci   - Build lightweight OCI-focused image"
	@echo "make docker-build-multi - Build multi-architecture image"
	@echo "make docker-run         - Run Coda in Docker container (with Ollama)"
	@echo "make docker-run-oci     - Run lightweight OCI-focused container"
	@echo "make docker-dev         - Build and run development container"
	@echo "make docker-dev-up      - Start development environment"
	@echo "make docker-dev-down    - Stop development environment"
	@echo "make docker-oci-up      - Start OCI-focused environment"
	@echo "make docker-oci-down    - Stop OCI-focused environment"
	@echo "make docker-test        - Run tests in Docker container"
	@echo "make docker-test-llm    - Run LLM tests with Docker Ollama"
	@echo "make docker-clean       - Clean Docker images and containers"
	@echo "make docker-push        - Push Docker image to registry"

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

# Run LLM tests with Ollama (requires Ollama service)
test-llm:
	@echo "Starting Ollama service for LLM tests..."
	@if ! curl -s http://localhost:11434/api/health > /dev/null 2>&1; then \
		echo "❌ Ollama not running. Start with: ollama serve"; \
		exit 1; \
	fi
	@echo "✅ Ollama is running"
	RUN_LLM_TESTS=1 OLLAMA_HOST=http://localhost:11434 \
		uv run pytest tests/llm/ -v -m llm --tb=short

# Run tests with coverage
test-cov:
	uv run pytest tests/ -v -m "unit or not integration" \
		--cov=coda --cov-report=html --cov-report=term-missing

# Run fast smoke tests
test-fast:
	uv run pytest tests/test_smoke.py -v

# Run CLI input tests
test-cli-input:
	uv run pytest tests/cli/test_interactive_cli_input.py -v --tb=short

# Run CLI completion tests
test-completion:
	uv run pytest tests/cli/test_cli_completion.py -v --tb=short

# Run CLI interrupt tests  
test-interrupt:
	uv run pytest tests/cli/test_cli_interrupt.py -v --tb=short

# Run Docker entrypoint tests
test-docker:
	uv run pytest tests/integration/test_docker_entrypoints.py -v --tb=short

# Run shell script tests
test-shell:
	uv run pytest tests/integration/test_shell_scripts.py -v --tb=short

# Run functional workflow tests
test-workflows:
	uv run pytest tests/functional/test_cli_workflows.py -v --tb=short

# Run Docker Compose tests
test-compose:
	uv run pytest tests/functional/test_docker_compose.py -v --tb=short

# Run all new tests
test-new: test-cli-input test-completion test-interrupt test-docker test-shell test-workflows test-compose
	@echo "All new tests completed ✓"

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

# Docker Commands
# ===============

# Build production Docker image (with Ollama)
docker-build:
	docker build -f docker/Dockerfile -t coda-code-assistant:latest .
	@echo "Production Docker image built ✓"

# Build lightweight OCI-focused image
docker-build-oci:
	docker build -f docker/Dockerfile.oci -t coda-code-assistant:oci .
	@echo "OCI-focused Docker image built ✓"

# Build multi-architecture Docker image
docker-build-multi:
	docker buildx create --name coda-builder --use --bootstrap || true
	docker buildx build \
		--platform linux/amd64,linux/arm64 \
		-t coda-code-assistant:latest \
		--push \
		.
	@echo "Multi-architecture Docker image built and pushed ✓"

# Run Coda in Docker container (with Ollama)
docker-run:
	docker run -it --rm \
		-p 11434:11434 \
		-v coda-config:/home/coda/.config/coda \
		-v coda-cache:/home/coda/.cache/coda \
		-v coda-data:/home/coda/.local/share/coda \
		coda-code-assistant:latest

# Run lightweight OCI-focused container
docker-run-oci:
	docker run -it --rm \
		-v ~/.oci:/home/coda/.oci:ro \
		-v coda-oci-config:/home/coda/.config/coda \
		-v coda-oci-cache:/home/coda/.cache/coda \
		-v coda-oci-data:/home/coda/.local/share/coda \
		-e OCI_CLI_COMPARTMENT_ID="$(OCI_CLI_COMPARTMENT_ID)" \
		-e OCI_CLI_REGION="$(OCI_CLI_REGION)" \
		coda-code-assistant:oci

# Build and run development container
docker-dev:
	docker build -f docker/Dockerfile.dev -t coda-code-assistant:dev .
	docker run -it --rm \
		-p 11434:11434 \
		-v $(PWD):/app \
		-v coda-dev-config:/home/coda/.config/coda \
		-v coda-dev-cache:/home/coda/.cache/coda \
		-v coda-dev-data:/home/coda/.local/share/coda \
		coda-code-assistant:dev

# Start development environment with docker-compose
docker-dev-up:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml up -d
	@echo "Development environment started ✓"
	@echo "Access Coda: docker-compose exec coda bash"
	@echo "Access Ollama: http://localhost:11434"

# Stop development environment
docker-dev-down:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down
	@echo "Development environment stopped ✓"

# Start OCI-focused environment
docker-oci-up:
	docker-compose --profile oci up -d
	@echo "OCI environment started ✓"
	@echo "Access Coda: docker-compose exec coda-oci coda"

# Stop OCI environment
docker-oci-down:
	docker-compose --profile oci down
	@echo "OCI environment stopped ✓"

# Run tests in Docker container
docker-test:
	docker build -f docker/Dockerfile.dev -t coda-code-assistant:test .
	docker run --rm \
		-v $(PWD):/app \
		-e RUN_TESTS=true \
		coda-code-assistant:test \
		uv run pytest tests/ -v -m "unit or not integration"

# Run LLM tests with Docker Ollama
docker-test-llm:
	@echo "Starting Docker-based LLM tests..."
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.test.yml up -d ollama-test
	@echo "Waiting for Ollama to be ready..."
	@timeout 60 bash -c 'until curl -s http://localhost:11435/api/health > /dev/null 2>&1; do sleep 2; done'
	@echo "✅ Ollama is ready, running LLM tests..."
	RUN_LLM_TESTS=1 OLLAMA_HOST=http://localhost:11435 \
		CODA_TEST_MODEL=tinyllama:1.1b \
		uv run pytest tests/llm/ -v -m llm --tb=short
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.test.yml down

# Clean Docker images and containers
docker-clean:
	docker-compose -f docker/docker-compose.yml -f docker/docker-compose.dev.yml down -v --remove-orphans
	docker image prune -f
	docker volume prune -f
	@echo "Docker cleanup completed ✓"

# Push Docker image to registry (requires login)
docker-push:
	@echo "Pushing to Docker registry..."
	docker tag coda-code-assistant:latest $(REGISTRY)/coda-code-assistant:latest
	docker push $(REGISTRY)/coda-code-assistant:latest
	@echo "Docker image pushed ✓"