#!/bin/bash
set -e

echo "🚀 Setting up Ollama for LLM testing..."

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

# Wait for Ollama to be ready
echo "⏳ Waiting for Ollama at ${OLLAMA_HOST}..."
timeout $TIMEOUT bash -c "
    while ! check_ollama; do 
        echo '  Waiting for Ollama service...'
        sleep 2
    done
"

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
    timeout $TIMEOUT bash -c "
        while ! check_model; do 
            echo '  Downloading model...'
            sleep 5
        done
    "
    
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