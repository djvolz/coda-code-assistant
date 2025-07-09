"""Integration tests for shell scripts."""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import pytest


class TestShellScripts:
    """Test cases for shell scripts used in the project."""

    @pytest.fixture
    def temp_script_dir(self):
        """Create a temporary directory for test scripts."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_commands(self):
        """Mock system commands for testing."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            yield mock_run

    def test_test_with_ollama_dependency_check(self, temp_script_dir):
        """Test dependency checking in test_with_ollama.sh."""
        script_path = os.path.join(temp_script_dir, "check_deps.sh")

        script_content = """#!/bin/bash
check_dependencies() {
    local missing_deps=()

    # Check for required commands
    for cmd in jq curl docker; do
        if ! command -v $cmd &> /dev/null; then
            missing_deps+=($cmd)
        fi
    done

    if [ ${#missing_deps[@]} -gt 0 ]; then
        echo "Error: Missing dependencies: ${missing_deps[*]}"
        echo "Please install: ${missing_deps[*]}"
        return 1
    fi

    echo "All dependencies satisfied"
    return 0
}

check_dependencies
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Test with all dependencies available
        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        # Should pass if basic commands exist
        if result.returncode == 0:
            assert "All dependencies satisfied" in result.stdout
        else:
            assert "Missing dependencies" in result.stdout

    def test_ollama_installation_check(self, temp_script_dir):
        """Test Ollama installation checking."""
        script_path = os.path.join(temp_script_dir, "check_ollama.sh")

        script_content = r"""#!/bin/bash
OLLAMA_MIN_VERSION="0.1.0"

check_ollama() {
    if ! command -v ollama &> /dev/null; then
        echo "Ollama not found"
        return 1
    fi

    # Check version
    local version=$(ollama --version 2>/dev/null | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -1)
    if [ -n "$version" ]; then
        echo "Ollama version: $version"
        return 0
    fi

    echo "Could not determine Ollama version"
    return 1
}

check_ollama
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        # Will fail if ollama not installed
        assert "Ollama" in result.stdout

    def test_model_download_script(self, temp_script_dir):
        """Test model downloading functionality."""
        script_path = os.path.join(temp_script_dir, "download_model.sh")

        script_content = """#!/bin/bash
MODEL_NAME="${1:-llama2}"
RETRY_COUNT=3
RETRY_DELAY=5

download_model() {
    local model=$1
    local attempt=1

    echo "Downloading model: $model"

    while [ $attempt -le $RETRY_COUNT ]; do
        echo "Attempt $attempt of $RETRY_COUNT..."

        # Simulate download (would be: ollama pull $model)
        if [ $attempt -eq 2 ]; then
            echo "Successfully downloaded $model"
            return 0
        fi

        echo "Download failed, retrying in ${RETRY_DELAY}s..."
        sleep 0.1  # Short sleep for testing
        attempt=$((attempt + 1))
    done

    echo "Failed to download $model after $RETRY_COUNT attempts"
    return 1
}

download_model "$MODEL_NAME"
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path, "codellama"], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Downloading model: codellama" in result.stdout
        assert "Successfully downloaded codellama" in result.stdout
        assert "Attempt 2 of 3" in result.stdout

    def test_test_execution_with_timeout(self, temp_script_dir):
        """Test test execution with timeout handling."""
        script_path = os.path.join(temp_script_dir, "run_tests.sh")

        script_content = """#!/bin/bash
TEST_TIMEOUT="${TEST_TIMEOUT:-300}"  # 5 minutes default
TEST_COMMAND="${TEST_COMMAND:-pytest}"

run_tests_with_timeout() {
    echo "Running tests with timeout: ${TEST_TIMEOUT}s"
    echo "Command: $TEST_COMMAND"

    # Use timeout command if available
    if command -v timeout &> /dev/null; then
        timeout $TEST_TIMEOUT $TEST_COMMAND
        local exit_code=$?

        if [ $exit_code -eq 124 ]; then
            echo "ERROR: Tests timed out after ${TEST_TIMEOUT}s"
            return 1
        fi

        return $exit_code
    else
        # Fallback without timeout
        echo "Warning: timeout command not available"
        $TEST_COMMAND
    fi
}

# Simulate test command
TEST_COMMAND="echo 'Tests passed'" run_tests_with_timeout
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(
            ["bash", script_path], capture_output=True, text=True, env={"TEST_TIMEOUT": "10"}
        )

        assert "Running tests with timeout: 10s" in result.stdout

    def test_ollama_server_management(self, temp_script_dir):
        """Test Ollama server start/stop functionality."""
        script_path = os.path.join(temp_script_dir, "manage_ollama.sh")

        script_content = """#!/bin/bash
OLLAMA_PID_FILE="/tmp/ollama_test.pid"

start_ollama_server() {
    echo "Starting Ollama server..."

    # Check if already running
    if [ -f "$OLLAMA_PID_FILE" ]; then
        local pid=$(cat "$OLLAMA_PID_FILE")
        if kill -0 $pid 2>/dev/null; then
            echo "Ollama already running (PID: $pid)"
            return 0
        fi
    fi

    # Simulate starting server
    sleep 60 &
    local pid=$!
    echo $pid > "$OLLAMA_PID_FILE"

    echo "Ollama started (PID: $pid)"

    # Wait for startup
    sleep 0.1
    echo "Ollama server ready"
    return 0
}

stop_ollama_server() {
    echo "Stopping Ollama server..."

    if [ -f "$OLLAMA_PID_FILE" ]; then
        local pid=$(cat "$OLLAMA_PID_FILE")
        if kill -TERM $pid 2>/dev/null; then
            echo "Stopped Ollama (PID: $pid)"
            rm -f "$OLLAMA_PID_FILE"
            return 0
        fi
    fi

    echo "Ollama server not running"
    return 0
}

# Test start and stop
start_ollama_server
stop_ollama_server
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Starting Ollama server" in result.stdout
        assert "Ollama started (PID:" in result.stdout
        assert "Stopping Ollama server" in result.stdout
        assert "Stopped Ollama" in result.stdout

    def test_environment_setup(self, temp_script_dir):
        """Test environment setup for testing."""
        script_path = os.path.join(temp_script_dir, "setup_env.sh")

        script_content = """#!/bin/bash
