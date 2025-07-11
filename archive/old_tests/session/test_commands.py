"""Tests for session command functionality."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.base.session import SessionCommands, SessionDatabase, SessionManager


class TestSessionCommands:
    """Test session command handling."""

    @pytest.fixture
    def session_commands(self):
        """Create session commands with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = SessionDatabase(db_path)
        manager = SessionManager(db)
        commands = SessionCommands(manager)
        yield commands

        # Cleanup
        db.close()
        db_path.unlink()

    def test_help_command(self, session_commands, capsys):
        """Test session help display."""
        result = session_commands.handle_session_command([])

        # Should return None and print help
        assert result is None

        # Check console output (mock console captures this)
        # In real implementation, this would be captured by Rich console

    def test_save_command_no_messages(self, session_commands):
        """Test saving with no messages."""
        result = session_commands.handle_session_command(["save", "Test Session"])
        assert result == "No messages to save."

    @patch("coda.session.commands.Prompt.ask")
    def test_save_and_load_session(self, mock_prompt, session_commands):
        """Test saving and loading a session."""
        # Mock prompt to return empty description
        mock_prompt.return_value = ""

        # Add some messages
        session_commands.add_message("user", "Hello", {"provider": "test", "model": "test-model"})
        session_commands.add_message(
            "assistant", "Hi there!", {"provider": "test", "model": "test-model"}
        )

        # Save session
        result = session_commands.handle_session_command(["save", "My Test Session"])
        # Could be either saved or updated depending on auto-save
        assert (
            "Session saved: My Test Session" in result
            or "Session updated: My Test Session" in result
        )
        assert session_commands.current_session_id is not None

        # Clear and verify
        session_commands.clear_conversation()
        assert len(session_commands.current_messages) == 0

        # Load session by name
        result = session_commands.handle_session_command(["load", "My Test Session"])
        assert result is None  # Load prints directly to console
        assert len(session_commands.current_messages) == 2
        assert session_commands.current_messages[0]["content"] == "Hello"

    @patch("coda.session.commands.Prompt.ask")
    def test_list_sessions(self, mock_prompt, session_commands):
        """Test listing sessions."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create some sessions
        session_commands.add_message("user", "Test 1", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Session 1"])

        session_commands.clear_conversation()
        session_commands.add_message("user", "Test 2", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Session 2"])

        # List sessions
        result = session_commands.handle_session_command(["list"])
        assert result is None  # List displays table directly

    @patch("coda.session.commands.Prompt.ask")
    def test_branch_session(self, mock_prompt, session_commands):
        """Test branching from current session."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create and save initial session
        session_commands.add_message(
            "user", "Original message", {"provider": "test", "model": "test"}
        )
        session_commands.add_message(
            "assistant", "Original response", {"provider": "test", "model": "test"}
        )
        session_commands.handle_session_command(["save", "Original Session"])

        # Branch from current
        result = session_commands.handle_session_command(["branch", "Branched Session"])
        assert "Created branch: Branched Session" in result

        # Verify we're now on the branch
        parent_id = session_commands.current_session_id
        assert parent_id is not None

    @patch("coda.session.commands.Prompt.ask")
    def test_delete_session(self, mock_prompt, session_commands):
        """Test deleting a session."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create a session
        session_commands.add_message("user", "Delete me", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "To Delete"])

        # Mock confirmation
        with patch("coda.session.commands.Confirm.ask", return_value=True):
            result = session_commands.handle_session_command(["delete", "To Delete"])
            assert "Session deleted: To Delete" in result
            assert session_commands.current_session_id is None

    @patch("coda.session.commands.Prompt.ask")
    def test_delete_cancelled(self, mock_prompt, session_commands):
        """Test cancelling session deletion."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create a session
        session_commands.add_message("user", "Keep me", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "To Keep"])

        # Mock confirmation denial
        with patch("coda.session.commands.Confirm.ask", return_value=False):
            result = session_commands.handle_session_command(["delete", "To Keep"])
            assert result == "Deletion cancelled."

    @patch("coda.session.commands.Prompt.ask")
    def test_session_info(self, mock_prompt, session_commands):
        """Test displaying session information."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create a session with some data
        session_commands.add_message(
            "user",
            "Info test",
            {"provider": "test_provider", "model": "test_model", "mode": "general"},
        )
        session_commands.handle_session_command(["save", "Info Session"])

        # Get info for current session
        result = session_commands.handle_session_command(["info"])
        assert result is None  # Info displays panel directly

    @patch("coda.session.commands.Prompt.ask")
    def test_search_sessions(self, mock_prompt, session_commands):
        """Test searching across sessions."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create sessions with searchable content
        session_commands.add_message(
            "user", "Python programming question", {"provider": "test", "model": "test"}
        )
        session_commands.handle_session_command(["save", "Python Session"])

        session_commands.clear_conversation()
        session_commands.add_message(
            "user", "JavaScript async await", {"provider": "test", "model": "test"}
        )
        session_commands.handle_session_command(["save", "JS Session"])

        # Search
        result = session_commands.handle_session_command(["search", "Python"])
        assert result is None  # Search displays results directly

    @patch("coda.session.commands.Prompt.ask")
    def test_export_json(self, mock_prompt, session_commands):
        """Test exporting session as JSON."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create session
        session_commands.add_message("user", "Export me", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Export Test"])

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = Mock()
            result = session_commands.handle_export_command(["json"])
            assert result is None  # Export prints success message

    @patch("coda.session.commands.Prompt.ask")
    def test_export_markdown(self, mock_prompt, session_commands):
        """Test exporting session as Markdown."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create session
        session_commands.add_message("user", "Export to MD", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "MD Export"])

        # Mock file operations
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value = Mock()
            result = session_commands.handle_export_command(["markdown"])
            assert result is None

    def test_export_invalid_format(self, session_commands):
        """Test exporting with invalid format."""
        result = session_commands.handle_export_command(["invalid"])
        assert "Unknown export format: invalid" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_find_session_by_id(self, mock_prompt, session_commands):
        """Test finding sessions by ID."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create a session
        session_commands.add_message("user", "Find me", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Findable Session"])
        session_id = session_commands.current_session_id

        # Find by partial ID
        session = session_commands._find_session(session_id[:8])
        assert session is not None
        assert session.name == "Findable Session"

    @patch("coda.session.commands.Prompt.ask")
    def test_find_session_by_name(self, mock_prompt, session_commands):
        """Test finding sessions by name."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create sessions
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Unique Name"])

        # Find by exact name
        session = session_commands._find_session("Unique Name")
        assert session is not None

        # Find by partial name
        session = session_commands._find_session("Unique")
        assert session is not None

        # Case insensitive
        session = session_commands._find_session("unique name")
        assert session is not None

    @patch("coda.session.commands.Prompt.ask")
    def test_update_existing_session(self, mock_prompt, session_commands):
        """Test updating an existing session."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Create and save session
        session_commands.add_message("user", "Initial", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Initial Name"])
        session_id = session_commands.current_session_id

        # Add more messages and save with new name
        session_commands.add_message("user", "More content", {"provider": "test", "model": "test"})
        result = session_commands.handle_session_command(["save", "Updated Name"])

        assert "Session updated: Updated Name" in result
        assert session_commands.current_session_id == session_id

    def test_message_tracking(self, session_commands):
        """Test that messages are properly tracked."""
        # Add messages with metadata
        session_commands.add_message(
            "user",
            "Test message",
            {
                "provider": "oci_genai",
                "model": "cohere.command-r-plus",
                "mode": "code",
                "custom_field": "custom_value",
            },
        )

        assert len(session_commands.current_messages) == 1
        msg = session_commands.current_messages[0]
        assert msg["role"] == "user"
        assert msg["content"] == "Test message"
        assert msg["metadata"]["provider"] == "oci_genai"
        assert msg["metadata"]["custom_field"] == "custom_value"

    def test_clear_conversation(self, session_commands):
        """Test clearing conversation."""
        # Add messages
        session_commands.add_message("user", "Message 1", {})
        session_commands.add_message("assistant", "Response 1", {})
        assert len(session_commands.current_messages) == 2

        # Clear
        session_commands.clear_conversation()
        assert len(session_commands.current_messages) == 0
        assert session_commands.current_session_id is None

    @patch("coda.session.commands.Prompt.ask")
    def test_get_context_messages(self, mock_prompt, session_commands):
        """Test getting context messages."""
        # Mock prompts
        mock_prompt.return_value = ""

        # Without session (in-memory only)
        session_commands.add_message("user", "Test", {})
        messages, truncated = session_commands.get_context_messages()
        assert len(messages) == 1
        assert not truncated

        # With saved session
        session_commands.handle_session_command(["save", "Context Test"])
        messages, truncated = session_commands.get_context_messages(
            model="gpt-3.5-turbo", max_tokens=100
        )
        # Should use session manager's context windowing
        assert isinstance(messages, list)
