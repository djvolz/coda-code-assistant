#!/bin/bash
set -e

# Start Ollama service in the background
echo "Starting Ollama service..."
ollama serve &
OLLAMA_PID=$!

# Wait for Ollama to be ready
echo "Waiting for Ollama to be ready..."
while ! curl -s http://localhost:11434/api/health > /dev/null 2>&1; do
    sleep 1
done

echo "Ollama is ready!"

# Pull a default model if none exists (optional - can be overridden)
if [ "${OLLAMA_PULL_DEFAULT:-true}" = "true" ]; then
    echo "Pulling default model (llama3.2:3b)..."
    ollama pull llama3.2:3b || echo "Failed to pull default model, continuing..."
fi

# Function to cleanup on exit
cleanup() {
    echo "Shutting down Ollama..."
    kill $OLLAMA_PID 2>/dev/null || true
    wait $OLLAMA_PID 2>/dev/null || true
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT

# Execute the main command
if [ "$1" = "coda" ]; then
    echo "Starting Coda..."
    exec coda "${@:2}"
else
    exec "$@"
fi