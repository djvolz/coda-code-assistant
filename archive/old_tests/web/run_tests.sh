#!/bin/bash
# Script to run web UI tests locally

set -e

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
BROWSER="chrome"
TEST_TYPE="all"
HEADLESS="true"
PORT=8600

# Parse command line arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --browser)
      BROWSER="$2"
      shift 2
      ;;
    --type)
      TEST_TYPE="$2"
      shift 2
      ;;
    --headed)
      HEADLESS="false"
      shift
      ;;
    --port)
      PORT="$2"
      shift 2
      ;;
    --help)
      echo "Usage: $0 [options]"
      echo "Options:"
      echo "  --browser <chrome|firefox>  Browser to use (default: chrome)"
      echo "  --type <unit|integration|functional|all>  Test type to run (default: all)"
      echo "  --headed                    Run browser tests in headed mode"
      echo "  --port <port>              Port for Streamlit server (default: 8600)"
      echo "  --help                     Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      exit 1
      ;;
  esac
done

echo -e "${GREEN}Web UI Test Runner${NC}"
echo "===================="
echo "Browser: $BROWSER"
echo "Test Type: $TEST_TYPE"
echo "Headless: $HEADLESS"
echo "Port: $PORT"
echo ""

# Check if required dependencies are installed
echo -e "${YELLOW}Checking dependencies...${NC}"

# Check for Python
if ! command -v python &> /dev/null; then
    echo -e "${RED}Python is not installed${NC}"
    exit 1
fi

# Check for pytest
if ! python -m pytest --version &> /dev/null; then
    echo -e "${RED}pytest is not installed. Run: pip install pytest${NC}"
    exit 1
fi

# Check for selenium
if ! python -c "import selenium" &> /dev/null; then
    echo -e "${RED}selenium is not installed. Run: pip install selenium${NC}"
    exit 1
fi

# Check for streamlit
if ! command -v streamlit &> /dev/null; then
    echo -e "${RED}streamlit is not installed. Run: pip install streamlit${NC}"
    exit 1
fi

# Create necessary directories
mkdir -p tests/web/screenshots
mkdir -p tests/web/logs

# Function to cleanup on exit
cleanup() {
    if [ ! -z "$SERVER_PID" ]; then
        echo -e "\n${YELLOW}Stopping Streamlit server...${NC}"
        kill $SERVER_PID 2>/dev/null || true
        wait $SERVER_PID 2>/dev/null || true
    fi
}

# Set up cleanup trap
trap cleanup EXIT

# Run unit tests if requested
if [ "$TEST_TYPE" = "unit" ] || [ "$TEST_TYPE" = "all" ]; then
    echo -e "\n${GREEN}Running unit tests...${NC}"
    python -m pytest tests/web/unit/ -v --tb=short || {
        echo -e "${RED}Unit tests failed${NC}"
        exit 1
    }
fi

# Start Streamlit server for browser tests
if [ "$TEST_TYPE" != "unit" ]; then
    echo -e "\n${YELLOW}Starting Streamlit server on port $PORT...${NC}"
    
    # Kill any existing server on the port
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    
    # Start server
    streamlit run coda/web/app.py \
        --server.headless true \
        --server.port $PORT \
        --server.enableCORS false \
        --server.enableXsrfProtection false \
        > tests/web/logs/streamlit.log 2>&1 &
    
    SERVER_PID=$!
    
    # Wait for server to start
    echo "Waiting for server to start..."
    for i in {1..30}; do
        if curl -s http://localhost:$PORT > /dev/null; then
            echo -e "${GREEN}Server is ready!${NC}"
            break
        fi
        echo -n "."
        sleep 2
    done
    
    if ! curl -s http://localhost:$PORT > /dev/null; then
        echo -e "${RED}Failed to start Streamlit server${NC}"
        echo "Server logs:"
        cat tests/web/logs/streamlit.log
        exit 1
    fi
fi

# Export environment variables for tests
export BROWSER=$BROWSER
export BASE_URL="http://localhost:$PORT"
export HEADLESS=$HEADLESS

# Run integration tests if requested
if [ "$TEST_TYPE" = "integration" ] || [ "$TEST_TYPE" = "all" ]; then
    echo -e "\n${GREEN}Running integration tests...${NC}"
    python -m pytest tests/web/integration/ -v --tb=short || {
        echo -e "${RED}Integration tests failed${NC}"
        exit 1
    }
fi

# Run functional tests if requested
if [ "$TEST_TYPE" = "functional" ] || [ "$TEST_TYPE" = "all" ]; then
    echo -e "\n${GREEN}Running functional tests...${NC}"
    python -m pytest tests/web/functional/ -v --tb=short || {
        echo -e "${RED}Functional tests failed${NC}"
        exit 1
    }
fi

echo -e "\n${GREEN}All tests passed!${NC}"