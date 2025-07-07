"""Unit tests for session auto-save functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestSessionAutoSave:
    """Test auto-save functionality for sessions."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def session_manager(self, temp_db_path):
        """Create session manager with temporary database."""
        db = SessionDatabase(temp_db_path)
        manager = SessionManager(db)
        yield manager
        db.close()

    @pytest.fixture
    def session_commands(self, session_manager):
        """Create session commands instance."""
        return SessionCommands(session_manager)

    def test_auto_save_enabled_by_default(self, session_commands):
        """Test that auto-save is enabled by default."""
        assert session_commands.auto_save_enabled is True

    def test_auto_save_disabled_when_configured(self, session_manager):
        """Test that auto-save can be disabled."""
        commands = SessionCommands(session_manager)
        commands.auto_save_enabled = False
        assert commands.auto_save_enabled is False

    def test_no_auto_save_without_user_message(self, session_commands):
        """Test that auto-save doesn't trigger without user message."""
        # Add only assistant message
        session_commands.add_message(
            role="assistant",
            content="Hello there!",
            metadata={"provider": "test", "model": "test-model"},
        )

        # Should not create a session
        assert session_commands.current_session_id is None
        assert len(session_commands.current_messages) == 1

    def test_auto_save_on_first_exchange(self, session_commands):
        """Test that auto-save triggers on first user-assistant exchange."""
        # Add user message
        session_commands.add_message(role="user", content="Hello AI!", metadata={"mode": "general"})

        # Session should not be created yet
        assert session_commands.current_session_id is None

        # Add assistant response
        session_commands.add_message(
            role="assistant",
            content="Hello! How can I help you?",
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Session should now be created
        assert session_commands.current_session_id is not None
        assert len(session_commands.current_messages) == 2

        # Verify session in database
        session = session_commands.manager.get_session(session_commands.current_session_id)
        assert session is not None
        assert session.name.startswith("auto-")
        assert session.description == "Auto-saved conversation"
        assert session.provider == "mock"
        assert session.model == "mock-echo"
        assert session.mode == "general"

        # Verify messages were saved
        messages = session_commands.manager.get_messages(session.id)
        assert len(messages) == 2
        assert messages[0].role == "user"
        assert messages[0].content == "Hello AI!"
        assert messages[1].role == "assistant"
        assert messages[1].content == "Hello! How can I help you?"

    def test_no_auto_save_when_disabled(self, session_commands):
        """Test that auto-save doesn't trigger when disabled."""
        # Disable auto-save
        session_commands.auto_save_enabled = False

        # Add user message
        session_commands.add_message(role="user", content="Hello AI!", metadata={"mode": "general"})

        # Add assistant response
        session_commands.add_message(
            role="assistant",
            content="Hello! How can I help you?",
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Session should not be created
        assert session_commands.current_session_id is None
        assert len(session_commands.current_messages) == 2

    def test_subsequent_messages_saved_to_existing_session(self, session_commands):
        """Test that subsequent messages are saved to existing auto-saved session."""
        # Create initial exchange to trigger auto-save
        session_commands.add_message(
            role="user", content="First message", metadata={"mode": "general"}
        )
        session_commands.add_message(
            role="assistant",
            content="First response",
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Capture session ID
        session_id = session_commands.current_session_id
        assert session_id is not None

        # Add more messages
        session_commands.add_message(
            role="user", content="Second message", metadata={"mode": "general"}
        )
        session_commands.add_message(
            role="assistant",
            content="Second response",
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Should still be the same session
        assert session_commands.current_session_id == session_id

        # Verify all messages were saved
        messages = session_commands.manager.get_messages(session_id)
        assert len(messages) == 4
        assert messages[2].content == "Second message"
        assert messages[3].content == "Second response"

    def test_rename_auto_saved_session(self, session_commands):
        """Test renaming an auto-saved session."""
        # Create auto-saved session
        session_commands.add_message(
            role="user", content="Test message", metadata={"mode": "general"}
        )
        session_commands.add_message(
            role="assistant",
            content="Test response",
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        session_id = session_commands.current_session_id
        assert session_id is not None

        # Rename the session
        result = session_commands._rename_session(["My Important Chat"])
        assert result == "Session renamed to: My Important Chat"

        # Verify the rename
        session = session_commands.manager.get_session(session_id)
        assert session.name == "My Important Chat"

    @patch("coda.themes.get_themed_console")
    def test_auto_save_notification(self, mock_get_console, session_manager):
        """Test that auto-save shows notification."""
        # Create mock console
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        # Create commands with mocked console
        commands = SessionCommands(session_manager)

        # Trigger auto-save
        commands.add_message(role="user", content="Test", metadata={"mode": "general"})
        commands.add_message(
            role="assistant",
            content="Response",
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Verify notification was printed
        commands.console.print.assert_called()
        calls = commands.console.print.call_args_list
        # Find the auto-save notification
        found_notification = False
        for call in calls:
            if call[0] and "Auto-saved session:" in str(call[0][0]):
                found_notification = True
                break
        assert found_notification

    @patch("coda.themes.get_themed_console")
    def test_auto_save_error_handling(self, mock_get_console, session_manager):
        """Test that auto-save handles errors gracefully."""
        # Create mock console
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        # Create commands with mocked console
        commands = SessionCommands(session_manager)

        # Mock the create_session to raise an error
        with patch.object(commands.manager, "create_session", side_effect=Exception("DB Error")):
            # Trigger auto-save
            commands.add_message(role="user", content="Test", metadata={"mode": "general"})
            commands.add_message(
                role="assistant",
                content="Response",
                metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
            )

        # Verify error was handled
        assert commands.current_session_id is None  # No session created
        assert len(commands.current_messages) == 2  # Messages still tracked

        # Verify error notification was printed
        commands.console.print.assert_called()
        calls = commands.console.print.call_args_list
        # Find the error notification
        found_error = False
        for call in calls:
            if call[0] and "Auto-save failed:" in str(call[0][0]):
                found_error = True
                break
        assert found_error
