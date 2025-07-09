"""Interactive session integration tests with mock provider."""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.providers import Message, MockProvider, Role
from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestInteractiveSessionIntegration:
    """Test interactive CLI session management integration."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def setup_interactive_cli(self, temp_db_path):
        """Set up interactive CLI with session management."""
        # Initialize components
        mock_provider = MockProvider()
        cli = InteractiveCLI()

        # Create session database and manager
        db = SessionDatabase(temp_db_path)
        session_manager = SessionManager(db)
        cli.session_commands = SessionCommands(session_manager)

        # Set up provider info
        models = mock_provider.list_models()
        cli.set_provider_info("mock", mock_provider, None, "mock-echo", models)

        yield cli, mock_provider, db

        db.close()

    def test_complete_session_workflow(self, setup_interactive_cli):
        """Test complete session workflow: chat -> save -> clear -> load -> continue."""
        cli, mock_provider, db = setup_interactive_cli

        # Simulate conversation messages (as interactive.py maintains them)
        cli_messages = []

        # === Phase 1: Start conversation ===
        user_msg = Message(role=Role.USER, content="What is Python?")
        cli_messages.append(user_msg)

        # Track in session commands
        cli.session_commands.add_message(
            "user", "What is Python?", {"provider": "mock", "model": "mock-echo", "mode": "general"}
        )

        # Get AI response
        ai_response = mock_provider.chat(cli_messages, "mock-echo")
        assistant_msg = Message(role=Role.ASSISTANT, content=ai_response.content)
        cli_messages.append(assistant_msg)

        # Track response
        cli.session_commands.add_message(
            "assistant", ai_response, {"provider": "mock", "model": "mock-echo"}
        )

        assert len(cli_messages) == 2
        assert "Python" in ai_response.content

        # === Phase 2: Continue conversation ===
        user_msg2 = Message(role=Role.USER, content="Tell me about decorators")
        cli_messages.append(user_msg2)
        cli.session_commands.add_message("user", "Tell me about decorators", {"provider": "mock"})

        ai_response2 = mock_provider.chat(cli_messages, "mock-echo")
        assistant_msg2 = Message(role=Role.ASSISTANT, content=ai_response2.content)
        cli_messages.append(assistant_msg2)
        cli.session_commands.add_message("assistant", ai_response2, {"provider": "mock"})

        assert len(cli_messages) == 4
        assert "decorator" in ai_response2.content.lower()

        # === Phase 3: Save session ===
        with patch("rich.prompt.Prompt.ask", return_value=""):
            result = cli.session_commands.handle_session_command(["save", "Test Session"])

        assert "Session saved" in result or "Session updated" in result
        session_id = cli.session_commands.current_session_id
        assert session_id is not None

        # === Phase 4: Clear conversation ===
        original_message_count = len(cli_messages)

        # Simulate /clear command
        cli.session_commands.clear_conversation()
        was_cleared = cli.session_commands.was_conversation_cleared()

        # Simulate CLI clearing its messages
        if was_cleared:
            cli_messages.clear()

        assert len(cli_messages) == 0
        assert len(cli.session_commands.current_messages) == 0
        assert was_cleared

        # === Phase 5: Test AI has no memory ===
        test_msg = Message(role=Role.USER, content="What were we discussing?")
        cli_messages.append(test_msg)

        no_memory_response = mock_provider.chat(cli_messages, "mock-echo")

        # Should not remember previous conversation
        has_memory = any(
            word in no_memory_response.content.lower() for word in ["python", "decorator"]
        )
        assert not has_memory, f"AI should not remember previous conversation: {no_memory_response}"

        # Remove test message
        cli_messages.pop()

        # === Phase 6: Load session ===
        result = cli.session_commands.handle_session_command(["load", "Test Session"])
        assert result is None  # Load prints directly

        # Check if messages were loaded
        loaded_messages = cli.session_commands.get_loaded_messages_for_cli()
        assert len(loaded_messages) == original_message_count

        # Simulate the CLI integration (from interactive.py)
        if loaded_messages:
            cli_messages.clear()
            cli_messages.extend(loaded_messages)

        assert len(cli_messages) == original_message_count

        # === Phase 7: Test AI memory restoration ===
        memory_test_msg = Message(
            role=Role.USER, content="What were we discussing about decorators?"
        )
        cli_messages.append(memory_test_msg)

        memory_response = mock_provider.chat(cli_messages, "mock-echo")

        # Should remember previous conversation
        has_context = any(
            word in memory_response.content.lower()
            for word in ["python", "decorator", "function", "modify"]
        )
        assert has_context, f"AI should remember context after loading: {memory_response}"

        # === Phase 8: Continue conversation ===
        # Remove test message, add AI response
        cli_messages.pop()
        cli_messages.append(Message(role=Role.ASSISTANT, content=memory_response))

        # Add new question
        followup_msg = Message(role=Role.USER, content="Can you show me a decorator example?")
        cli_messages.append(followup_msg)

        followup_response = mock_provider.chat(cli_messages, "mock-echo")

        # Should continue conversation naturally
        assert (
            "decorator" in followup_response.content.lower()
            or "python" in followup_response.content.lower()
        )

    def test_session_commands_integration(self, setup_interactive_cli):
        """Test session commands work correctly with CLI."""
        cli, mock_provider, db = setup_interactive_cli

        # Add messages
        cli.session_commands.add_message("user", "Hello", {"provider": "mock"})
        cli.session_commands.add_message("assistant", "Hi there!", {"provider": "mock"})

        # Test save
        with patch("rich.prompt.Prompt.ask", return_value=""):
            result = cli.session_commands.handle_session_command(["save", "CLI Test"])
        assert "Session saved" in result or "Session updated" in result

        # Test list
        result = cli.session_commands.handle_session_command(["list"])
        assert result is None  # List displays table

        # Test clear
        cli.session_commands.clear_conversation()
        assert len(cli.session_commands.current_messages) == 0

        # Test load
        result = cli.session_commands.handle_session_command(["load", "CLI Test"])
        assert result is None  # Load displays info
        assert len(cli.session_commands.current_messages) == 2

    def test_mock_provider_context_awareness(self, setup_interactive_cli):
        """Test mock provider correctly maintains conversation context."""
        cli, mock_provider, db = setup_interactive_cli

        # Build conversation
        messages = [
            Message(role=Role.USER, content="What is Python?"),
            Message(role=Role.ASSISTANT, content="Python is a programming language"),
            Message(role=Role.USER, content="Tell me about decorators"),
            Message(role=Role.ASSISTANT, content="Decorators modify functions"),
        ]

        # Test context-aware response
        messages.append(
            Message(role=Role.USER, content="What were we discussing about decorators?")
        )
        response = mock_provider.chat(messages, "mock-echo")

        # Should reference previous conversation
        context_indicators = ["decorator", "python", "function", "modify", "syntax"]
        has_context = any(indicator in response.content.lower() for indicator in context_indicators)
        assert has_context, f"Mock provider should show context awareness: {response}"

        # Test without context
        no_context_messages = [Message(role=Role.USER, content="What were we discussing?")]
        no_context_response = mock_provider.chat(no_context_messages, "mock-echo")

        # Should not reference specific topics
        has_specific_context = any(
            word in no_context_response.content.lower() for word in ["python", "decorator"]
        )
        assert not has_specific_context, (
            f"Without context, should not reference specific topics: {no_context_response}"
        )

    def test_session_export_with_interactive_data(self, setup_interactive_cli):
        """Test session export contains correct interactive conversation data."""
        cli, mock_provider, db = setup_interactive_cli

        # Create conversation
        cli.session_commands.add_message("user", "Test export message", {"provider": "mock"})
        cli.session_commands.add_message("assistant", "Export response", {"provider": "mock"})

        # Save session
        with patch("rich.prompt.Prompt.ask", return_value=""):
            cli.session_commands.handle_session_command(["save", "Export Test"])

        session_id = cli.session_commands.current_session_id

        # Test export
        session_manager = cli.session_commands.manager
        json_export = session_manager.export_session(session_id, "json")
        md_export = session_manager.export_session(session_id, "markdown")

        # Verify content
        assert "Test export message" in json_export
        assert "Export response" in json_export
        assert "Test export message" in md_export
        assert "Export response" in md_export

        # Verify structure
        assert '"role": "user"' in json_export
        assert '"role": "assistant"' in json_export
        assert "👤 User" in md_export or "🤖 Assistant" in md_export

    def test_conversation_continuity_edge_cases(self, setup_interactive_cli):
        """Test edge cases in conversation continuity."""
        cli, mock_provider, db = setup_interactive_cli

        # Test loading non-existent session
        result = cli.session_commands.handle_session_command(["load", "NonExistent"])
        assert "Session not found" in result

        # Test saving empty conversation
        result = cli.session_commands.handle_session_command(["save", "Empty"])
        assert "No messages to save" in result

        # Test clear when already empty
        cli.session_commands.clear_conversation()
        was_cleared = cli.session_commands.was_conversation_cleared()
        assert was_cleared

        # Test loading when no flag set
        loaded_messages = cli.session_commands.get_loaded_messages_for_cli()
        assert len(loaded_messages) == 0
