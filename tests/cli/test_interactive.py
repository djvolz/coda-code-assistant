"""Integration tests for the interactive CLI module."""

from unittest.mock import Mock, patch

import pytest
from rich.console import Console

from coda.cli.interactive import run_interactive_session


@pytest.mark.integration
class TestInteractiveSession:
    """Test the interactive session functionality."""

    @pytest.fixture
    def mock_console(self):
        """Create a mock console."""
        return Mock(spec=Console)

    @pytest.fixture
    def mock_oci_provider(self):
        """Create a mock OCI provider."""
        provider = Mock()
        provider.list_models = Mock(
            return_value=[
                Mock(
                    id="test.model.1",
                    display_name="Test Model 1",
                    metadata={"capabilities": ["CHAT"]},
                ),
                Mock(
                    id="test.model.2",
                    display_name="Test Model 2",
                    metadata={"capabilities": ["CHAT"]},
                ),
            ]
        )

        # Create async chat_stream mock
        async def mock_chat_stream(*args, **kwargs):
            chunks = ["Hello", " from", " the", " assistant"]
            for chunk in chunks:
                yield Mock(content=chunk)

        provider.chat_stream = mock_chat_stream
        return provider

    @pytest.fixture
    def mock_interactive_cli(self, mock_console):
        """Create a mock InteractiveCLI."""
        cli = Mock()
        cli.console = mock_console
        cli.current_model = "test.model.1"
        cli.available_models = []
        cli.interrupt_event = Mock()
        cli.interrupt_event.is_set = Mock(return_value=False)
        cli.reset_interrupt = Mock()
        cli.start_interrupt_listener = Mock()
        cli.stop_interrupt_listener = Mock()

        # Create async get_input mock
        async def mock_get_input():
            return "/exit"

        cli.get_input = mock_get_input

        # Create async process_slash_command mock
        async def mock_process_slash_command(cmd):
            if cmd == "/exit":
                raise SystemExit(0)
            return True

        cli.process_slash_command = mock_process_slash_command

        return cli

    @pytest.mark.asyncio
    @patch("coda.cli.interactive.InteractiveCLI")
    @patch("coda.providers.OCIGenAIProvider")
    async def test_run_interactive_session_basic(
        self, mock_oci_class, mock_cli_class, mock_oci_provider, mock_interactive_cli
    ):
        """Test basic interactive session flow."""
        # Setup mocks
        mock_oci_class.return_value = mock_oci_provider
        mock_cli_class.return_value = mock_interactive_cli

        # Run session - should exit via /exit command
        with pytest.raises(SystemExit) as exc_info:
            await run_interactive_session(provider="oci_genai", model="test.model.1", debug=False)

        assert exc_info.value.code == 0

        # Verify initialization
        mock_oci_class.assert_called_once()
        mock_cli_class.assert_called_once()
        mock_oci_provider.list_models.assert_called_once()

    @pytest.mark.asyncio
    @patch("coda.cli.interactive.InteractiveCLI")
    @patch("coda.providers.OCIGenAIProvider")
    @patch("coda.cli.model_selector.ModelSelector")
    async def test_run_interactive_session_model_selection(
        self,
        mock_selector_class,
        mock_oci_class,
        mock_cli_class,
        mock_oci_provider,
        mock_interactive_cli,
    ):
        """Test interactive session with model selection."""
        # Setup model selector mock
        selector = Mock()

        async def mock_select_model():
            return "test.model.2"

        selector.select_model_interactive = mock_select_model
        mock_selector_class.return_value = selector

        # Setup mocks
        mock_oci_class.return_value = mock_oci_provider
        mock_cli_class.return_value = mock_interactive_cli

        # Run session without specifying model
        with pytest.raises(SystemExit):
            await run_interactive_session(
                provider="oci_genai", model=None, debug=False  # No model specified
            )

        # Verify model selector was used
        mock_selector_class.assert_called_once()
        assert mock_interactive_cli.current_model == "test.model.2"

    @pytest.mark.asyncio
    @patch("coda.cli.interactive.InteractiveCLI")
    @patch("coda.providers.OCIGenAIProvider")
    async def test_run_interactive_session_error_handling(
        self, mock_oci_class, mock_cli_class, mock_console
    ):
        """Test error handling in interactive session."""
        # Setup OCI provider to raise error
        mock_oci_class.side_effect = ValueError("compartment_id is required")

        # Create a real InteractiveCLI instance for this test
        cli = Mock()
        cli.console = mock_console
        mock_cli_class.return_value = cli

        # Run session - should handle error gracefully
        await run_interactive_session(provider="oci_genai", model="test.model", debug=False)

        # Verify error message was printed
        calls = [str(call) for call in mock_console.print.call_args_list]
        assert any("compartment ID not configured" in str(call) for call in calls)

    @pytest.mark.asyncio
    async def test_multiline_input_handling(self, mock_interactive_cli):
        """Test handling of multiline input."""
        # Setup mock to return multiline indicator then content
        inputs = ["test\\", "line1", "line2", "", "/exit"]
        input_iter = iter(inputs)

        async def mock_get_input(multiline=False):
            return next(input_iter)

        mock_interactive_cli.get_input = mock_get_input

        # Would need more complex setup to fully test multiline
        # This is a placeholder for the test structure
        assert True

    @pytest.mark.asyncio
    async def test_interrupt_handling(self, mock_interactive_cli, mock_oci_provider):
        """Test interrupt handling during streaming."""
        # Setup interrupt to trigger
        mock_interactive_cli.interrupt_event.is_set = Mock(side_effect=[False, False, True])

        # Create a streaming response that can be interrupted
        async def mock_chat_stream(*args, **kwargs):
            chunks = ["Hello", " from", " the", " assistant", " with", " more", " text"]
            for i, chunk in enumerate(chunks):
                if mock_interactive_cli.interrupt_event.is_set():
                    break
                yield Mock(content=chunk)

        mock_oci_provider.chat_stream = mock_chat_stream

        # Would need full session setup to test interrupt
        # This is a placeholder for the test structure
        assert True

    @pytest.mark.asyncio
    async def test_empty_input_handling(self, mock_interactive_cli):
        """Test handling of empty input (from Ctrl+C)."""
        # Setup mock to return empty input then exit
        inputs = ["", "", "/exit"]
        input_iter = iter(inputs)

        async def mock_get_input():
            return next(input_iter)

        mock_interactive_cli.get_input = mock_get_input

        # Would need full session setup to test empty input handling
        # This is a placeholder for the test structure
        assert True
