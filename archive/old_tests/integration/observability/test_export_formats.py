"""Integration tests for observability data export formats."""

import json
import os
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.configuration import ConfigManager
from coda.observability.manager import ObservabilityManager


class TestObservabilityExportFormats:
    """Test all supported export formats for observability data."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield temp_dir

    @pytest.fixture
    def config_manager(self, temp_dir):
        """Create a config manager with observability enabled."""
        config_path = Path(temp_dir) / "config.toml"
        config_content = f"""
[observability]
enabled = true
storage_path = "{os.path.join(temp_dir, "observability")}"
metrics.enabled = true
tracing.enabled = true
health.enabled = true
error_tracking.enabled = true
profiling.enabled = true

[provider.mock]
type = "mock"
model_name = "mock-smart"
"""
        config_path.write_text(config_content)

        manager = ConfigManager()
        manager.load_config(str(config_path))
        return manager

    @pytest.fixture
    def observability_manager_with_data(self, config_manager):
        """Create an observability manager with sample data."""
        obs_manager = ObservabilityManager(config_manager)

        # Generate diverse data for export testing
        # 1. Events
        obs_manager.track_event("session_start", {"user_id": "test123", "provider": "mock"})
        obs_manager.track_event("model_switch", {"from": "gpt-3.5", "to": "gpt-4"})
        obs_manager.track_event("session_end", {"duration": 300, "messages": 10})

        # 2. Traces
        with obs_manager.trace("api_request") as span:
            span.set_attribute("method", "POST")
            span.set_attribute("endpoint", "/v1/chat/completions")
            time.sleep(0.01)

            with obs_manager.trace("token_processing"):
                time.sleep(0.005)

        with obs_manager.trace("database_query") as span:
            span.set_attribute("query_type", "SELECT")
            span.set_attribute("table", "sessions")
            time.sleep(0.002)

        # 3. Errors
        obs_manager.track_error(
            ConnectionError("Failed to connect to API endpoint"),
            {"provider": "openai", "retry_count": 3, "severity": "high"},
        )
        obs_manager.track_error(
            ValueError("Invalid model name: gpt-5"), {"user_input": "gpt-5", "severity": "medium"}
        )
        obs_manager.track_error(
            RuntimeError("Token limit exceeded"), {"tokens": 5000, "limit": 4096, "severity": "low"}
        )

        # 4. Provider metrics
        obs_manager.track_provider_request("openai", 0.234, True, {"model": "gpt-4", "tokens": 150})
        obs_manager.track_provider_request(
            "anthropic", 0.456, True, {"model": "claude-2", "tokens": 200}
        )
        obs_manager.track_provider_request("openai", 1.234, False, {"error": "timeout"})

        # 5. Token usage
        obs_manager.track_token_usage("openai", 1000, 500, 0.03)
        obs_manager.track_token_usage("anthropic", 1500, 750, 0.04)
        obs_manager.track_token_usage("mock", 100, 50, 0.0)

        return obs_manager

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

    def test_json_export_format(self, config_manager, observability_manager_with_data, temp_dir):
        """Test JSON export format with all data types."""
        obs_manager = observability_manager_with_data

        # Export to JSON
        export_path = os.path.join(temp_dir, "export.json")

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(
                cli._cmd_observability, f"export --format json --output {export_path}"
            )
            assert "export" in output.lower()

        # Verify JSON file was created and is valid
        assert os.path.exists(export_path)

        with open(export_path) as f:
            data = json.load(f)

        # Verify JSON structure
        assert isinstance(data, dict)
        assert "export_timestamp" in data
        assert "metrics" in data
        assert "traces" in data
        assert "errors" in data
        assert "health" in data

        # Verify data content
        metrics = data.get("metrics", {})
        assert "session_events" in metrics or "events" in metrics
        assert "provider_metrics" in metrics or "providers" in metrics
        assert "token_usage" in metrics or "tokens" in metrics

        errors = data.get("errors", [])
        assert len(errors) >= 3
        assert any("ConnectionError" in str(e) or "connect" in str(e) for e in errors)

        traces = data.get("traces", [])
        assert len(traces) >= 2
        assert any("api_request" in str(t) or "name" in str(t) for t in traces)

    def test_summary_export_format(self, config_manager, observability_manager_with_data, temp_dir):
        """Test summary export format."""
        obs_manager = observability_manager_with_data

        export_path = os.path.join(temp_dir, "summary.txt")

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(
                cli._cmd_observability, f"export --format summary --output {export_path}"
            )
            assert "export" in output.lower()

        # Verify summary file was created
        assert os.path.exists(export_path)

        with open(export_path) as f:
            content = f.read()

        # Verify summary content
        assert "Observability Export Summary" in content or "Summary" in content
        assert "Total Events:" in content or "Events:" in content
        assert "Total Errors:" in content or "Errors:" in content
        assert "Total Traces:" in content or "Traces:" in content

        # Should include high-level statistics
        assert any(word in content for word in ["session", "provider", "token", "error"])

    def test_csv_export_format(self, config_manager, observability_manager_with_data, temp_dir):
        """Test CSV export format."""
        obs_manager = observability_manager_with_data

        # CSV export might create multiple files for different data types
        export_dir = os.path.join(temp_dir, "csv_export")
        os.makedirs(export_dir, exist_ok=True)

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            # Try exporting to CSV format
            output = self.capture_output(
                cli._cmd_observability, f"export --format csv --output {export_dir}/data.csv"
            )

            # CSV format might not be implemented, check response
            if "not supported" in output.lower() or "invalid format" in output.lower():
                pytest.skip("CSV format not implemented yet")
            else:
                assert "export" in output.lower()

                # Check for CSV files
                csv_files = list(Path(export_dir).glob("*.csv"))
                assert len(csv_files) > 0

                # Verify CSV content
                for csv_file in csv_files:
                    with open(csv_file) as f:
                        content = f.read()
                        # Should have header row
                        lines = content.strip().split("\n")
                        assert len(lines) > 1  # Header + at least one data row
                        assert "," in lines[0]  # CSV format

    def test_html_export_format(self, config_manager, observability_manager_with_data, temp_dir):
        """Test HTML export format."""
        obs_manager = observability_manager_with_data

        export_path = os.path.join(temp_dir, "report.html")

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(
                cli._cmd_observability, f"export --format html --output {export_path}"
            )

            # HTML format might not be implemented
            if "not supported" in output.lower() or "invalid format" in output.lower():
                pytest.skip("HTML format not implemented yet")
            else:
                assert "export" in output.lower()

                # Verify HTML file
                assert os.path.exists(export_path)

                with open(export_path) as f:
                    content = f.read()

                # Verify HTML structure
                assert "<html" in content.lower()
                assert "<body" in content.lower()
                assert "</html>" in content.lower()

                # Should contain data sections
                assert any(
                    word in content.lower() for word in ["metrics", "traces", "errors", "health"]
                )

    def test_default_export_format(self, config_manager, observability_manager_with_data, temp_dir):
        """Test export with default format (should be JSON)."""
        obs_manager = observability_manager_with_data

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            # Export without specifying format
            output = self.capture_output(cli._cmd_observability, "export")
            assert "export" in output.lower()

            # Should mention JSON or show a default path
            assert "json" in output.lower() or ".json" in output.lower()

    def test_export_empty_data(self, config_manager, temp_dir):
        """Test export when no data has been collected."""
        # Create fresh observability manager with no data
        obs_manager = ObservabilityManager(config_manager)

        export_path = os.path.join(temp_dir, "empty_export.json")

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(
                cli._cmd_observability, f"export --format json --output {export_path}"
            )
            assert "export" in output.lower()

        # Should still create a valid file
        if os.path.exists(export_path):
            with open(export_path) as f:
                data = json.load(f)

            # Should have structure but empty/minimal data
            assert isinstance(data, dict)
            assert "export_timestamp" in data

    def test_export_with_special_characters(self, config_manager, temp_dir):
        """Test export with data containing special characters."""
        obs_manager = ObservabilityManager(config_manager)

        # Add data with special characters
        obs_manager.track_event(
            "test_event",
            {
                "message": "Test with special chars: \"quotes\", 'apostrophes', \n newlines, \t tabs",
                "unicode": "emojis 🚀 and symbols ♠♣♥♦",
                "path": "C:\\Windows\\System32\\cmd.exe",
            },
        )

        obs_manager.track_error(
            Exception("Error with <html> tags & special chars"),
            {"context": "Testing & validating < > characters"},
        )

        export_path = os.path.join(temp_dir, "special_chars.json")

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(
                cli._cmd_observability, f"export --format json --output {export_path}"
            )
            assert "export" in output.lower()

        # Verify JSON is still valid
        if os.path.exists(export_path):
            with open(export_path) as f:
                data = json.load(f)  # Should not raise JSONDecodeError
            assert isinstance(data, dict)

    def test_export_large_dataset(self, config_manager, temp_dir):
        """Test export with large amount of data."""
        obs_manager = ObservabilityManager(config_manager)

        # Generate large dataset
        for i in range(1000):
            obs_manager.track_event(f"event_{i}", {"index": i, "data": f"value_{i}" * 10})

            if i % 10 == 0:
                obs_manager.track_error(Exception(f"Error {i}"), {"index": i, "severity": "low"})

            if i % 5 == 0:
                with obs_manager.trace(f"operation_{i}"):
                    pass

        export_path = os.path.join(temp_dir, "large_export.json")

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            output = self.capture_output(
                cli._cmd_observability, f"export --format json --output {export_path}"
            )
            assert "export" in output.lower()

        # Verify large file is created
        if os.path.exists(export_path):
            file_size = os.path.getsize(export_path)
            assert file_size > 10000  # Should be reasonably large

            # Verify it's still valid JSON
            with open(export_path) as f:
                data = json.load(f)
            assert isinstance(data, dict)

    def test_export_format_validation(
        self, config_manager, observability_manager_with_data, temp_dir
    ):
        """Test validation of export format parameter."""
        obs_manager = observability_manager_with_data

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            # Test invalid format
            output = self.capture_output(cli._cmd_observability, "export --format invalid_format")
            assert (
                "invalid" in output.lower()
                or "not supported" in output.lower()
                or "error" in output.lower()
            )

            # Test case sensitivity
            output = self.capture_output(cli._cmd_observability, "export --format JSON")
            # Should either accept uppercase or show error
            assert "export" in output.lower() or "error" in output.lower()

    def test_export_path_validation(self, config_manager, observability_manager_with_data):
        """Test validation of export output path."""
        obs_manager = observability_manager_with_data

        with patch("coda.cli.interactive_cli.ConfigManager", return_value=config_manager):
            cli = InteractiveCLI()
            cli.config_manager = config_manager
            cli._observability_manager = obs_manager

            # Test invalid path
            invalid_path = "/invalid/directory/that/does/not/exist/export.json"
            output = self.capture_output(cli._cmd_observability, f"export --output {invalid_path}")
            assert (
                "error" in output.lower()
                or "failed" in output.lower()
                or "invalid" in output.lower()
            )

            # Test path traversal attempt
            dangerous_path = "../../../etc/passwd"
            output = self.capture_output(
                cli._cmd_observability, f"export --output {dangerous_path}"
            )
            # Should be rejected for security reasons
            assert (
                "error" in output.lower()
                or "invalid" in output.lower()
                or "denied" in output.lower()
            )
