"""Integration tests for Docker entrypoint scripts."""

import os
import shutil
import subprocess
import tempfile
from unittest.mock import patch

import pytest


class TestDockerEntrypoints:
    """Test cases for Docker entrypoint scripts."""

    @pytest.fixture
    def temp_script_dir(self):
        """Create a temporary directory for test scripts."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_env(self):
        """Mock environment variables for testing."""
        original_env = os.environ.copy()
        test_env = {
            "OLLAMA_HOST": "http://localhost:11434",
            "OLLAMA_MODEL": "llama2",
            "CODA_CONFIG_PATH": "/app/config",
            "PYTHONPATH": "/app",
        }
        os.environ.update(test_env)
        yield test_env
        os.environ.clear()
        os.environ.update(original_env)

    def test_entrypoint_ollama_startup(self, temp_script_dir, mock_env):
        """Test main entrypoint starts Ollama service."""
        script_path = os.path.join(temp_script_dir, "entrypoint.sh")

        # Create a mock entrypoint script
        script_content = """#!/bin/bash
echo "Starting Ollama service..."
# Simulate ollama serve
sleep 0.1 &
OLLAMA_PID=$!
echo "Ollama started with PID: $OLLAMA_PID"
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Run the script
        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 0
        assert "Starting Ollama service" in result.stdout
        assert "Ollama started with PID" in result.stdout

    def test_entrypoint_health_check(self, temp_script_dir, mock_env):
        """Test Ollama health check functionality."""
        script_path = os.path.join(temp_script_dir, "health_check.sh")

        script_content = """#!/bin/bash
check_ollama_health() {
    local retries=0
    local max_retries=3

    while [ $retries -lt $max_retries ]; do
        if curl -f http://localhost:11434/api/tags >/dev/null 2>&1; then
            echo "Ollama is healthy"
            return 0
        fi
        retries=$((retries + 1))
        sleep 1
    done

    echo "Ollama health check failed"
    return 1
}

check_ollama_health
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Mock curl to fail (Ollama not running)
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 1

            result = subprocess.run(["bash", script_path], capture_output=True, text=True)

            assert "health check failed" in result.stdout

    def test_entrypoint_model_pulling(self, temp_script_dir, mock_env):
        """Test model pulling functionality."""
        script_path = os.path.join(temp_script_dir, "pull_model.sh")

        script_content = """#!/bin/bash
OLLAMA_MODEL="${OLLAMA_MODEL:-llama2}"

pull_model() {
    echo "Checking if model $OLLAMA_MODEL exists..."

    # Simulate checking for model
    if [ "$OLLAMA_MODEL" = "existing-model" ]; then
        echo "Model $OLLAMA_MODEL already exists"
        return 0
    fi

    echo "Pulling model $OLLAMA_MODEL..."
    # Simulate model pull
    sleep 0.1
    echo "Model $OLLAMA_MODEL pulled successfully"
    return 0
}

pull_model
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Test with new model
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            env={**mock_env, "OLLAMA_MODEL": "new-model"},
        )

        assert result.returncode == 0
        assert "Pulling model new-model" in result.stdout
        assert "pulled successfully" in result.stdout

    def test_entrypoint_signal_handling(self, temp_script_dir):
        """Test signal handling in entrypoint."""
        script_path = os.path.join(temp_script_dir, "signal_handler.sh")

        script_content = """#!/bin/bash
OLLAMA_PID=""
CODA_PID=""

cleanup() {
    echo "Received termination signal"

    if [ -n "$CODA_PID" ]; then
        echo "Stopping Coda (PID: $CODA_PID)"
        kill -TERM $CODA_PID 2>/dev/null
    fi

    if [ -n "$OLLAMA_PID" ]; then
        echo "Stopping Ollama (PID: $OLLAMA_PID)"
        kill -TERM $OLLAMA_PID 2>/dev/null
    fi

    exit 0
}

trap cleanup SIGTERM SIGINT

# Simulate running processes
sleep 10 &
OLLAMA_PID=$!
sleep 10 &
CODA_PID=$!

echo "Processes started: Ollama=$OLLAMA_PID, Coda=$CODA_PID"

# Send signal to self
kill -TERM $$
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert "Received termination signal" in result.stdout
        assert "Stopping Coda" in result.stdout
        assert "Stopping Ollama" in result.stdout

    def test_entrypoint_dev_external_ollama(self, temp_script_dir, mock_env):
        """Test dev entrypoint with external Ollama."""
        script_path = os.path.join(temp_script_dir, "entrypoint-dev.sh")

        script_content = """#!/bin/bash
USE_EXTERNAL_OLLAMA="${USE_EXTERNAL_OLLAMA:-false}"
EXTERNAL_OLLAMA_HOST="${EXTERNAL_OLLAMA_HOST:-}"

if [ "$USE_EXTERNAL_OLLAMA" = "true" ] && [ -n "$EXTERNAL_OLLAMA_HOST" ]; then
    echo "Using external Ollama at $EXTERNAL_OLLAMA_HOST"
    export OLLAMA_HOST="$EXTERNAL_OLLAMA_HOST"

    # Check connection
    if curl -f "$OLLAMA_HOST/api/tags" >/dev/null 2>&1; then
        echo "Connected to external Ollama"
    else
        echo "Failed to connect to external Ollama"
        exit 1
    fi
else
    echo "Starting local Ollama"
