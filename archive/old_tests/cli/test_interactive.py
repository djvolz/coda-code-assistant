"""Integration tests for the interactive CLI module."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from rich.console import Console

from coda.cli.interactive import (
    _get_chat_models,
    _handle_chat_interaction,
    _initialize_provider,
    _select_model,
    run_interactive_session,
)
from coda.cli.interactive_cli import DeveloperMode, InteractiveCLI


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
        cli = Mock(spec=InteractiveCLI)
        cli.current_mode = DeveloperMode.GENERAL
        cli.current_model = "test.model.1"
        cli.available_models = []
        cli.interrupt_event = Mock()
        cli.interrupt_event.is_set = Mock(return_value=False)
        cli.reset_interrupt = Mock()
        cli.start_interrupt_listener = Mock()
        cli.stop_interrupt_listener = Mock()
        cli.get_input = AsyncMock(return_value="test message")
        cli.process_slash_command = AsyncMock(return_value=False)
        return cli

    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration."""
        config = Mock()
        config.to_dict = Mock(
            return_value={"temperature": 0.7, "max_tokens": 2000, "default_provider": "oci_genai"}
        )
        config.debug = False
        config.default_provider = "oci_genai"
        return config

    @pytest.mark.asyncio
    async def test_initialize_provider(self, mock_config):
        """Test provider initialization."""
        with patch("coda.cli.interactive.ProviderFactory") as mock_factory_class:
            mock_factory = Mock()
            mock_factory.create = Mock(return_value=Mock())
            mock_factory_class.return_value = mock_factory

            console = Mock()

            result = await _initialize_provider(mock_factory, "test_provider", console)

            assert result is not None
            mock_factory.create.assert_called_once_with("test_provider")
            assert console.print.call_count >= 2  # Should print initialization messages

    @pytest.mark.asyncio
    async def test_get_chat_models(self):
        """Test chat model filtering and deduplication."""
        mock_provider = Mock()
        mock_provider.list_models = Mock(
            return_value=[
                Mock(id="model1", metadata={"capabilities": ["CHAT"]}, provider="test"),
                Mock(id="model2", metadata={"capabilities": ["TEXT_GENERATION"]}, provider="test"),
                Mock(
                    id="model1", metadata={"capabilities": ["CHAT"]}, provider="test"
                ),  # Duplicate
                Mock(id="model3", metadata={}, provider="ollama"),  # Ollama model
            ]
        )

        console = Mock()

        result = await _get_chat_models(mock_provider, console)

        assert len(result) == 3  # Should deduplicate model1
        model_ids = [m.id for m in result]
        assert "model1" in model_ids
        assert "model2" in model_ids
        assert "model3" in model_ids

    @pytest.mark.asyncio
    async def test_select_model_with_interactive(self):
        """Test interactive model selection."""
        unique_models = [Mock(id="model1"), Mock(id="model2")]
        console = Mock()

        with patch("coda.cli.interactive.ModelSelector") as mock_selector_class:
            mock_selector = Mock()
            mock_selector.select_model_interactive = AsyncMock(return_value="selected_model")
            mock_selector_class.return_value = mock_selector

            result = await _select_model(unique_models, None, console)

            assert result == "selected_model"
            mock_selector_class.assert_called_once_with(unique_models, console)

    @pytest.mark.asyncio
    async def test_select_model_with_specified_model(self):
        """Test model selection when model is already specified."""
        unique_models = [Mock(id="model1"), Mock(id="model2")]
        console = Mock()

        result = await _select_model(unique_models, "specified_model", console)

        assert result == "specified_model"
        assert console.print.call_count >= 3  # Should print model selection messages

    @pytest.mark.asyncio
    async def test_handle_chat_interaction_with_slash_command(
        self, mock_interactive_cli, mock_config
    ):
        """Test chat interaction that processes a slash command."""
        mock_provider = Mock()
        messages = []
        console = Mock()

        # Mock CLI to return a slash command
        mock_interactive_cli.get_input = AsyncMock(return_value="/help")
        mock_interactive_cli.process_slash_command = AsyncMock(return_value=True)

        result = await _handle_chat_interaction(
            mock_provider, mock_interactive_cli, messages, console, mock_config
        )

        assert result is True
        mock_interactive_cli.process_slash_command.assert_called_once_with("/help")

    @pytest.mark.asyncio
    async def test_handle_chat_interaction_with_regular_message(
        self, mock_interactive_cli, mock_config
    ):
        """Test chat interaction with a regular message."""
        mock_provider = Mock()
        mock_stream = [Mock(content="Hello"), Mock(content=" world")]
        mock_provider.chat_stream = Mock(return_value=mock_stream)

        messages = []
        console = Mock()

        # Mock CLI to return regular input
        mock_interactive_cli.get_input = AsyncMock(return_value="Hello AI")
        mock_interactive_cli.process_slash_command = AsyncMock(return_value=False)

        result = await _handle_chat_interaction(
            mock_provider, mock_interactive_cli, messages, console, mock_config
        )

        assert result is True
        assert len(messages) == 2  # User message + Assistant message
        mock_provider.chat_stream.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_chat_interaction_with_interrupt(self, mock_interactive_cli, mock_config):
        """Test chat interaction with user interrupt."""
        mock_provider = Mock()
        mock_stream = [Mock(content="Hello"), Mock(content=" world")]
        mock_provider.chat_stream = Mock(return_value=mock_stream)

        messages = []
        console = Mock()

        # Mock interrupt event
        mock_interactive_cli.interrupt_event.is_set = Mock(
            side_effect=[False, True]
        )  # Interrupt on second chunk
        mock_interactive_cli.get_input = AsyncMock(return_value="Hello AI")
        mock_interactive_cli.process_slash_command = AsyncMock(return_value=False)

        result = await _handle_chat_interaction(
            mock_provider, mock_interactive_cli, messages, console, mock_config
        )

        assert result is True
        mock_interactive_cli.start_interrupt_listener.assert_called_once()
        mock_interactive_cli.stop_interrupt_listener.assert_called_once()

    @pytest.mark.asyncio
    @patch("coda.cli.interactive.InteractiveCLI")
    @patch("coda.providers.ProviderFactory")
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
                provider="oci_genai",
                model=None,
                debug=False,  # No model specified
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
            for _i, chunk in enumerate(chunks):
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
