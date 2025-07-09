"""Unit tests for the web command module."""

import subprocess
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from coda.cli.web_command import web


class TestWebCommand:
    """Test suite for web command functionality."""

    @pytest.fixture
    def runner(self):
        """Create a Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch("coda.cli.web_command.get_config") as mock:
            config = Mock()
            config.debug = False
            mock.return_value = config
            yield mock

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess.run."""
        with patch("coda.cli.web_command.subprocess.run") as mock:
            yield mock

    @pytest.fixture
    def mock_console(self):
        """Mock console output."""
        with patch("coda.cli.web_command.console") as mock:
            yield mock

    def test_web_command_default_options(self, runner, mock_config, mock_subprocess, mock_console):
        """Test web command with default options."""
        result = runner.invoke(web)

        assert result.exit_code == 0
        mock_config.assert_called_once()

        # Verify subprocess was called with correct default arguments
        mock_subprocess.assert_called_once()
        call_args = mock_subprocess.call_args[0][0]

        assert sys.executable in call_args
        assert "-m" in call_args
        assert "streamlit" in call_args
        assert "run" in call_args
        assert "--server.port" in call_args
        assert "8501" in call_args
        assert "--server.address" in call_args
        assert "localhost" in call_args
        assert "--server.headless" not in call_args  # Browser enabled by default

    def test_web_command_custom_port_and_host(
        self, runner, mock_config, mock_subprocess, mock_console
    ):
        """Test web command with custom port and host."""
        result = runner.invoke(web, ["--port", "8080", "--host", "0.0.0.0"])

        assert result.exit_code == 0

        call_args = mock_subprocess.call_args[0][0]
        assert "8080" in call_args
        assert "0.0.0.0" in call_args

    def test_web_command_no_browser(self, runner, mock_config, mock_subprocess, mock_console):
        """Test web command with browser disabled."""
        result = runner.invoke(web, ["--no-browser"])

        assert result.exit_code == 0

        call_args = mock_subprocess.call_args[0][0]
        assert "--server.headless" in call_args
        assert "true" in call_args

    def test_web_command_debug_mode(self, runner, mock_config, mock_subprocess, mock_console):
        """Test web command in debug mode."""
        result = runner.invoke(web, ["--debug"])

        assert result.exit_code == 0

        call_args = mock_subprocess.call_args[0][0]
        assert "--logger.level" in call_args
        assert "debug" in call_args

    def test_web_command_keyboard_interrupt(
        self, runner, mock_config, mock_subprocess, mock_console
    ):
        """Test web command handling keyboard interrupt."""
        mock_subprocess.side_effect = KeyboardInterrupt()

        result = runner.invoke(web)

        # Should exit cleanly with code 0
        assert result.exit_code == 0

        # Should print stop message
        mock_console.print.assert_any_call("\n[yellow]Web UI stopped by user[/yellow]")

    def test_web_command_subprocess_error(self, runner, mock_config, mock_subprocess, mock_console):
        """Test web command handling subprocess errors."""
        mock_subprocess.side_effect = subprocess.CalledProcessError(1, "streamlit")

        result = runner.invoke(web)

        assert result.exit_code == 1

        # Should print error message
        assert any(
            "Error running web UI" in str(call) for call in mock_console.print.call_args_list
        )

    def test_web_command_config_error(self, runner, mock_subprocess, mock_console):
        """Test web command handling configuration errors."""
        with patch("coda.cli.web_command.get_config") as mock_config:
            mock_config.side_effect = Exception("Config error")

            result = runner.invoke(web)

            assert result.exit_code == 1

            # Should print config error message
            mock_console.print.assert_called_with(
                "[red]Error loading configuration: Config error[/red]"
            )

            # Subprocess should not be called
            mock_subprocess.assert_not_called()

    def test_web_command_app_path_resolution(
        self, runner, mock_config, mock_subprocess, mock_console
    ):
        """Test that app path is correctly resolved."""
        result = runner.invoke(web)

        assert result.exit_code == 0

        call_args = mock_subprocess.call_args[0][0]

        # Find the app.py path in the arguments
        app_path_idx = None
        for i, arg in enumerate(call_args):
            if arg == "run":
                app_path_idx = i + 1
                break

        assert app_path_idx is not None
        app_path = Path(call_args[app_path_idx])

        # Verify it points to the correct file
        assert app_path.name == "app.py"
        assert "web" in app_path.parts

    def test_web_command_all_options_combined(
        self, runner, mock_config, mock_subprocess, mock_console
    ):
        """Test web command with all options combined."""
        result = runner.invoke(
            web, ["--port", "9000", "--host", "127.0.0.1", "--no-browser", "--debug"]
        )

        assert result.exit_code == 0

        call_args = mock_subprocess.call_args[0][0]

        # Verify all options are present
        assert "9000" in call_args
        assert "127.0.0.1" in call_args
        assert "--server.headless" in call_args
        assert "--logger.level" in call_args
        assert "debug" in call_args

    def test_web_command_panel_output(self, runner, mock_config, mock_subprocess, mock_console):
        """Test that welcome panel is displayed correctly."""
        result = runner.invoke(web, ["--port", "8888", "--host", "example.com"])

        assert result.exit_code == 0

        # Verify panel was printed with correct information
        print_calls = mock_console.print.call_args_list
        assert len(print_calls) > 0

        # Check that the panel contains the correct URL
        panel_call = print_calls[0][0][0]
        assert hasattr(panel_call, "renderable")  # It's a Panel
        assert "http://example.com:8888" in str(panel_call.renderable)