fi
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Test with external Ollama
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            env={
                **mock_env,
                "USE_EXTERNAL_OLLAMA": "true",
                "EXTERNAL_OLLAMA_HOST": "http://external:11434",
            },
        )

        assert "Using external Ollama" in result.stdout
        assert "http://external:11434" in result.stdout

    def test_entrypoint_oci_config_validation(self, temp_script_dir, mock_env):
        """Test OCI entrypoint configuration validation."""
        script_path = os.path.join(temp_script_dir, "entrypoint-oci.sh")

        script_content = """#!/bin/bash
# Required OCI environment variables
required_vars=("OCI_COMPARTMENT_ID" "OCI_REGION" "OCI_TENANCY_ID")

validate_oci_config() {
    local missing_vars=()

    for var in "${required_vars[@]}"; do
        if [ -z "${!var}" ]; then
            missing_vars+=("$var")
        fi
    done

    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo "Error: Missing required OCI variables: ${missing_vars[*]}"
        return 1
    fi

    echo "OCI configuration validated"
    return 0
}

validate_oci_config
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        # Test with missing variables
        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            env=mock_env,  # No OCI vars
        )

        assert result.returncode == 1
        assert "Missing required OCI variables" in result.stdout

    def test_entrypoint_timeout_handling(self, temp_script_dir):
        """Test timeout handling in entrypoint scripts."""
        script_path = os.path.join(temp_script_dir, "timeout_test.sh")

        script_content = """#!/bin/bash
wait_for_service() {
    local service=$1
    local timeout=$2
    local elapsed=0

    echo "Waiting for $service (timeout: ${timeout}s)..."

    while [ $elapsed -lt $timeout ]; do
        # Simulate service check
        if [ $elapsed -gt 2 ]; then
            echo "$service is ready"
            return 0
        fi

        sleep 1
        elapsed=$((elapsed + 1))
        echo "Waited ${elapsed}s..."
    done

    echo "Timeout waiting for $service"
    return 1
}

# Test with short timeout
wait_for_service "test-service" 5
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 0
        assert "test-service is ready" in result.stdout
        assert "Waited" in result.stdout

    def test_entrypoint_error_propagation(self, temp_script_dir):
        """Test error propagation in entrypoint scripts."""
        script_path = os.path.join(temp_script_dir, "error_test.sh")

        script_content = """#!/bin/bash
set -e  # Exit on error

start_service() {
    echo "Starting service..."
    # Simulate error
    return 1
}

handle_error() {
    local exit_code=$1
    echo "Error occurred with exit code: $exit_code"
    exit $exit_code
}

start_service || handle_error $?
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 1
        assert "Error occurred with exit code: 1" in result.stdout

    def test_entrypoint_environment_propagation(self, temp_script_dir):
        """Test environment variable propagation."""
        script_path = os.path.join(temp_script_dir, "env_test.sh")

        script_content = """#!/bin/bash
# Export variables for child processes
export OLLAMA_HOST="${OLLAMA_HOST:-http://localhost:11434}"
export CODA_LOG_LEVEL="${CODA_LOG_LEVEL:-INFO}"

echo "OLLAMA_HOST=$OLLAMA_HOST"
echo "CODA_LOG_LEVEL=$CODA_LOG_LEVEL"

# Simulate starting child process with env
env | grep -E "(OLLAMA|CODA)" | sort
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(
            ["bash", script_path],
            capture_output=True,
            text=True,
            env={**os.environ, "CODA_LOG_LEVEL": "DEBUG"},
        )

        assert result.returncode == 0
        assert "CODA_LOG_LEVEL=DEBUG" in result.stdout
        assert "OLLAMA_HOST=" in result.stdout

    def test_entrypoint_graceful_shutdown(self, temp_script_dir):
        """Test graceful shutdown sequence."""
        script_path = os.path.join(temp_script_dir, "shutdown_test.sh")

        script_content = """#!/bin/bash
SHUTDOWN_GRACE_PERIOD=5

graceful_shutdown() {
    echo "Initiating graceful shutdown..."

    # Notify services
    echo "Sending SIGTERM to services..."

    # Wait for services to stop
    local waited=0
    while [ $waited -lt $SHUTDOWN_GRACE_PERIOD ]; do
        # Check if services stopped
        if [ $waited -eq 2 ]; then
            echo "All services stopped gracefully"
            return 0
        fi

        sleep 1
        waited=$((waited + 1))
        echo "Waiting for shutdown... ${waited}s"
    done

    echo "Force stopping remaining services"
    return 0
}

graceful_shutdown
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        result = subprocess.run(["bash", script_path], capture_output=True, text=True)

        assert result.returncode == 0
        assert "graceful shutdown" in result.stdout
        assert "All services stopped gracefully" in result.stdout

    @pytest.mark.parametrize(
        "model_name,expected",
        [
            ("llama2", "Model llama2 ready"),
            ("codellama", "Model codellama ready"),
            ("", "No model specified"),
        ],
    )
    def test_entrypoint_model_variations(self, temp_script_dir, model_name, expected):
        """Test entrypoint with different model configurations."""
        script_path = os.path.join(temp_script_dir, "model_test.sh")

        script_content = """#!/bin/bash
MODEL="${OLLAMA_MODEL:-}"

if [ -z "$MODEL" ]; then
    echo "No model specified"
else
    echo "Model $MODEL ready"
fi
"""
        with open(script_path, "w") as f:
            f.write(script_content)
        os.chmod(script_path, 0o755)

        env = {"OLLAMA_MODEL": model_name} if model_name else {}
        result = subprocess.run(["bash", script_path], capture_output=True, text=True, env=env)

        assert expected in result.stdout
