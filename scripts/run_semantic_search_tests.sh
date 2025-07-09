#!/bin/bash
# Run all semantic search related tests

set -e

echo "Running Semantic Search Tests"
echo "============================"

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests with nice output
run_test_module() {
    local module=$1
    local description=$2
    
    echo -e "\n${YELLOW}Testing: ${description}${NC}"
    if uv run python -m pytest "$module" -v; then
        echo -e "${GREEN}✓ ${description} passed${NC}"
    else
        echo -e "${RED}✗ ${description} failed${NC}"
        exit 1
    fi
}

# Unit tests
echo -e "\n${YELLOW}=== Unit Tests ===${NC}"
run_test_module "tests/test_chunking.py" "Chunking Module"
run_test_module "tests/embeddings/test_mock.py" "Mock Embedding Provider"
run_test_module "tests/embeddings/test_sentence_transformers.py" "Sentence Transformers Provider"
run_test_module "tests/embeddings/test_ollama.py" "Ollama Provider"
run_test_module "tests/embeddings/test_oci_embeddings.py" "OCI Embedding Provider"
run_test_module "tests/embeddings/test_factory.py" "Embedding Factory"
run_test_module "tests/vector_stores/test_faiss_store.py" "FAISS Vector Store"
run_test_module "tests/test_semantic_search.py" "Semantic Search Manager"
run_test_module "tests/cli/test_search_display.py" "Search Display UI"

# Integration tests
echo -e "\n${YELLOW}=== Integration Tests ===${NC}"
run_test_module "tests/integration/test_semantic_search_integration.py" "Semantic Search Integration"
run_test_module "tests/integration/test_semantic_search_cli.py" "CLI Integration"

# Coverage report
echo -e "\n${YELLOW}=== Coverage Report ===${NC}"
uv run python -m pytest \
    tests/test_chunking.py \
    tests/embeddings/test_*.py \
    tests/vector_stores/test_*.py \
    tests/test_semantic_search.py \
    tests/cli/test_search_display.py \
    tests/integration/test_semantic_search*.py \
    --cov=coda.chunking \
    --cov=coda.embeddings \
    --cov=coda.vector_stores \
    --cov=coda.semantic_search \
    --cov=coda.semantic_search_coda \
    --cov=coda.cli.search_display \
    --cov-report=term-missing \
    --cov-report=html:htmlcov/semantic_search

echo -e "\n${GREEN}All tests passed!${NC}"
echo "Coverage report available in htmlcov/semantic_search/index.html"