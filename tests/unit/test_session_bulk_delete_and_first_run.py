"""Unit tests for Phase 4.5 lower-priority features."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from rich.console import Console

from coda.cli.interactive import _check_first_run
from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestBulkDelete:
    """Test bulk delete functionality."""

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

    def test_delete_all_with_no_sessions(self, session_commands):
        """Test delete-all when no sessions exist."""
        result = session_commands._delete_all_sessions([])
        assert result == "No sessions found to delete."

    def test_delete_all_auto_only_with_no_auto_sessions(self, session_commands):
        """Test delete-all auto-only when no auto sessions exist."""
        # Create a non-auto session
        session_commands.manager.create_session(
            name="Manual Session", provider="mock", model="mock-echo"
        )

        result = session_commands._delete_all_sessions(["--auto-only"])
        assert result == "No auto-saved sessions found to delete."

    @patch("coda.session.commands.Confirm.ask")
    def test_delete_all_cancelled(self, mock_confirm, session_commands):
        """Test delete-all cancelled by user."""
        # Create sessions
        for i in range(3):
            session_commands.manager.create_session(
                name=f"Session {i}", provider="mock", model="mock-echo"
            )

        # User cancels
        mock_confirm.return_value = False

        result = session_commands._delete_all_sessions([])
        assert result == "Deletion cancelled."

        # Verify sessions still exist
        sessions = session_commands.manager.get_active_sessions(limit=10)
        assert len(sessions) == 3

    @patch("coda.session.commands.Confirm.ask")
    def test_delete_all_success(self, mock_confirm, session_commands):
        """Test successful delete-all."""
        # Create sessions
        for i in range(3):
            session_commands.manager.create_session(
                name=f"Session {i}", provider="mock", model="mock-echo"
            )

        # User confirms
        mock_confirm.return_value = True

        result = session_commands._delete_all_sessions([])
        assert result == "Successfully deleted 3 all session(s)."

        # Verify sessions deleted
        sessions = session_commands.manager.get_active_sessions(limit=10)
        assert len(sessions) == 0

    @patch("coda.session.commands.Confirm.ask")
    def test_delete_all_auto_only(self, mock_confirm, session_commands):
        """Test delete-all with auto-only flag."""
        # Create mixed sessions
        session_commands.manager.create_session(
            name="auto-20250105_120000", provider="mock", model="mock-echo"
        )
        session_commands.manager.create_session(
            name="auto-20250105_130000", provider="mock", model="mock-echo"
        )
        session_commands.manager.create_session(
            name="Manual Session", provider="mock", model="mock-echo"
        )

        # User confirms
        mock_confirm.return_value = True

        result = session_commands._delete_all_sessions(["--auto-only"])
        assert result == "Successfully deleted 2 auto-saved session(s)."

        # Verify only auto sessions deleted
        sessions = session_commands.manager.get_active_sessions(limit=10)
        assert len(sessions) == 1
        assert sessions[0].name == "Manual Session"

    @patch("coda.session.commands.Confirm.ask")
    def test_delete_all_clears_current_session(self, mock_confirm, session_commands):
        """Test that delete-all clears current session if it's being deleted."""
        # Create and set current session
        session = session_commands.manager.create_session(
            name="Current Session", provider="mock", model="mock-echo"
        )
        session_commands.current_session_id = session.id
        session_commands.current_messages = [{"role": "user", "content": "test"}]
        session_commands._has_user_message = True

        # User confirms
        mock_confirm.return_value = True

        session_commands._delete_all_sessions([])

        # Verify current session cleared
        assert session_commands.current_session_id is None
        assert session_commands.current_messages == []
        assert session_commands._has_user_message is False


class TestFirstRunNotification:
    """Test first-run notification functionality."""

    @pytest.fixture
    def temp_home(self, tmp_path):
        """Create temporary home directory."""
        home = tmp_path / "home"
        home.mkdir()
        with patch.dict(os.environ, {"HOME": str(home)}):
            yield home

    @pytest.mark.asyncio
    async def test_first_run_shows_notification(self, temp_home):
        """Test that first run shows notification."""
        console = Console(file=MagicMock())

        # Ensure marker doesn't exist
        marker = temp_home / ".local/share/coda/.first_run_complete"
        assert not marker.exists()

        # Run first-run check with auto-save enabled
        await _check_first_run(console, auto_save_enabled=True)

        # Verify notification was printed
        console.file.write.assert_called()
        output = "".join(call[0][0] for call in console.file.write.call_args_list)
        assert "Welcome to Coda!" in output
        assert "Auto-Save is ENABLED" in output
        assert "💾" in output

        # Verify marker was created
        assert marker.exists()

    @pytest.mark.asyncio
    async def test_first_run_disabled_notification(self, temp_home):
        """Test first run with auto-save disabled."""
        console = Console(file=MagicMock())

        # Run first-run check with auto-save disabled
        await _check_first_run(console, auto_save_enabled=False)

        # Verify correct notification
        output = "".join(call[0][0] for call in console.file.write.call_args_list)
        assert "Welcome to Coda!" in output
        assert "Auto-Save is DISABLED" in output
        assert "🔒" in output

    @pytest.mark.asyncio
    async def test_subsequent_run_no_notification(self, temp_home):
        """Test that subsequent runs don't show notification."""
        console = Console(file=MagicMock())

        # Create marker manually
        marker = temp_home / ".local/share/coda/.first_run_complete"
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.touch()

        # Run first-run check
        await _check_first_run(console, auto_save_enabled=True)

        # Verify no notification
        console.file.write.assert_not_called()


class TestDatabaseIndexes:
    """Test that database indexes are created properly."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    def test_indexes_created(self, temp_db_path):
        """Test that all indexes are created in the database."""
        # Create database
        db = SessionDatabase(temp_db_path)

        # Get connection to check indexes
        conn = db.engine.connect()

        # Query for indexes
        from sqlalchemy import text

        result = conn.execute(
            text("SELECT name FROM sqlite_master WHERE type='index' AND sql NOT NULL")
        )
        index_names = [row[0] for row in result]

        # Verify new indexes exist
        expected_indexes = [
            "idx_session_created",
            "idx_session_accessed",
            "idx_session_name",
            "idx_session_parent",
            "idx_session_tags_tag",
        ]

        for expected in expected_indexes:
            assert any(expected in idx for idx in index_names), f"Index {expected} not found"

        conn.close()
        db.close()
