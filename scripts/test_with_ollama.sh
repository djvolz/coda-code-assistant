#!/bin/bash
set -e

# Function to check dependencies
check_dependencies() {
    for cmd in curl grep; do
        if ! command -v $cmd &> /dev/null; then
            echo "❌ Required command not found: $cmd"
            exit 1
        fi
    done
}

# Function to wait for condition with timeout
wait_for_condition() {
    local condition_fn=$1
    local message=$2
    local timeout=$3
    
    local counter=0
    while ! $condition_fn; do
        if [ $counter -ge $timeout ]; then
            return 1
        fi
        echo "  $message"
        sleep 2
        counter=$((counter + 2))
    done
    return 0
}

echo "🚀 Setting up Ollama for LLM testing..."

# Check dependencies first
check_dependencies

# Configuration
OLLAMA_HOST=${OLLAMA_HOST:-"http://localhost:11434"}
TEST_MODEL=${CODA_TEST_MODEL:-"tinyllama:1.1b"}
TIMEOUT=${OLLAMA_TIMEOUT:-300}

# Function to check if Ollama is ready
check_ollama() {
    curl -f "${OLLAMA_HOST}/api/health" > /dev/null 2>&1
}

# Function to check if model is available
check_model() {
    curl -s "${OLLAMA_HOST}/api/tags" | grep -q "$TEST_MODEL"
}

# Validate OLLAMA_HOST URL format
if ! echo "$OLLAMA_HOST" | grep -qE '^https?://'; then
    echo "❌ Invalid OLLAMA_HOST format: $OLLAMA_HOST (must start with http:// or https://)"
    exit 1
fi

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama at ${OLLAMA_HOST}..."
if ! wait_for_condition check_ollama "Waiting for Ollama service..." $TIMEOUT; then
    echo "❌ Timeout waiting for Ollama service at ${OLLAMA_HOST}"
    exit 1
fi

if ! check_ollama; then
    echo "❌ Ollama service not available at ${OLLAMA_HOST}"
    exit 1
fi

echo "✅ Ollama service is ready!"

# Pull test model if not available
if ! check_model; then
    echo "📦 Pulling test model: ${TEST_MODEL}..."
    
    curl -X POST "${OLLAMA_HOST}/api/pull" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${TEST_MODEL}\"}" &
    
    PULL_PID=$!
    
    # Wait for model to be available
    if ! wait_for_condition check_model "Downloading model..." $TIMEOUT; then
        echo "❌ Timeout waiting for model ${TEST_MODEL}"
        kill $PULL_PID 2>/dev/null || true
        exit 1
    fi
    
    wait $PULL_PID || true
    
    if ! check_model; then
        echo "❌ Failed to pull model: ${TEST_MODEL}"
        exit 1
    fi
fi

echo "✅ Model ${TEST_MODEL} is available!"

# Run the LLM tests
echo "🧪 Running LLM tests..."
export RUN_LLM_TESTS=true
export OLLAMA_HOST="$OLLAMA_HOST"
export CODA_TEST_PROVIDER=ollama
export CODA_TEST_MODEL="$TEST_MODEL"

uv run pytest tests/llm/ -v -m llm --tb=short

echo "✅ LLM tests completed successfully!"

# Optional cleanup
if [ "${CLEANUP_MODEL:-false}" = "true" ]; then
    echo "🧹 Cleaning up test model..."
    curl -X DELETE "${OLLAMA_HOST}/api/delete" \
        -H "Content-Type: application/json" \
        -d "{\"name\": \"${TEST_MODEL}\"}" || true
fi

echo "🎉 All done!"