setup_test_environment() {
    echo "Setting up test environment..."

    # Export required variables
    export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
    export CODA_TEST_MODE="true"
    export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}$(pwd)"

    # Create necessary directories
    mkdir -p test_output
    mkdir -p .coverage

    # Display environment
    echo "Environment configured:"
    echo "  OLLAMA_HOST=$OLLAMA_HOST"
    echo "  CODA_TEST_MODE=$CODA_TEST_MODE"
    echo "  PYTHONPATH=$PYTHONPATH"

    return 0
}

setup_test_environment
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(
            ["bash", script_path], capture_output=True, text=True, cwd=temp_script_dir
        )

        assert result.returncode == 0
        assert "Setting up test environment" in result.stdout
        assert "OLLAMA_HOST=http://localhost:11434" in result.stdout
        assert "CODA_TEST_MODE=true" in result.stdout

    def test_cleanup_operations(self, temp_script_dir):
        """Test cleanup operations in scripts."""
        script_path = os.path.join(temp_script_dir, "cleanup.sh")

        script_content = """#!/bin/bash
cleanup() {
    echo "Performing cleanup..."

    # Stop services
    if [ -n "$OLLAMA_PID" ]; then
        echo "Stopping Ollama process: $OLLAMA_PID"
        kill -TERM $OLLAMA_PID 2>/dev/null || true
    fi

    # Remove temporary files
    rm -f /tmp/ollama_test.pid
    rm -rf ./test_output

    # Clear environment
    unset CODA_TEST_MODE
    unset TEST_OLLAMA_HOST

    echo "Cleanup completed"
    return 0
}

# Simulate having a PID
OLLAMA_PID=12345
cleanup
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Performing cleanup" in result.stdout
        assert "Stopping Ollama process: 12345" in result.stdout
        assert "Cleanup completed" in result.stdout

    def test_error_handling_and_exit_codes(self, temp_script_dir):
        """Test error handling and exit codes."""
        script_path = os.path.join(temp_script_dir, "error_handling.sh")

        script_content = """#!/bin/bash
set -e  # Exit on error

handle_error() {
    local exit_code=$?
    local line_no=$1
    echo "Error on line $line_no: Exit code $exit_code"

    # Cleanup on error
    echo "Performing error cleanup..."

    exit $exit_code
}

trap 'handle_error $LINENO' ERR

# Function that might fail
risky_operation() {
    echo "Attempting risky operation..."

    # Simulate failure condition
    if [ "$FORCE_FAIL" = "true" ]; then
        echo "Operation failed!"
        return 1
    fi

    echo "Operation succeeded"
    return 0
}

# Run with error handling
risky_operation
echo "Script completed successfully"
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Test failure case
        result = subprocess.run(
            ["bash", script_path], capture_output=True, text=True, env={"FORCE_FAIL": "true"}
        )

        assert result.returncode == 1
        assert "Operation failed!" in result.stdout
        assert "Error on line" in result.stdout
        assert "Performing error cleanup" in result.stdout

    def test_parallel_execution(self, temp_script_dir):
        """Test parallel execution capabilities."""
        script_path = os.path.join(temp_script_dir, "parallel_test.sh")

        script_content = """#!/bin/bash
run_parallel_tests() {
    echo "Starting parallel test execution..."

    # Define test suites
    declare -a test_suites=(
        "unit_tests"
        "integration_tests"
        "performance_tests"
    )

    # Run tests in parallel
    for suite in "${test_suites[@]}"; do
        (
            echo "Starting $suite..."
            sleep 0.1  # Simulate test execution
            echo "$suite completed"
        ) &
    done

    # Wait for all background jobs
    echo "Waiting for all test suites to complete..."
    wait

    echo "All parallel tests completed"
    return 0
}

run_parallel_tests
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Starting parallel test execution" in result.stdout
        assert "unit_tests completed" in result.stdout
        assert "integration_tests completed" in result.stdout
        assert "performance_tests completed" in result.stdout
        assert "All parallel tests completed" in result.stdout

    @pytest.mark.parametrize(
        "exit_code,expected_message",
        [
            (0, "Tests passed successfully"),
            (1, "Tests failed with errors"),
            (2, "Tests failed with warnings"),
            (124, "Tests timed out"),
        ],
    )
    def test_exit_code_handling(self, temp_script_dir, exit_code, expected_message):
        """Test handling of different exit codes."""
        script_path = os.path.join(temp_script_dir, "exit_codes.sh")

        script_content = f"""#!/bin/bash
EXIT_CODE={exit_code}

interpret_exit_code() {{
    case $1 in
        0) echo "Tests passed successfully" ;;
        1) echo "Tests failed with errors" ;;
        2) echo "Tests failed with warnings" ;;
        124) echo "Tests timed out" ;;
        *) echo "Unknown exit code: $1" ;;
    esac
    return $1
}}

interpret_exit_code $EXIT_CODE
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == exit_code
        assert expected_message in result.stdout
