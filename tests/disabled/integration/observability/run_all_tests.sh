#!/bin/bash
# Run all observability integration tests

echo "=== Running Observability Integration Test Suite ==="
echo "This will run all tests created for Phase 11.2"
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test categories
declare -a test_categories=(
    "Provider Command Tests"
    "Configuration State Tests"
    "Data Export Tests"
    "Error Handling Tests"
    "Advanced Tests"
)

declare -a test_files=(
    "test_mock_provider_commands.py"
    "test_ollama_provider_commands.py"
    "test_enabled_disabled_states.py"
    "test_component_configurations.py"
    "test_export_formats.py"
    "test_error_scenarios.py"
    "test_retention_policies.py"
    "test_memory_limits.py"
    "test_load_testing.py"
    "test_thread_safety.py"
)

# Function to run a test file
run_test() {
    local test_file=$1
    echo -e "${YELLOW}Running $test_file...${NC}"
    
    if uv run pytest "tests/integration/observability/$test_file" -v --run-integration; then
        echo -e "${GREEN}✓ $test_file passed${NC}"
        return 0
    else
        echo -e "${RED}✗ $test_file failed${NC}"
        return 1
    fi
    echo ""
}

# Run all tests
total_tests=${#test_files[@]}
passed_tests=0
failed_tests=0

echo "Found $total_tests test files to run"
echo "================================"
echo ""

for test_file in "${test_files[@]}"; do
    if run_test "$test_file"; then
        ((passed_tests++))
    else
        ((failed_tests++))
    fi
done

echo ""
echo "================================"
echo "Test Summary:"
echo -e "${GREEN}Passed: $passed_tests${NC}"
echo -e "${RED}Failed: $failed_tests${NC}"
echo ""

# Run with coverage if requested
if [[ "$1" == "--coverage" ]]; then
    echo "Running with coverage analysis..."
    uv run pytest tests/integration/observability/ -v --run-integration --cov=coda.observability --cov-report=html --cov-report=term
    echo "Coverage report generated in htmlcov/"
fi

# Run only slow tests if requested
if [[ "$1" == "--slow" ]]; then
    echo "Running slow tests (load testing)..."
    uv run pytest tests/integration/observability/test_load_testing.py -v --run-integration -m slow
fi

# Exit with appropriate code
if [[ $failed_tests -eq 0 ]]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi