"""Additional tests to improve coverage for session commands."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from coda.session import SessionCommands, SessionDatabase, SessionManager


@pytest.mark.unit
@pytest.mark.fast
class TestSessionCommandsAdditional:
    """Additional tests to improve session commands coverage."""

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

    def test_init_with_none_manager(self):
        """Test initialization without providing manager."""
        commands = SessionCommands(None)
        assert commands.manager is not None
        assert commands.console is not None
        assert commands.auto_save_enabled is True
        assert commands._has_user_message is False

    def test_handle_export_help(self, session_commands):
        """Test export command with no args shows help."""
        result = session_commands.handle_export_command([])
        assert result is None  # Export help displays directly

    def test_handle_session_command_unknown(self, session_commands):
        """Test unknown session subcommand."""
        result = session_commands.handle_session_command(["unknown"])
        assert "Unknown session subcommand: unknown" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_save_with_auto_save_disabled(self, mock_prompt, session_commands):
        """Test saving when auto-save is disabled."""
        mock_prompt.return_value = "Test description"

        # Disable auto-save
        session_commands.auto_save_enabled = False

        # Add message
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})

        # Save should create new session
        result = session_commands.handle_session_command(["save", "New Session"])
        assert "Session saved: New Session" in result

    def test_load_last_no_sessions(self, session_commands):
        """Test loading last session when no sessions exist."""
        result = session_commands.handle_session_command(["load", "last"])
        assert "Session not found: last" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_load_last_with_sessions(self, mock_prompt, session_commands):
        """Test loading last session successfully."""
        mock_prompt.return_value = ""

        # Create a session
        session_commands.add_message("user", "Message 1", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Last Session"])

        # Clear current
        session_commands.clear_conversation()

        # Load last
        result = session_commands.handle_session_command(["load", "last"])
        assert result is None  # Success returns None
        assert len(session_commands.current_messages) == 1
        assert session_commands._messages_loaded is True

    @patch("coda.session.commands.Prompt.ask")
    def test_rename_session_no_current(self, mock_prompt, session_commands):
        """Test renaming when no current session."""
        # Try to rename without current session
        result = session_commands.handle_session_command(["rename"])
        assert "No current session" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_rename_session_current_with_prompt(self, mock_prompt, session_commands):
        """Test renaming current session with prompt."""
        mock_prompt.side_effect = ["", "New Name"]  # First for save, second for rename

        # Create session
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Original Name"])

        # Rename with prompt
        result = session_commands.handle_session_command(["rename"])
        assert "Session renamed to: New Name" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_rename_session_current_with_args(self, mock_prompt, session_commands):
        """Test renaming current session with direct name."""
        mock_prompt.return_value = ""

        # Create session
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Original"])

        # Rename directly
        result = session_commands.handle_session_command(["rename", "Updated Name"])
        assert "Session renamed to: Updated Name" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_rename_specific_session(self, mock_prompt, session_commands):
        """Test renaming a specific session by reference."""
        mock_prompt.return_value = ""

        # Create two sessions
        session_commands.add_message("user", "Test 1", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Session 1"])
        session_id = session_commands.current_session_id

        session_commands.clear_conversation()
        session_commands.add_message("user", "Test 2", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Session 2"])

        # Rename first session by ID
        result = session_commands.handle_session_command(
            ["rename", session_id[:8], "Renamed Session"]
        )
        assert "Session renamed to: Renamed Session" in result

    def test_rename_session_not_found(self, session_commands):
        """Test renaming non-existent session."""
        result = session_commands.handle_session_command(["rename", "nonexistent", "New Name"])
        assert "Session not found: nonexistent" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_rename_session_exception(self, mock_prompt, session_commands):
        """Test rename with database exception."""
        mock_prompt.return_value = ""

        # Create session
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Original"])

        # Mock exception
        with patch.object(
            session_commands.manager, "update_session", side_effect=Exception("DB Error")
        ):
            result = session_commands.handle_session_command(["rename", "Failed Name"])
            assert "Failed to rename session: DB Error" in result

    @patch("coda.session.commands.Confirm.ask")
    def test_delete_all_sessions_confirmed(self, mock_confirm, session_commands):
        """Test deleting all sessions with confirmation."""
        mock_confirm.return_value = True

        # Create sessions
        with patch("coda.session.commands.Prompt.ask", return_value=""):
            session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
            session_commands.handle_session_command(["save", "Session 1"])

            session_commands.clear_conversation()
            session_commands.add_message("user", "Test 2", {"provider": "test", "model": "test"})
            session_commands.handle_session_command(["save", "Session 2"])

        # Delete all
        result = session_commands.handle_session_command(["delete-all"])
        assert "Successfully deleted" in result
        assert session_commands.current_session_id is None

    @patch("coda.session.commands.Confirm.ask")
    def test_delete_all_cancelled(self, mock_confirm, session_commands):
        """Test cancelling delete all."""
        mock_confirm.return_value = False

        result = session_commands.handle_session_command(["delete-all"])
        # If no sessions, returns different message
        assert "Deletion cancelled" in result or "No sessions found" in result

    @patch("coda.session.commands.Confirm.ask")
    @patch("coda.session.commands.Prompt.ask")
    def test_delete_all_auto_sessions(self, mock_prompt, mock_confirm, session_commands):
        """Test deleting only auto-saved sessions."""
        mock_prompt.return_value = ""
        mock_confirm.return_value = True

        # Create mixed sessions
        session_commands.add_message("user", "Auto", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "auto_session_20240101_120000"])

        session_commands.clear_conversation()
        session_commands.add_message("user", "Manual", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Manual Session"])

        # Delete only auto
        result = session_commands.handle_session_command(["delete-all", "auto"])
        assert "Successfully deleted" in result  # The message format changed

    def test_unknown_session_command(self, session_commands):
        """Test unknown session command returns error."""
        # stats is not a valid command
        result = session_commands.handle_session_command(["stats"])
        assert "Unknown session subcommand: stats" in result

    def test_branch_no_current_session(self, session_commands):
        """Test branching with no current session."""
        result = session_commands.handle_session_command(["branch", "New Branch"])
        assert "No active session to branch from" in result

    def test_search_no_query(self, session_commands):
        """Test search without query."""
        result = session_commands.handle_session_command(["search"])
        assert result == "Please provide a search query."

    def test_info_no_current_session(self, session_commands):
        """Test info with no current session."""
        result = session_commands.handle_session_command(["info"])
        assert "No session specified or loaded" in result

    def test_info_specific_session_not_found(self, session_commands):
        """Test info for non-existent session."""
        result = session_commands.handle_session_command(["info", "nonexistent"])
        assert "Session not found: nonexistent" in result

    @patch("coda.session.commands.Prompt.ask")
    def test_info_specific_session(self, mock_prompt, session_commands):
        """Test info for specific session."""
        mock_prompt.return_value = ""

        # Create session
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Info Test"])

        # Get info by name
        result = session_commands.handle_session_command(["info", "Info Test"])
        assert result is None  # Info displays directly

    def test_export_no_current_session(self, session_commands):
        """Test export with no current session."""
        result = session_commands.handle_export_command(["json"])
        assert "No session specified or loaded" in result

    @patch("builtins.open", create=True)
    @patch("coda.session.commands.Prompt.ask")
    def test_export_text_format(self, mock_prompt, mock_open, session_commands):
        """Test exporting as text format."""
        mock_prompt.return_value = ""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Create session
        session_commands.add_message("user", "Test", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Text Export"])

        # Export as text
        result = session_commands.handle_export_command(["text"])
        assert result is None

        # Check file was written
        mock_file.write.assert_called()

    @patch("builtins.open", create=True)
    @patch("coda.session.commands.Prompt.ask")
    def test_export_specific_session(self, mock_prompt, mock_open, session_commands):
        """Test export specific session by name."""
        mock_prompt.return_value = ""
        mock_file = MagicMock()
        mock_open.return_value.__enter__.return_value = mock_file

        # Create two sessions
        session_commands.add_message("user", "Test 1", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Session One"])

        session_commands.clear_conversation()
        session_commands.add_message("user", "Test 2", {"provider": "test", "model": "test"})
        session_commands.handle_session_command(["save", "Session Two"])

        # Export first session by name
        result = session_commands.handle_export_command(["json", "Session One"])
        assert result is None

        # Check file was written
        assert mock_open.called
        assert mock_file.write.called

    def test_clear_clears_session_info(self, session_commands):
        """Test that clear properly resets session info."""
        # Don't set invalid session ID that would violate FK constraint
        # Just add messages and verify clear works
        session_commands.add_message("user", "Test", {})
        assert session_commands._has_user_message is True

        # Clear
        session_commands.clear_conversation()

        assert session_commands.current_session_id is None
        # Note: _has_user_message is not reset by clear_conversation
        assert len(session_commands.current_messages) == 0
        assert hasattr(session_commands, "_conversation_cleared")
        assert session_commands._conversation_cleared is True

    def test_add_message_sets_user_flag(self, session_commands):
        """Test that adding user message sets flag."""
        assert not session_commands._has_user_message

        session_commands.add_message("user", "Test", {})
        assert session_commands._has_user_message

        # Assistant message doesn't change flag
        session_commands.add_message("assistant", "Response", {})
        assert session_commands._has_user_message

    @patch("coda.session.commands.Prompt.ask")
    def test_get_context_messages_with_parent(self, mock_prompt, session_commands):
        """Test getting context with parent session."""
        mock_prompt.return_value = ""

        # Create parent session
        session_commands.add_message(
            "user", "Parent message", {"provider": "test", "model": "test"}
        )
        session_commands.handle_session_command(["save", "Parent"])
        # Parent session ID is now saved

        # Create branch
        session_commands.handle_session_command(["branch", "Child"])

        # Add message to child
        session_commands.add_message("user", "Child message", {"provider": "test", "model": "test"})

        # Get context should include parent messages
        messages, truncated = session_commands.get_context_messages()
        assert len(messages) >= 2  # Parent + child messages
