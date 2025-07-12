"""Integration tests for theme application in conversations."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from rich.console import Console

from coda.cli.chat_session import ChatSession
from coda.cli.interactive import _handle_chat_interaction
from coda.cli.shared import DeveloperMode
from coda.configuration import CodaConfig
from coda.providers import MockProvider, Model
from coda.themes import ConsoleTheme, Theme


@pytest.mark.integration
class TestThemeIntegration:
    """Test that themes are properly applied throughout the conversation."""

    @pytest.fixture
    def mock_config(self):
        """Create a mock config."""
        config = Mock(spec=CodaConfig)
        config.to_dict.return_value = {"temperature": 0.7, "max_tokens": 2000}
        config.ui = {"theme": "default"}
        return config

    @pytest.fixture
    def custom_theme(self):
        """Create a custom theme for testing."""
        return Theme(
            name="test-theme",
            description="Test theme",
            console=ConsoleTheme(
                success="green",
                error="red",
                warning="yellow",
                info="magenta",  # Distinctive color for testing
                user_message="blue",  # Distinctive color for testing
                assistant_message="yellow",  # Distinctive color for testing
                code_theme="monokai",
            ),
            prompt=Mock(),  # We're not testing prompt themes here
        )

    def test_one_shot_uses_theme_colors(self, mock_config, custom_theme):
        """Test that one-shot mode uses theme colors for messages."""
        # Mock console to capture output
        console = Mock(spec=Console)
        console.print = Mock()

        # Mock provider
        provider = MockProvider()
        models = [Model(id="mock-echo", name="Mock Echo", provider="mock", metadata={})]

        # Create chat session
        session = ChatSession(
            provider=provider,
            model="mock-echo",
            config=mock_config,
            console=console,
            provider_name="mock",
            factory=Mock(),
            unique_models=models,
        )

        # Mock the theme system to return our custom theme
        with patch("coda.themes.get_console_theme", return_value=custom_theme.console):
            # Run one-shot
            session.run_one_shot("Hello world")

        # Verify user message uses theme color
        user_call = console.print.call_args_list[0]
        assert "[blue]User:[/blue]" in str(user_call)

        # Verify assistant message uses theme color
        assistant_call = console.print.call_args_list[1]
        assert "[yellow]Assistant:[/yellow]" in str(assistant_call)

    def test_interactive_mode_uses_theme_colors(self, mock_config, custom_theme):
        """Test that interactive mode uses theme colors for messages."""
        # Mock console to capture output
        console = Mock(spec=Console)
        console.print = Mock()

        # Mock provider that returns streaming chunks properly
        from unittest.mock import Mock as MockChunk

        chunk = MockChunk()
        chunk.content = "Test response"
        provider = Mock()
        provider.chat_stream = Mock(return_value=iter([chunk]))

        models = [Model(id="mock-echo", name="Mock Echo", provider="mock", metadata={})]

        # Create chat session
        session = ChatSession(
            provider=provider,
            model="mock-echo",
            config=mock_config,
            console=console,
            provider_name="mock",
            factory=Mock(),
            unique_models=models,
        )

        # Mock the theme system to return our custom theme
        with patch("coda.themes.get_console_theme", return_value=custom_theme.console):
            # Mock Prompt.ask to return test message then /exit
            with patch("coda.cli.chat_session.Prompt.ask", side_effect=["Test message", "/exit"]):
                session.run_interactive()

        # Find the assistant message print call
        assistant_calls = [
            call for call in console.print.call_args_list if "Assistant:" in str(call)
        ]

        # Verify assistant message uses theme color
        assert any("[yellow]Assistant:[/yellow]" in str(call) for call in assistant_calls)

    @pytest.mark.asyncio
    async def test_thinking_message_uses_theme_colors(self, mock_config, custom_theme):
        """Test that thinking/status messages use theme colors."""
        # Mock console to capture output
        console = Mock(spec=Console)
        console.status = Mock()

        # Create a mock status context manager
        mock_status = Mock()
        mock_status.__enter__ = Mock(return_value=mock_status)
        mock_status.__exit__ = Mock(return_value=None)
        mock_status.stop = Mock()
        console.status.return_value = mock_status

        # Mock CLI with interrupt event and mode
        cli = Mock()
        cli.interrupt_event = Mock()
        cli.interrupt_event.is_set.return_value = False
        cli.current_mode = DeveloperMode.GENERAL
        cli.current_model = "test-model"
        cli.reset_interrupt = Mock()
        cli.start_interrupt_listener = Mock()
        cli.stop_interrupt_listener = Mock()
        cli.get_input = AsyncMock(return_value="Test message")
        cli.process_slash_command = AsyncMock(return_value=False)
        cli.session_commands = Mock()
        cli.session_commands.add_message = Mock()

        # Mock provider with streaming response - use proper chunk objects
        from unittest.mock import Mock as MockChunk

        chunk = MockChunk()
        chunk.content = "Test response"
        provider = Mock()
        provider.chat_stream = Mock(return_value=iter([chunk]))

        # Create messages list
        messages = []

        # Mock the theme system to return our custom theme
        with patch("coda.themes.get_console_theme", return_value=custom_theme.console):
            # Call the chat interaction handler
            await _handle_chat_interaction(provider, cli, messages, console, mock_config)

        # Verify status was called with theme color
        console.status.assert_called_once()
        status_call = console.status.call_args[0][0]
        # Should use magenta (our test theme's info color) for thinking message
        assert "[magenta]" in status_call
        assert "Thinking..." in status_call

    def test_session_deletion_uses_theme_colors(self, custom_theme):
        """Test that session deletion status uses theme colors."""
        from coda.session.commands import SessionCommands

        # Mock console to capture output
        console = Mock(spec=Console)
        console.status = Mock()
        console.print = Mock()

        # Create a mock status context manager
        mock_status = Mock()
        mock_status.__enter__ = Mock(return_value=mock_status)
        mock_status.__exit__ = Mock(return_value=None)
        console.status.return_value = mock_status

        # Create session commands
        session_commands = SessionCommands()
        session_commands.console = console

        # Mock the session manager
        with patch.object(session_commands, "manager") as mock_manager:
            # Mock finding auto-saved sessions with correct prefix
            from coda.constants import SESSION

            mock_session1 = Mock()
            mock_session1.id = "1"
            mock_session1.name = f"{SESSION.AUTO_PREFIX}20241205-143022"
            mock_session2 = Mock()
            mock_session2.id = "2"
            mock_session2.name = f"{SESSION.AUTO_PREFIX}20241205-151545"
            mock_manager.get_active_sessions.return_value = [mock_session1, mock_session2]
            mock_manager.delete_session.return_value = None

            # Mock the theme system to return our custom theme
            with patch("coda.themes.get_console_theme", return_value=custom_theme.console):
                # Mock Confirm.ask to return True (yes to deletion)
                with patch("coda.session.commands.Confirm.ask", return_value=True):
                    # Delete all sessions using the actual method
                    session_commands._delete_all_sessions(["--auto-only"])

        # Verify status was called with theme color
        console.status.assert_called_once()
        status_call = console.status.call_args[0][0]
        # Should use magenta (our test theme's info color)
        assert "[magenta]" in status_call
        assert "Deleting" in status_call
        assert "sessions..." in status_call

    def test_multiple_theme_switches_apply_correctly(self, mock_config):
        """Test that switching themes multiple times applies colors correctly."""
        # Mock console to capture output
        console = Mock(spec=Console)
        console.print = Mock()

        # Mock provider
        provider = MockProvider()
        models = [Model(id="mock-echo", name="Mock Echo", provider="mock", metadata={})]

        # Create chat session
        session = ChatSession(
            provider=provider,
            model="mock-echo",
            config=mock_config,
            console=console,
            provider_name="mock",
            factory=Mock(),
            unique_models=models,
        )

        # Test with different themes
        themes = [
            ConsoleTheme(user_message="red", assistant_message="green"),
            ConsoleTheme(user_message="blue", assistant_message="yellow"),
            ConsoleTheme(user_message="magenta", assistant_message="cyan"),
        ]

        for theme in themes:
            console.print.reset_mock()  # Clear previous calls

            with patch("coda.themes.get_console_theme", return_value=theme):
                session.run_one_shot("Test")

            # Verify colors match current theme
            user_call = console.print.call_args_list[0]
            assert f"[{theme.user_message}]User:[/{theme.user_message}]" in str(user_call)

            assistant_call = console.print.call_args_list[1]
            assert f"[{theme.assistant_message}]Assistant:[/{theme.assistant_message}]" in str(
                assistant_call
            )

    @pytest.mark.asyncio
    async def test_different_modes_use_theme_thinking_messages(self, mock_config, custom_theme):
        """Test that different developer modes show themed thinking messages."""
        modes_and_messages = [
            (DeveloperMode.CODE, "Generating code"),
            (DeveloperMode.DEBUG, "Analyzing"),
            (DeveloperMode.EXPLAIN, "Preparing explanation"),
            (DeveloperMode.REVIEW, "Reviewing"),
            (DeveloperMode.REFACTOR, "Analyzing code structure"),
            (DeveloperMode.PLAN, "Planning"),
        ]

        for mode, expected_message in modes_and_messages:
            # Mock console
            console = Mock(spec=Console)
            console.status = Mock()
            console.print = Mock()

            # Create a mock status context manager
            mock_status = Mock()
            mock_status.__enter__ = Mock(return_value=mock_status)
            mock_status.__exit__ = Mock(return_value=None)
            mock_status.stop = Mock()
            console.status.return_value = mock_status

            # Mock CLI with current mode
            cli = Mock()
            cli.interrupt_event = Mock()
            cli.interrupt_event.is_set.return_value = False
            cli.current_mode = mode
            cli.current_model = "test-model"
            cli.reset_interrupt = Mock()
            cli.start_interrupt_listener = Mock()
            cli.stop_interrupt_listener = Mock()
            cli.get_input = AsyncMock(return_value="Test message")
            cli.process_slash_command = AsyncMock(return_value=False)
            cli.session_commands = Mock()
            cli.session_commands.add_message = Mock()

            # Mock provider with streaming response
            from unittest.mock import Mock as MockChunk

            chunk = MockChunk()
            chunk.content = "Test response"
            provider = Mock()
            provider.chat_stream = Mock(return_value=iter([chunk]))
            messages = []

            # Mock the theme system
            with patch("coda.themes.get_console_theme", return_value=custom_theme.console):
                # Call the chat interaction handler
                await _handle_chat_interaction(provider, cli, messages, console, mock_config)

            # Verify correct thinking message with theme color
            console.status.assert_called_once()
            status_call = console.status.call_args[0][0]
            assert "[magenta]" in status_call  # Our test theme's info color
            assert expected_message in status_call
