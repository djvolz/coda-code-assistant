"""SQLite database connection and initialization for session management."""

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from .constants import FTS_TABLE_NAME
from .models import Base


class SessionDatabase:
    """Manages SQLite database connections for session storage."""

    def __init__(self, db_path: Path | None = None):
        """Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Compute default path using XDG conventions
            import os
            from pathlib import Path

            from .constants import SESSION_DB

            # Use XDG_DATA_HOME if set, otherwise ~/.local/share
            xdg_data_home = os.environ.get("XDG_DATA_HOME")
            if xdg_data_home:
                data_dir = Path(xdg_data_home) / "coda"
            else:
                data_dir = Path.home() / ".local" / "share" / "coda"

            db_path = data_dir / SESSION_DB

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Create engine with connection pooling disabled for SQLite
        self.engine = create_engine(
            f"sqlite:///{self.db_path}",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )

        # Enable foreign key support and WAL mode for better concurrency
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA synchronous=NORMAL")
            cursor.close()

        # Create session factory
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine,
            expire_on_commit=False,  # Prevent objects from being expired after commit
        )

        # Initialize database
        self.init_db()

    def init_db(self):
        """Create all tables if they don't exist."""
        Base.metadata.create_all(bind=self.engine)

        # Create FTS5 virtual table for full-text search
        with self.engine.connect() as conn:
            # Check if FTS table exists
            result = conn.execute(
                text(
                    f"SELECT name FROM sqlite_master WHERE type='table' AND name='{FTS_TABLE_NAME}'"
                )
            )
            if not result.fetchone():
                conn.execute(
                    text(
                        f"""
                    CREATE VIRTUAL TABLE {FTS_TABLE_NAME} USING fts5(
                        message_id UNINDEXED,
                        session_id UNINDEXED,
                        content,
                        role UNINDEXED,
                        tokenize='porter unicode61'
                    )
                """
                    )
                )
                conn.commit()

    @contextmanager
    def get_session(self) -> DBSession:
        """Get a database session context manager.

        Yields:
            SQLAlchemy session object.
        """
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def close(self):
        """Close database connections."""
        self.engine.dispose()

    def vacuum(self):
        """Optimize database by running VACUUM."""
        with self.engine.connect() as conn:
            conn.execute(text("VACUUM"))
            conn.commit()

    def get_db_size(self) -> int:
        """Get database file size in bytes."""
        if self.db_path.exists():
            return self.db_path.stat().st_size
        return 0

    def backup(self, backup_path: Path):
        """Create a backup of the database.

        Args:
            backup_path: Path to save the backup.
        """
        import shutil

        if self.db_path.exists():
            backup_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.db_path, backup_path)

    def clear_all(self):
        """Clear all data from the database (use with caution)."""
        Base.metadata.drop_all(bind=self.engine)
        self.init_db()
