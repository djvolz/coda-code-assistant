"""Tests for session manager functionality."""

import json
import tempfile
from pathlib import Path

import pytest

from coda.base.session import SessionDatabase, SessionManager
from coda.base.session.models import SessionStatus


class TestSessionManager:
    """Test session management operations."""

    @pytest.fixture
    def manager(self):
        """Create a session manager with temporary database."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = SessionDatabase(db_path)
        manager = SessionManager(db)
        yield manager

        # Cleanup
        db.close()
        db_path.unlink()

    def test_create_session(self, manager):
        """Test creating a new session."""
        session = manager.create_session(
            name="Test Session",
            provider="oci_genai",
            model="cohere.command-r-plus",
            mode="code",
            description="Test session for unit tests",
        )

        assert session.name == "Test Session"
        assert session.provider == "oci_genai"
        assert session.model == "cohere.command-r-plus"
        assert session.mode == "code"
        assert session.description == "Test session for unit tests"
        assert session.status == SessionStatus.ACTIVE.value

    def test_add_message(self, manager):
        """Test adding messages to a session."""
        # Create session
        session = manager.create_session(name="Message Test", provider="test", model="test-model")

        # Add messages
        msg1 = manager.add_message(
            session_id=session.id,
            role="user",
            content="What is Python?",
            metadata={"timestamp": "2024-01-01T10:00:00"},
        )

        msg2 = manager.add_message(
            session_id=session.id,
            role="assistant",
            content="Python is a high-level programming language.",
            model="test-model",
            provider="test",
            token_usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            cost=0.001,
        )

        # Verify messages
        assert msg1.sequence == 1
        assert msg2.sequence == 2
        assert msg2.total_tokens == 30
        assert msg2.cost == 0.001

        # Verify session updated
        updated_session = manager.get_session(session.id)
        assert updated_session.message_count == 2
        assert updated_session.total_tokens == 30
        assert updated_session.total_cost == 0.001

    def test_get_messages(self, manager):
        """Test retrieving messages from a session."""
        # Create session with messages
        session = manager.create_session(name="Retrieval Test", provider="test", model="test-model")

        for i in range(5):
            manager.add_message(
                session_id=session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i}",
            )

        # Get all messages
        messages = manager.get_messages(session.id)
        assert len(messages) == 5
        assert messages[0].content == "Message 0"
        assert messages[4].content == "Message 4"

        # Get limited messages
        limited = manager.get_messages(session.id, limit=3)
        assert len(limited) == 3

        # Get with offset
        offset_msgs = manager.get_messages(session.id, limit=2, offset=2)
        assert len(offset_msgs) == 2
        assert offset_msgs[0].content == "Message 2"

    def test_search_sessions(self, manager):
        """Test full-text search across sessions."""
        # Create sessions with searchable content
        session1 = manager.create_session(name="Python Tutorial", provider="test", model="test")
        manager.add_message(
            session_id=session1.id, role="user", content="How do I use decorators in Python?"
        )

        session2 = manager.create_session(name="JavaScript Guide", provider="test", model="test")
        manager.add_message(
            session_id=session2.id, role="user", content="What are arrow functions in JavaScript?"
        )

        # Search for Python
        results = manager.search_sessions("Python")
        assert len(results) == 1
        assert results[0][0].name == "Python Tutorial"

        # Search for functions
        results = manager.search_sessions("functions")
        assert len(results) == 1
        assert results[0][0].name == "JavaScript Guide"

    def test_session_branching(self, manager):
        """Test creating session branches."""
        # Create parent session with messages
        parent = manager.create_session(name="Parent Session", provider="test", model="test")

        manager.add_message(session_id=parent.id, role="user", content="First message")
        msg2 = manager.add_message(session_id=parent.id, role="assistant", content="First response")
        manager.add_message(session_id=parent.id, role="user", content="Second message")

        # Create branch from second message
        branch = manager.create_session(
            name="Branch Session",
            provider="test",
            model="test",
            parent_id=parent.id,
            branch_point_message_id=msg2.id,
        )

        # Verify branch has messages up to branch point
        branch_messages = manager.get_messages(branch.id)
        assert len(branch_messages) == 2
        assert branch_messages[0].content == "First message"
        assert branch_messages[1].content == "First response"

    def test_delete_session(self, manager):
        """Test session deletion."""
        # Create session
        session = manager.create_session(name="Delete Test", provider="test", model="test")
        session_id = session.id

        # Soft delete
        manager.delete_session(session_id, hard_delete=False)
        deleted = manager.get_session(session_id)
        assert deleted.status == SessionStatus.DELETED.value

        # Hard delete
        manager.delete_session(session_id, hard_delete=True)
        assert manager.get_session(session_id) is None

    def test_archive_session(self, manager):
        """Test session archival."""
        session = manager.create_session(name="Archive Test", provider="test", model="test")

        manager.archive_session(session.id)
        archived = manager.get_session(session.id)
        assert archived.status == SessionStatus.ARCHIVED.value

    def test_update_session(self, manager):
        """Test updating session metadata."""
        session = manager.create_session(name="Update Test", provider="test", model="test")

        # Update with tags
        manager.update_session(
            session.id,
            name="Updated Name",
            description="New description",
            tags=["python", "testing"],
            config={"theme": "dark"},
        )

        updated = manager.get_session(session.id)
        assert updated.name == "Updated Name"
        assert updated.description == "New description"
        assert len(updated.tags) == 2
        assert {tag.name for tag in updated.tags} == {"python", "testing"}
        assert updated.config["theme"] == "dark"

    def test_get_session_context(self, manager):
        """Test getting session context with windowing."""
        session = manager.create_session(
            name="Context Test", provider="test", model="gpt-3.5-turbo"
        )

        # Add many messages
        for i in range(20):
            manager.add_message(
                session_id=session.id,
                role="user" if i % 2 == 0 else "assistant",
                content=f"Message {i} " * 50,  # Make messages longer
            )

        # Get context with token limit
        context, was_truncated = manager.get_session_context(
            session.id, max_tokens=1000, model="gpt-3.5-turbo"
        )

        assert was_truncated
        assert len(context) < 20  # Should be truncated
        # Should have summary message
        assert any(
            msg["role"] == "system" and "summary" in msg["content"].lower() for msg in context
        )

    def test_export_json(self, manager):
        """Test exporting session as JSON."""
        session = manager.create_session(name="Export Test", provider="test", model="test")

        manager.add_message(session_id=session.id, role="user", content="Test message")

        # Export as JSON
        json_export = manager.export_session(session.id, format="json")
        data = json.loads(json_export)

        assert data["session"]["name"] == "Export Test"
        assert len(data["messages"]) == 1
        assert data["messages"][0]["content"] == "Test message"

    def test_export_markdown(self, manager):
        """Test exporting session as Markdown."""
        session = manager.create_session(
            name="Markdown Export", provider="test", model="test", description="Test description"
        )

        manager.add_message(session_id=session.id, role="user", content="Hello")
        manager.add_message(session_id=session.id, role="assistant", content="Hi there!")

        # Export as Markdown
        md_export = manager.export_session(session.id, format="markdown")

        assert "# Markdown Export" in md_export
        assert "Test description" in md_export
        assert "👤 User" in md_export
        assert "🤖 Assistant" in md_export
        assert "Hello" in md_export
        assert "Hi there!" in md_export

    def test_export_html(self, manager):
        """Test exporting session as HTML."""
        session = manager.create_session(name="HTML Export", provider="test", model="test")

        manager.add_message(session_id=session.id, role="user", content="Test")

        # Export as HTML
        html_export = manager.export_session(session.id, format="html")

        assert "<!DOCTYPE html>" in html_export
        assert "<title>HTML Export</title>" in html_export
        assert 'class="message user"' in html_export
        assert "Test" in html_export

    def test_get_active_sessions(self, manager):
        """Test retrieving active sessions."""
        # Create mix of sessions
        manager.create_session(name="Active 1", provider="test", model="test")
        manager.create_session(name="Active 2", provider="test", model="test")
        archived = manager.create_session(name="Archived", provider="test", model="test")

        manager.archive_session(archived.id)

        # Get active sessions
        active_sessions = manager.get_active_sessions()
        assert len(active_sessions) == 2
        assert {s.name for s in active_sessions} == {"Active 1", "Active 2"}

        # Test pagination
        page1 = manager.get_active_sessions(limit=1, offset=0)
        assert len(page1) == 1
