"""Session data models using SQLAlchemy."""

from datetime import datetime
from enum import Enum
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class MessageRole(Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SessionStatus(Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


session_tags = Table(
    "session_tags",
    Base.metadata,
    Column("session_id", String, ForeignKey("sessions.id"), primary_key=True),
    Column("tag_id", String, ForeignKey("tags.id"), primary_key=True),
    Index("idx_session_tags_tag", "tag_id", "session_id"),  # For tag-based lookups
)


class Session(Base):
    """Represents a conversation session."""

    __tablename__ = "sessions"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    mode = Column(String, default="general")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    accessed_at = Column(DateTime, default=datetime.utcnow)

    # Session metadata
    status = Column(String, default=SessionStatus.ACTIVE.value)
    parent_id = Column(String, ForeignKey("sessions.id"), nullable=True)
    branch_point_message_id = Column(String, ForeignKey("messages.id"), nullable=True)

    # Configuration
    system_prompt = Column(Text)
    temperature = Column(Float)
    max_tokens = Column(Integer)
    config = Column(JSON, default=dict)

    # Statistics
    message_count = Column(Integer, default=0)
    total_tokens = Column(Integer, default=0)
    total_cost = Column(Float, default=0.0)

    # Relationships
    messages = relationship(
        "Message",
        back_populates="session",
        foreign_keys="Message.session_id",
        cascade="all, delete-orphan",
        order_by="Message.sequence",
    )
    tags = relationship("Tag", secondary=session_tags, back_populates="sessions")
    parent = relationship("Session", remote_side=[id], backref="branches")

    # Indexes
    __table_args__ = (
        Index("idx_session_updated", "updated_at"),
        Index("idx_session_status", "status"),
        Index("idx_session_provider_model", "provider", "model"),
        Index("idx_session_created", "created_at"),  # For /session last queries
        Index("idx_session_accessed", "accessed_at"),  # For access-based ordering
        Index("idx_session_name", "name"),  # For name-based lookups
        Index("idx_session_parent", "parent_id"),  # For branch navigation
    )


class Message(Base):
    """Represents a message in a session."""

    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    session_id = Column(String, ForeignKey("sessions.id"), nullable=False)
    sequence = Column(Integer, nullable=False)

    # Message content
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    model = Column(String)
    provider = Column(String)

    # Token usage
    prompt_tokens = Column(Integer)
    completion_tokens = Column(Integer)
    total_tokens = Column(Integer)
    cost = Column(Float)

    # Additional data
    message_metadata = Column(JSON, default=dict)
    tool_calls = Column(JSON)  # For Phase 5 integration
    attachments = Column(JSON)  # File references, images, etc

    # Error tracking
    error = Column(Text)
    error_type = Column(String)

    # Relationships
    session = relationship("Session", back_populates="messages", foreign_keys=[session_id])

    # Full-text search
    search_content = Column(Text)  # Preprocessed content for FTS

    # Indexes
    __table_args__ = (
        Index("idx_message_session_seq", "session_id", "sequence"),
        Index("idx_message_created", "created_at"),
        Index("idx_message_role", "role"),
    )


class Tag(Base):
    """Tags for organizing sessions."""

    __tablename__ = "tags"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    name = Column(String, unique=True, nullable=False)
    color = Column(String)  # Hex color code
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    sessions = relationship("Session", secondary=session_tags, back_populates="tags")


class Attachment(Base):
    """File attachments for messages."""

    __tablename__ = "attachments"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    message_id = Column(String, ForeignKey("messages.id"), nullable=False)
    filename = Column(String, nullable=False)
    content_type = Column(String)
    size = Column(Integer)
    path = Column(String)  # Local file path or URL
    attachment_metadata = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    message = relationship("Message", backref="attachment_records")


class SearchIndex(Base):
    """Full-text search index for sessions and messages."""

    __tablename__ = "search_index"

    id = Column(String, primary_key=True, default=lambda: str(uuid4()))
    entity_type = Column(String, nullable=False)  # 'session' or 'message'
    entity_id = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    search_metadata = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Indexes
    __table_args__ = (
        Index("idx_search_entity", "entity_type", "entity_id"),
        Index("idx_search_updated", "updated_at"),
    )
