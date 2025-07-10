"""Unit tests for 'load last session' functionality."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestSessionLast:
    """Test load last session functionality."""

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

    def test_load_last_with_no_sessions(self, session_commands):
        """Test loading last session when no sessions exist."""
        result = session_commands._load_last_session()
        assert result == "No sessions found to load."

    def test_load_last_with_single_session(self, session_commands):
        """Test loading last session with one session."""
        # Create a session
        session = session_commands.manager.create_session(
            name="Test Session",
            description="Test description",
            provider="mock",
            model="mock-echo",
            mode="general",
        )

        # Add some messages
        session_commands.manager.add_message(
            session_id=session.id, role="user", content="Hello", metadata={}
        )
        session_commands.manager.add_message(
            session_id=session.id, role="assistant", content="Hi there!", metadata={}
        )

        # Load last session
        result = session_commands._load_last_session()
        assert result is None  # Success

        # Verify session loaded
        assert session_commands.current_session_id == session.id
        assert len(session_commands.current_messages) == 2
        assert session_commands.current_messages[0]["content"] == "Hello"
        assert session_commands.current_messages[1]["content"] == "Hi there!"
        assert session_commands._messages_loaded is True

    def test_load_last_with_multiple_sessions(self, session_commands):
        """Test loading last session returns most recent."""
        # Create older session
        older = session_commands.manager.create_session(
            name="Older Session", provider="mock", model="mock-echo", mode="general"
        )

        # Add a message to older session
        session_commands.manager.add_message(
            session_id=older.id, role="user", content="Old message", metadata={}
        )

        # Create newer session (will have later created_at)
        import time

        time.sleep(0.1)  # Ensure different timestamp

        newer = session_commands.manager.create_session(
            name="Newer Session", provider="mock", model="mock-smart", mode="code"
        )

        # Add messages to newer session
        session_commands.manager.add_message(
            session_id=newer.id, role="user", content="New message", metadata={}
        )
        session_commands.manager.add_message(
            session_id=newer.id, role="assistant", content="New response", metadata={}
        )

        # Load last session
        result = session_commands._load_last_session()
        assert result is None  # Success

        # Should load the newer session
        assert session_commands.current_session_id == newer.id
        assert len(session_commands.current_messages) == 2
        assert session_commands.current_messages[0]["content"] == "New message"

    def test_load_last_preserves_metadata(self, session_commands):
        """Test that load last preserves message metadata."""
        # Create session
        session = session_commands.manager.create_session(
            name="Metadata Test", provider="ollama", model="llama3", mode="debug"
        )

        # Add message with metadata
        session_commands.manager.add_message(
            session_id=session.id,
            role="user",
            content="Test",
            metadata={"custom": "data"},
            model="llama3",
            provider="ollama",
            token_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            cost=0.001,
        )

        # Load last session
        session_commands._load_last_session()

        # Check metadata preserved
        msg = session_commands.current_messages[0]
        assert msg["metadata"]["provider"] == "ollama"
        assert msg["metadata"]["model"] == "llama3"
        assert msg["metadata"]["mode"] == "debug"
        assert msg["metadata"]["token_usage"]["total_tokens"] == 30
        assert msg["metadata"]["cost"] == 0.001

    @patch("coda.themes.get_themed_console")
    def test_load_last_displays_session_info(self, mock_get_console, session_manager):
        """Test that load last displays session information."""
        # Create mock console
        mock_console = MagicMock()
        mock_get_console.return_value = mock_console

        # Create commands with mocked console
        commands = SessionCommands(session_manager)

        # Create session with description
        session = commands.manager.create_session(
            name="Display Test",
            description="This is a test session",
            provider="litellm",
            model="gpt-4",
            mode="explain",
        )

        # Add a message
        commands.manager.add_message(
            session_id=session.id, role="user", content="Test", metadata={}
        )

        # Load last session
        commands._load_last_session()

        # Verify console output
        calls = commands.console.print.call_args_list

        # Should display session name
        assert any("Display Test" in str(call[0][0]) for call in calls)

        # Should display provider and model
        assert any("litellm" in str(call[0][0]) and "gpt-4" in str(call[0][0]) for call in calls)

        # Should display description
        assert any("This is a test session" in str(call[0][0]) for call in calls)

    def test_session_last_command_integration(self, session_commands):
        """Test /session last command through handle_session_command."""
        # Create a session
        session = session_commands.manager.create_session(
            name="Command Test", provider="mock", model="mock-echo", mode="general"
        )

        # Add message
        session_commands.manager.add_message(
            session_id=session.id, role="user", content="Test command", metadata={}
        )

        # Call through command handler
        result = session_commands.handle_session_command(["last"])

        # Should succeed
        assert result is None
        assert session_commands.current_session_id == session.id
