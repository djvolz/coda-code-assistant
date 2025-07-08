#!/bin/bash
# Script to run all agent-related tests

set -e

echo "🧪 Running Agent Tests Suite"
echo "=========================="

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to run tests and check results
run_test_suite() {
    local suite_name=$1
    local test_command=$2
    
    echo -e "\n${YELLOW}Running ${suite_name}...${NC}"
    
    if eval "$test_command"; then
        echo -e "${GREEN}✓ ${suite_name} passed${NC}"
        return 0
    else
        echo -e "${RED}✗ ${suite_name} failed${NC}"
        return 1
    fi
}

# Track failures
FAILED=0

# 1. Run agent unit tests
run_test_suite "Agent Unit Tests" \
    "python -m pytest tests/agents/test_decorators.py tests/agents/test_function_tool.py tests/agents/test_builtin_tools.py tests/agents/test_tool_adapter.py -v" || FAILED=$((FAILED + 1))

# 2. Run agent integration tests
run_test_suite "Agent Integration Tests" \
    "python -m pytest tests/agents/test_agent_tool_integration.py -v" || FAILED=$((FAILED + 1))

# 3. Run CLI workflow tests
run_test_suite "CLI Agent Workflow Tests" \
    "python -m pytest tests/cli/test_agent_chat_workflow.py tests/cli/test_tool_chat_workflow.py -v" || FAILED=$((FAILED + 1))

# 4. Run existing agent tests
run_test_suite "Existing Agent Tests" \
    "python -m pytest tests/test_agent.py tests/test_tool_calling.py tests/test_oci_tool_calling.py -v" || FAILED=$((FAILED + 1))

# 5. Run tool tests
run_test_suite "Tool Tests" \
    "python -m pytest tests/tools/ -v" || FAILED=$((FAILED + 1))

# Generate coverage report
echo -e "\n${YELLOW}Generating coverage report...${NC}"
python -m pytest tests/agents/ tests/tools/ tests/cli/*agent* tests/cli/*tool* \
    --cov=coda/agents --cov=coda/tools --cov=coda/cli/agent_chat --cov=coda/cli/tool_chat \
    --cov-report=html --cov-report=term --quiet

echo -e "\n${YELLOW}Test Summary${NC}"
echo "============"

if [ $FAILED -eq 0 ]; then
    echo -e "${GREEN}All test suites passed! 🎉${NC}"
    echo -e "Coverage report generated in htmlcov/"
    exit 0
else
    echo -e "${RED}${FAILED} test suite(s) failed 😞${NC}"
    exit 1
fi