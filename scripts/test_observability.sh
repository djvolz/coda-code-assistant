#!/bin/bash
# Script to run observability tests locally with coverage

set -e

echo "🧪 Running Observability Tests"
echo "=============================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests and check result
run_tests() {
    local test_name=$1
    local test_command=$2
    
    echo -e "\n${YELLOW}Running ${test_name}...${NC}"
    if eval "$test_command"; then
        echo -e "${GREEN}✓ ${test_name} passed${NC}"
        return 0
    else
        echo -e "${RED}✗ ${test_name} failed${NC}"
        return 1
    fi
}

# Check if we're in a virtual environment
if [ -z "$VIRTUAL_ENV" ]; then
    echo "⚠️  Warning: Not in a virtual environment. Using uv run..."
    PYTEST_CMD="uv run python -m pytest"
else
    PYTEST_CMD="python -m pytest"
fi

# Parse command line arguments
RUN_ALL=true
RUN_UNIT=false
RUN_INTEGRATION=false
RUN_FUNCTIONAL=false
COVERAGE_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --unit)
            RUN_ALL=false
            RUN_UNIT=true
            shift
            ;;
        --integration)
            RUN_ALL=false
            RUN_INTEGRATION=true
            shift
            ;;
        --functional)
            RUN_ALL=false
            RUN_FUNCTIONAL=true
            shift
            ;;
        --coverage)
            COVERAGE_ONLY=true
            shift
            ;;
        --help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  --unit          Run only unit tests"
            echo "  --integration   Run only integration tests"
            echo "  --functional    Run only functional tests"
            echo "  --coverage      Generate coverage report only"
            echo "  --help          Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
            ;;
    esac
done

# Create test results directory
mkdir -p test-results

if [ "$COVERAGE_ONLY" = true ]; then
    echo -e "\n${YELLOW}Generating coverage report...${NC}"
    $PYTEST_CMD \
        tests/unit/observability/ tests/unit/cli/ tests/unit/test_configuration.py \
        tests/integration/observability/ tests/functional/test_observability_workflows.py \
        --cov=coda.observability --cov=coda.cli --cov=coda.configuration \
        --cov-report=html:test-results/htmlcov \
        --cov-report=term \
        --cov-report=xml:test-results/coverage.xml \
        -q
    echo -e "${GREEN}Coverage report generated in test-results/htmlcov/index.html${NC}"
    exit 0
fi

# Track overall success
ALL_PASSED=true

# Run unit tests
if [ "$RUN_ALL" = true ] || [ "$RUN_UNIT" = true ]; then
    if ! run_tests "Observability Unit Tests" "$PYTEST_CMD tests/unit/observability/ -v -m 'unit or not integration'"; then
        ALL_PASSED=false
    fi
    
    if ! run_tests "CLI Unit Tests" "$PYTEST_CMD tests/unit/cli/ -v -m 'unit or not integration'"; then
        ALL_PASSED=false
    fi
    
    if ! run_tests "Configuration Unit Tests" "$PYTEST_CMD tests/unit/test_configuration.py -v -m 'unit or not integration'"; then
        ALL_PASSED=false
    fi
fi

# Run integration tests
if [ "$RUN_ALL" = true ] || [ "$RUN_INTEGRATION" = true ]; then
    if ! run_tests "Observability Integration Tests" "$PYTEST_CMD tests/integration/observability/ -v -m integration"; then
        ALL_PASSED=false
    fi
fi

# Run functional tests
if [ "$RUN_ALL" = true ] || [ "$RUN_FUNCTIONAL" = true ]; then
    if ! run_tests "Observability Functional Tests" "$PYTEST_CMD tests/functional/test_observability_workflows.py -v -m functional"; then
        ALL_PASSED=false
    fi
fi

# Generate coverage report if all tests passed
if [ "$ALL_PASSED" = true ] && [ "$RUN_ALL" = true ]; then
    echo -e "\n${YELLOW}Generating coverage report...${NC}"
    $PYTEST_CMD \
        tests/unit/observability/ tests/unit/cli/ tests/unit/test_configuration.py \
        tests/integration/observability/ \
        --cov=coda.observability --cov=coda.cli --cov=coda.configuration \
        --cov-report=html:test-results/htmlcov \
        --cov-report=term-missing \
        --cov-report=xml:test-results/coverage.xml \
        -q
    
    echo -e "\n${GREEN}✓ All tests passed!${NC}"
    echo -e "Coverage report available at: test-results/htmlcov/index.html"
else
    echo -e "\n${RED}✗ Some tests failed${NC}"
    exit 1
fi

# Check coverage thresholds
echo -e "\n${YELLOW}Checking coverage thresholds...${NC}"
COVERAGE_OUTPUT=$($PYTEST_CMD \
    tests/unit/observability/ tests/unit/cli/ tests/unit/test_configuration.py \
    --cov=coda.observability --cov=coda.cli --cov=coda.configuration \
    --cov-report=term \
    -q 2>&1 | grep "TOTAL" | awk '{print $NF}' | sed 's/%//')

if [ -n "$COVERAGE_OUTPUT" ]; then
    COVERAGE=${COVERAGE_OUTPUT%.*}
    if [ "$COVERAGE" -ge 80 ]; then
        echo -e "${GREEN}✓ Coverage ${COVERAGE}% meets threshold (80%)${NC}"
    else
        echo -e "${RED}✗ Coverage ${COVERAGE}% below threshold (80%)${NC}"
        exit 1
    fi
fi