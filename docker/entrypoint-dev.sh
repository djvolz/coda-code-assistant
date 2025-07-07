#!/bin/bash
set -e

echo "Starting Coda development environment..."

# Install the package in development mode
if [ -f "/app/pyproject.toml" ]; then
    echo "Installing Coda in development mode..."
    cd /app
    uv pip install -e .
fi

# Wait for external Ollama service if configured
if [ "$OLLAMA_HOST" != "127.0.0.1:11434" ]; then
    echo "Waiting for external Ollama service at $OLLAMA_HOST..."
    while ! curl -s "http://$OLLAMA_HOST/api/health" > /dev/null 2>&1; do
        sleep 1
    done
    echo "External Ollama service is ready!"
fi

# Run tests if requested
if [ "${RUN_TESTS:-false}" = "true" ]; then
    echo "Running tests..."
    make test
fi

# Execute the main command
exec "$@"