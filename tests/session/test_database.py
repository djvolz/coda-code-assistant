"""Tests for session database functionality."""

import tempfile
from pathlib import Path

import pytest
from sqlalchemy import text

from coda.session.database import SessionDatabase
from coda.session.models import Message, Session, Tag


class TestSessionDatabase:
    """Test session database operations."""

    @pytest.fixture
    def temp_db(self):
        """Create a temporary database for testing."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        db = SessionDatabase(db_path)
        yield db

        # Cleanup
        db.close()
        db_path.unlink()

    def test_database_creation(self, temp_db):
        """Test that database and tables are created correctly."""
        # Check that database file exists
        assert temp_db.db_path.exists()

        # Check tables exist
        with temp_db.engine.connect() as conn:
            result = conn.execute(text("SELECT name FROM sqlite_master WHERE type='table'"))
            tables = [row[0] for row in result]

            assert "sessions" in tables
            assert "messages" in tables
            assert "tags" in tables
            assert "attachments" in tables
            assert "search_index" in tables
            assert "messages_fts" in tables

    def test_session_creation(self, temp_db):
        """Test creating a session."""
        with temp_db.get_session() as db:
            session = Session(name="Test Session", provider="test_provider", model="test_model")
            db.add(session)
            db.commit()

            # Verify session was created
            saved_session = db.query(Session).filter_by(name="Test Session").first()
            assert saved_session is not None
            assert saved_session.provider == "test_provider"
            assert saved_session.model == "test_model"
            assert saved_session.message_count == 0

    def test_message_creation(self, temp_db):
        """Test creating messages."""
        with temp_db.get_session() as db:
            # Create session first
            session = Session(name="Test Session", provider="test_provider", model="test_model")
            db.add(session)
            db.commit()

            # Create messages
            msg1 = Message(session_id=session.id, sequence=1, role="user", content="Hello, world!")
            msg2 = Message(
                session_id=session.id,
                sequence=2,
                role="assistant",
                content="Hello! How can I help you?",
            )
            db.add(msg1)
            db.add(msg2)
            db.commit()

            # Verify messages
            messages = db.query(Message).filter_by(session_id=session.id).all()
            assert len(messages) == 2
            assert messages[0].content == "Hello, world!"
            assert messages[1].role == "assistant"

    def test_fts_index(self, temp_db):
        """Test full-text search functionality."""
        with temp_db.get_session() as db:
            # Create session and message
            session = Session(name="Test Session", provider="test_provider", model="test_model")
            db.add(session)
            db.commit()

            message = Message(
                session_id=session.id,
                sequence=1,
                role="user",
                content="Python programming with SQLite database",
            )
            db.add(message)
            db.commit()

            # Add to FTS index
            db.execute(
                text(
                    """
                INSERT INTO messages_fts (message_id, session_id, content, role)
                VALUES (:msg_id, :session_id, :content, :role)
            """
                ),
                {
                    "msg_id": message.id,
                    "session_id": session.id,
                    "content": message.content,
                    "role": message.role,
                },
            )
            db.commit()

            # Search
            result = db.execute(
                text(
                    """
                SELECT message_id FROM messages_fts
                WHERE messages_fts MATCH 'SQLite'
            """
                )
            ).fetchall()

            assert len(result) == 1
            assert result[0][0] == message.id

    def test_tag_relationships(self, temp_db):
        """Test tag relationships with sessions."""
        with temp_db.get_session() as db:
            # Create session and tags
            session = Session(name="Test Session", provider="test_provider", model="test_model")
            tag1 = Tag(name="python")
            tag2 = Tag(name="database")

            session.tags.append(tag1)
            session.tags.append(tag2)

            db.add(session)
            db.commit()

            # Verify relationships
            saved_session = db.query(Session).filter_by(name="Test Session").first()
            assert len(saved_session.tags) == 2
            assert {tag.name for tag in saved_session.tags} == {"python", "database"}

    def test_session_branching(self, temp_db):
        """Test session parent-child relationships."""
        with temp_db.get_session() as db:
            # Create parent session
            parent = Session(name="Parent Session", provider="test_provider", model="test_model")
            db.add(parent)
            db.commit()

            # Create branch
            branch = Session(
                name="Branch Session",
                provider="test_provider",
                model="test_model",
                parent_id=parent.id,
            )
            db.add(branch)
            db.commit()

            # Verify relationship
            saved_parent = db.query(Session).filter_by(id=parent.id).first()
            assert len(saved_parent.branches) == 1
            assert saved_parent.branches[0].name == "Branch Session"

            saved_branch = db.query(Session).filter_by(id=branch.id).first()
            assert saved_branch.parent.name == "Parent Session"

    def test_vacuum(self, temp_db):
        """Test database vacuum operation."""
        initial_size = temp_db.get_db_size()

        # Create and delete some data
        with temp_db.get_session() as db:
            for i in range(10):
                session = Session(name=f"Session {i}", provider="test", model="test")
                db.add(session)
            db.commit()

            # Delete all sessions
            db.query(Session).delete()
            db.commit()

        # Run vacuum
        temp_db.vacuum()

        # Size should be similar to initial (not much larger)
        final_size = temp_db.get_db_size()
        assert final_size < initial_size + 10000  # Allow 10KB growth

    def test_backup(self, temp_db):
        """Test database backup functionality."""
        # Create some data
        with temp_db.get_session() as db:
            session = Session(name="Backup Test", provider="test", model="test")
            db.add(session)
            db.commit()

        # Force WAL checkpoint to ensure data is written to main database
        with temp_db.engine.connect() as conn:
            conn.execute(text("PRAGMA wal_checkpoint(TRUNCATE)"))
            conn.commit()

        # Create backup
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            backup_path = Path(f.name)

        temp_db.backup(backup_path)

        # Verify backup exists and contains data
        assert backup_path.exists()

        # Open backup and check data
        backup_db = SessionDatabase(backup_path)
        with backup_db.get_session() as db:
            session = db.query(Session).filter_by(name="Backup Test").first()
            assert session is not None

        # Cleanup
        backup_db.close()
        backup_path.unlink()
