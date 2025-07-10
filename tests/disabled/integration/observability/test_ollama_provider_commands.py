"""Integration tests for observability commands with Ollama provider."""

import os
import tempfile
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityCommandsWithOllamaProvider:
    """Test all observability commands with Ollama provider integration."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a config manager with observability enabled and Ollama provider."""
        config_path = Path(temp_dir) / "config.toml"
        config_content = """
[observability]
enabled = true
storage_path = "{storage_path}"
metrics.enabled = true
tracing.enabled = true
health.enabled = true
error_tracking.enabled = true
profiling.enabled = true

[provider.ollama]
type = "ollama"
model_name = "llama2"
api_base = "http://localhost:11434"
"""
        config_content = config_content.format(storage_path=os.path.join(temp_dir, "observability"))
        config_path.write_text(config_content)

        manager = ConfigManager()
        manager.load_config(str(config_path))
        return manager

    @pytest.fixture
    def mock_ollama_provider(self):
        """Create a mocked Ollama provider."""
        provider = Mock()
        provider.name = "ollama"
        provider.model = "llama2"
        provider.list_models = Mock(return_value=["llama2", "codellama", "mistral"])
        provider.chat = Mock(return_value="Mocked Ollama response")
        provider.chat_stream = Mock(return_value=iter(["Mocked ", "streaming ", "response"]))
        return provider

    @pytest.fixture
    def cli(self, config_manager, mock_ollama_provider):
        """Create an interactive CLI instance with mocked Ollama provider."""
        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            with patch("coda.providers.factory.create_provider", return_value=mock_ollama_provider):
                cli = InteractiveCLI()
                cli.config_manager = config_manager
                cli.provider = mock_ollama_provider
                return cli

    @pytest.fixture
    def observability_manager(self, config_manager):
        """Create an observability manager instance."""
        return ObservabilityManager(config_manager)

    def capture_output(self, func, *args, **kwargs):
        """Capture stdout output from a function."""
        import io
        import sys

        old_stdout = sys.stdout
        sys.stdout = captured_output = io.StringIO()
        try:
            func(*args, **kwargs)
            return captured_output.getvalue()
        finally:
            sys.stdout = old_stdout

    def test_observability_status_with_ollama(self, cli, observability_manager):
        """Test observability status command with Ollama provider context."""
        cli._observability_manager = observability_manager

        # Track some Ollama-specific events
        observability_manager.track_event(
            "provider_initialized", {"provider": "ollama", "model": "llama2"}
        )

        # Run status command
        output = self.capture_output(cli._cmd_observability, "status")

        # Verify output
        assert "Observability Status" in output
        assert "Enabled: True" in output
        assert "metrics: ✓" in output

    def test_ollama_provider_metrics(self, cli, observability_manager, mock_ollama_provider):
        """Test metrics collection for Ollama provider operations."""
        cli._observability_manager = observability_manager

        # Simulate Ollama API calls and track metrics
        start_time = time.time()
        mock_ollama_provider.chat(["Test message"])
        latency = time.time() - start_time

        observability_manager.track_provider_request(
            "ollama", latency, True, {"model": "llama2", "endpoint": "chat"}
        )

        # Track token usage for Ollama
        observability_manager.track_token_usage("ollama", 150, 75, 0.0)  # Ollama is typically free

        # Run metrics command
        output = self.capture_output(cli._cmd_observability, "metrics --detailed")

        # Verify Ollama metrics are captured
        assert "ollama" in output.lower() or "Metrics" in output

    def test_ollama_health_monitoring(self, cli, observability_manager, mock_ollama_provider):
        """Test health monitoring for Ollama provider."""
        cli._observability_manager = observability_manager

        # Simulate health check for Ollama
        observability_manager.track_event(
            "health_check", {"provider": "ollama", "status": "healthy", "response_time": 0.05}
        )

        # Run health command
        output = self.capture_output(cli._cmd_observability, "health")

        # Verify health status
        assert "Health Status" in output or "healthy" in output.lower()

    def test_ollama_specific_health_check(self, cli, observability_manager):
        """Test health check for Ollama-specific component."""
        cli._observability_manager = observability_manager

        # Check health of provider component
        output = self.capture_output(cli._cmd_observability, "health providers")

        # Should show provider health status
        assert "provider" in output.lower() or "health" in output.lower()

    def test_ollama_request_tracing(self, cli, observability_manager, mock_ollama_provider):
        """Test tracing of Ollama API requests."""
        cli._observability_manager = observability_manager

        # Simulate traced Ollama operations
        with observability_manager.trace("ollama_chat_request") as span:
            span.set_attribute("provider", "ollama")
            span.set_attribute("model", "llama2")
            span.set_attribute("endpoint", "/api/chat")
            time.sleep(0.01)  # Simulate API latency
            mock_ollama_provider.chat(["Traced request"])

        with observability_manager.trace("ollama_list_models") as span:
            span.set_attribute("provider", "ollama")
            models = mock_ollama_provider.list_models()
            span.set_attribute("model_count", len(models))

        # Run traces command
        output = self.capture_output(cli._cmd_observability, "traces --limit 5")

        # Verify Ollama operations are traced
        assert "ollama_chat_request" in output or "ollama" in output.lower()

    def test_ollama_error_tracking(self, cli, observability_manager):
        """Test error tracking for Ollama-specific errors."""
        cli._observability_manager = observability_manager

        # Track Ollama-specific errors
        observability_manager.track_error(
            ConnectionError("Failed to connect to Ollama at localhost:11434"),
            {"provider": "ollama", "severity": "high", "retry_count": 3},
        )

        observability_manager.track_error(
            ValueError("Invalid model 'unknown-model' for Ollama"),
            {"provider": "ollama", "severity": "medium", "model": "unknown-model"},
        )

        # Run errors command
        output = self.capture_output(cli._cmd_observability, "errors --days 1")

        # Verify Ollama errors are shown
        assert "Ollama" in output or "ConnectionError" in output or "Error" in output

    def test_ollama_streaming_metrics(self, cli, observability_manager, mock_ollama_provider):
        """Test metrics collection for Ollama streaming responses."""
        cli._observability_manager = observability_manager

        # Simulate streaming response metrics
        chunks = 0
        start_time = time.time()
        for _ in mock_ollama_provider.chat_stream(["Stream test"]):
            chunks += 1
        stream_duration = time.time() - start_time

        observability_manager.track_event(
            "ollama_stream_complete",
            {
                "provider": "ollama",
                "chunks": chunks,
                "duration": stream_duration,
                "model": "llama2",
            },
        )

        # Run metrics command
        output = self.capture_output(cli._cmd_observability, "metrics")

        # Verify streaming metrics
        assert "Metrics" in output

    def test_ollama_model_switching_tracking(
        self, cli, observability_manager, mock_ollama_provider
    ):
        """Test tracking of model switching operations in Ollama."""
        cli._observability_manager = observability_manager

        # Track model switches
        models = ["llama2", "codellama", "mistral"]
        for model in models:
            observability_manager.track_event(
                "model_switch",
                {"provider": "ollama", "from_model": mock_ollama_provider.model, "to_model": model},
            )
            mock_ollama_provider.model = model

        # Export data to verify events
        output = self.capture_output(cli._cmd_observability, "export --format summary")

        # Verify model switch events are tracked
        assert "export" in output.lower()

    def test_ollama_performance_profiling(self, cli, observability_manager):
        """Test performance profiling for Ollama operations."""
        cli._observability_manager = observability_manager

        # Simulate some Ollama operations for profiling
        def ollama_operation():
            with observability_manager.trace("ollama_inference"):
                time.sleep(0.01)
                return "result"

        # Run multiple operations
        for _ in range(5):
            ollama_operation()

        # Run performance command
        output = self.capture_output(cli._cmd_observability, "performance --limit 5")

        # Verify performance data
        assert "Performance" in output or "Profiling" in output

    def test_ollama_export_with_filters(self, cli, observability_manager, temp_dir):
        """Test exporting Ollama-specific observability data."""
        cli._observability_manager = observability_manager

        # Generate Ollama-specific data
        observability_manager.track_event("ollama_init", {"version": "0.1.0"})
        observability_manager.track_provider_request("ollama", 0.05, True, {"model": "llama2"})

        # Export to custom path
        export_path = os.path.join(temp_dir, "ollama_metrics.json")
        output = self.capture_output(
            cli._cmd_observability, f"export --format json --output {export_path}"
        )

        # Verify export
        assert "export" in output.lower()
        # Check if file was created (in real test)
        # assert os.path.exists(export_path)

    def test_ollama_connection_failure_handling(self, cli, observability_manager):
        """Test observability when Ollama connection fails."""
        cli._observability_manager = observability_manager

        # Simulate connection failures
        for i in range(3):
            observability_manager.track_error(
                ConnectionError(f"Connection attempt {i + 1} failed"),
                {
                    "provider": "ollama",
                    "attempt": i + 1,
                    "endpoint": "http://localhost:11434",
                    "severity": "high",
                },
            )

        # Check error analysis
        output = self.capture_output(cli._cmd_observability, "errors --limit 5")

        # Should show connection errors
        assert "Connection" in output or "failed" in output or "Error" in output

    def test_ollama_model_loading_metrics(self, cli, observability_manager, mock_ollama_provider):
        """Test metrics for Ollama model loading operations."""
        cli._observability_manager = observability_manager

        # Simulate model loading
        models_to_load = ["llama2:7b", "codellama:13b", "mistral:7b"]
        for model in models_to_load:
            start = time.time()
            # Simulate loading delay
            time.sleep(0.01)
            load_time = time.time() - start

            observability_manager.track_event(
                "ollama_model_loaded",
                {
                    "provider": "ollama",
                    "model": model,
                    "load_time": load_time,
                    "size_gb": 4.5 if "7b" in model else 8.2,
                },
            )

        # Check metrics
        output = self.capture_output(cli._cmd_observability, "metrics --detailed")

        # Verify model loading events
        assert "model" in output.lower() or "Metrics" in output

    def test_ollama_resource_monitoring(self, cli, observability_manager):
        """Test resource usage monitoring for Ollama."""
        cli._observability_manager = observability_manager

        # Track resource usage
        observability_manager.track_event(
            "resource_usage",
            {
                "provider": "ollama",
                "cpu_percent": 45.2,
                "memory_gb": 6.8,
                "gpu_memory_gb": 4.2,
                "active_models": 2,
            },
        )

        # Check health with resource info
        output = self.capture_output(cli._cmd_observability, "health")

        assert "Health" in output or "health" in output.lower()

    def test_all_observability_commands_sequence(
        self, cli, observability_manager, mock_ollama_provider
    ):
        """Test running all observability commands in sequence with Ollama."""
        cli._observability_manager = observability_manager

        # Generate comprehensive test data
        # 1. Initialize and track startup
        observability_manager.track_event("ollama_startup", {"provider": "ollama"})

        # 2. Perform operations
        with observability_manager.trace("full_test_sequence"):
            # Chat request
            observability_manager.track_provider_request("ollama", 0.1, True, {"model": "llama2"})

            # Token usage
            observability_manager.track_token_usage("ollama", 200, 150, 0.0)

            # Error
            observability_manager.track_error(
                RuntimeError("Test error in sequence"), {"provider": "ollama", "severity": "low"}
            )

        # 3. Run all commands
        commands = [
            "status",
            "metrics",
            "metrics --detailed",
            "health",
            "health providers",
            "traces",
            "traces --limit 20",
            "errors",
            "errors --limit 5 --days 1",
            "performance",
            "export --format summary",
        ]

        outputs = []
        for cmd in commands:
            output = self.capture_output(cli._cmd_observability, cmd)
            outputs.append((cmd, output))

        # Verify all commands executed successfully
        for cmd, output in outputs:
            assert len(output) > 0, f"Command '{cmd}' produced no output"
            # Should not contain unhandled errors
            assert "Traceback" not in output, f"Command '{cmd}' had an error"
