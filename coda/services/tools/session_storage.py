"""
Tool result storage format for session integration.

This module defines how tool invocations and results are stored
in sessions for replay, search, and analytics.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .base import ToolResult


class ToolInvocationStatus(str, Enum):
    """Status of a tool invocation."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ToolInvocation(BaseModel):
    """Record of a tool invocation within a session."""

    # Unique identifier for this invocation
    invocation_id: str = Field(..., description="Unique identifier for this tool invocation")

    # Session context
    session_id: str = Field(..., description="ID of the session this invocation belongs to")
    message_id: str | None = Field(
        None, description="ID of the message that triggered this invocation"
    )

    # Tool information
    tool_name: str = Field(..., description="Name of the tool that was invoked")
    tool_server: str = Field("builtin", description="Server providing the tool")
    tool_category: str = Field(..., description="Category of the tool")

    # Invocation details
    arguments: dict[str, Any] = Field(..., description="Arguments passed to the tool")
    status: ToolInvocationStatus = Field(ToolInvocationStatus.PENDING, description="Current status")

    # Execution timing
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="When invocation was created"
    )
    started_at: datetime | None = Field(None, description="When execution started")
    completed_at: datetime | None = Field(None, description="When execution completed")

    # Results
    result: ToolResult | None = Field(None, description="Tool execution result")

    # User interaction
    user_approved: bool | None = Field(
        None, description="Whether user approved dangerous operation"
    )
    approval_prompt: str | None = Field(None, description="Prompt shown to user for approval")

    # Context and metadata
    context: dict[str, Any] = Field(
        default_factory=dict, description="Additional context information"
    )
    tags: list[str] = Field(default_factory=list, description="Tags for categorization and search")

    def duration_seconds(self) -> float | None:
        """Calculate execution duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

    def is_dangerous(self) -> bool:
        """Check if this was a dangerous tool invocation."""
        return self.user_approved is not None

    def to_search_text(self) -> str:
        """Generate searchable text for this invocation."""
        parts = [
            self.tool_name,
            self.tool_category,
            str(self.arguments),
        ]

        if self.result and self.result.result:
            parts.append(str(self.result.result))

        if self.result and self.result.error:
            parts.append(str(self.result.error))

        parts.extend(self.tags)

        return " ".join(str(part) for part in parts if part)


class SessionToolSummary(BaseModel):
    """Summary of tool usage within a session."""

    session_id: str = Field(..., description="Session identifier")

    # Tool usage statistics
    total_invocations: int = Field(0, description="Total number of tool invocations")
    successful_invocations: int = Field(0, description="Number of successful invocations")
    failed_invocations: int = Field(0, description="Number of failed invocations")
    dangerous_invocations: int = Field(0, description="Number of dangerous tool invocations")

    # Tool categories used
    categories_used: list[str] = Field(default_factory=list, description="Categories of tools used")
    tools_used: list[str] = Field(default_factory=list, description="Names of tools used")

    # Timing information
    first_invocation: datetime | None = Field(None, description="Time of first tool invocation")
    last_invocation: datetime | None = Field(None, description="Time of last tool invocation")
    total_execution_time: float = Field(0.0, description="Total execution time in seconds")

    # Most used tools
    tool_usage_count: dict[str, int] = Field(
        default_factory=dict, description="Count of each tool used"
    )

    @classmethod
    def from_invocations(
        cls, session_id: str, invocations: list[ToolInvocation]
    ) -> "SessionToolSummary":
        """Create summary from list of tool invocations."""
        if not invocations:
            return cls(session_id=session_id)

        successful = [
            inv
            for inv in invocations
            if inv.status == ToolInvocationStatus.COMPLETED and inv.result and inv.result.success
        ]
        failed = [
            inv
            for inv in invocations
            if inv.status == ToolInvocationStatus.FAILED or (inv.result and not inv.result.success)
        ]
        dangerous = [inv for inv in invocations if inv.is_dangerous()]

        categories = list(set(inv.tool_category for inv in invocations))
        tools = list(set(inv.tool_name for inv in invocations))

        tool_counts = {}
        for inv in invocations:
            tool_counts[inv.tool_name] = tool_counts.get(inv.tool_name, 0) + 1

        total_time = sum(inv.duration_seconds() or 0 for inv in invocations)

        timestamps = [inv.created_at for inv in invocations]

        return cls(
            session_id=session_id,
            total_invocations=len(invocations),
            successful_invocations=len(successful),
            failed_invocations=len(failed),
            dangerous_invocations=len(dangerous),
            categories_used=categories,
            tools_used=tools,
            first_invocation=min(timestamps) if timestamps else None,
            last_invocation=max(timestamps) if timestamps else None,
            total_execution_time=total_time,
            tool_usage_count=tool_counts,
        )


class ToolInvocationFilter(BaseModel):
    """Filter for searching tool invocations."""

    # Session filters
    session_ids: list[str] | None = Field(None, description="Filter by session IDs")

    # Tool filters
    tool_names: list[str] | None = Field(None, description="Filter by tool names")
    tool_categories: list[str] | None = Field(None, description="Filter by tool categories")
    tool_servers: list[str] | None = Field(None, description="Filter by tool servers")

    # Status filters
    statuses: list[ToolInvocationStatus] | None = Field(
        None, description="Filter by invocation status"
    )
    success_only: bool | None = Field(None, description="Only successful invocations")
    failed_only: bool | None = Field(None, description="Only failed invocations")
    dangerous_only: bool | None = Field(None, description="Only dangerous invocations")

    # Time filters
    created_after: datetime | None = Field(None, description="Filter by creation time")
    created_before: datetime | None = Field(None, description="Filter by creation time")
    duration_min: float | None = Field(None, description="Minimum execution duration in seconds")
    duration_max: float | None = Field(None, description="Maximum execution duration in seconds")

    # Content filters
    search_text: str | None = Field(None, description="Search in arguments and results")
    tags: list[str] | None = Field(None, description="Filter by tags")

    # Pagination
    limit: int | None = Field(None, description="Maximum number of results")
    offset: int | None = Field(0, description="Number of results to skip")

    def matches(self, invocation: ToolInvocation) -> bool:
        """Check if an invocation matches this filter."""
        # Session filters
        if self.session_ids and invocation.session_id not in self.session_ids:
            return False

        # Tool filters
        if self.tool_names and invocation.tool_name not in self.tool_names:
            return False
        if self.tool_categories and invocation.tool_category not in self.tool_categories:
            return False
        if self.tool_servers and invocation.tool_server not in self.tool_servers:
            return False

        # Status filters
        if self.statuses and invocation.status not in self.statuses:
            return False
        if self.success_only and (not invocation.result or not invocation.result.success):
            return False
        if self.failed_only and invocation.result and invocation.result.success:
            return False
        if self.dangerous_only and not invocation.is_dangerous():
            return False

        # Time filters
        if self.created_after and invocation.created_at < self.created_after:
            return False
        if self.created_before and invocation.created_at > self.created_before:
            return False

        duration = invocation.duration_seconds()
        if self.duration_min is not None and (duration is None or duration < self.duration_min):
            return False
        if self.duration_max is not None and (duration is None or duration > self.duration_max):
            return False

        # Content filters
        if self.search_text:
            search_text = invocation.to_search_text().lower()
            if self.search_text.lower() not in search_text:
                return False

        if self.tags:
            if not any(tag in invocation.tags for tag in self.tags):
                return False

        return True


# Database schema for session integration
TOOL_INVOCATIONS_SCHEMA = """
CREATE TABLE IF NOT EXISTS tool_invocations (
    invocation_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    message_id TEXT,
    tool_name TEXT NOT NULL,
    tool_server TEXT NOT NULL DEFAULT 'builtin',
    tool_category TEXT NOT NULL,
    arguments TEXT NOT NULL,  -- JSON
    status TEXT NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    result TEXT,  -- JSON serialized ToolResult
    user_approved BOOLEAN,
    approval_prompt TEXT,
    context TEXT,  -- JSON
    tags TEXT,  -- JSON array
    search_text TEXT,  -- Generated for FTS

    FOREIGN KEY (session_id) REFERENCES sessions(session_id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tool_invocations_session ON tool_invocations(session_id);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_tool ON tool_invocations(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_category ON tool_invocations(tool_category);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_status ON tool_invocations(status);
CREATE INDEX IF NOT EXISTS idx_tool_invocations_created ON tool_invocations(created_at);

-- Full-text search index
CREATE VIRTUAL TABLE IF NOT EXISTS tool_invocations_fts USING fts5(
    invocation_id UNINDEXED,
    search_text,
    content='tool_invocations',
    content_rowid='rowid'
);

-- Triggers to keep FTS table in sync
CREATE TRIGGER IF NOT EXISTS tool_invocations_fts_insert AFTER INSERT ON tool_invocations
BEGIN
    INSERT INTO tool_invocations_fts(invocation_id, search_text)
    VALUES (new.invocation_id, new.search_text);
END;

CREATE TRIGGER IF NOT EXISTS tool_invocations_fts_update AFTER UPDATE ON tool_invocations
BEGIN
    UPDATE tool_invocations_fts
    SET search_text = new.search_text
    WHERE invocation_id = new.invocation_id;
END;

CREATE TRIGGER IF NOT EXISTS tool_invocations_fts_delete AFTER DELETE ON tool_invocations
BEGIN
    DELETE FROM tool_invocations_fts WHERE invocation_id = old.invocation_id;
END;
"""


def create_tool_invocation(
    session_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    tool_category: str,
    message_id: str | None = None,
    tool_server: str = "builtin",
    context: dict[str, Any] | None = None,
    tags: list[str] | None = None,
) -> ToolInvocation:
    """Create a new tool invocation record."""
    import uuid

    return ToolInvocation(
        invocation_id=str(uuid.uuid4()),
        session_id=session_id,
        message_id=message_id,
        tool_name=tool_name,
        tool_server=tool_server,
        tool_category=tool_category,
        arguments=arguments,
        context=context or {},
        tags=tags or [],
    )


def update_invocation_result(
    invocation: ToolInvocation,
    result: ToolResult,
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
) -> ToolInvocation:
    """Update a tool invocation with execution results."""
    invocation.result = result
    invocation.status = (
        ToolInvocationStatus.COMPLETED if result.success else ToolInvocationStatus.FAILED
    )

    if started_at:
        invocation.started_at = started_at
    if completed_at:
        invocation.completed_at = completed_at
    elif not invocation.completed_at:
        invocation.completed_at = datetime.utcnow()

    return invocation


# Future integration points for session management
class ToolSessionInterface:
    """Interface for integrating tools with session management."""

    async def log_tool_invocation(self, invocation: ToolInvocation) -> None:
        """Log a tool invocation to the session."""
        pass

    async def update_tool_result(self, invocation_id: str, result: ToolResult) -> None:
        """Update tool invocation with result."""
        pass

    async def search_tool_invocations(self, filter: ToolInvocationFilter) -> list[ToolInvocation]:
        """Search tool invocations."""
        pass

    async def get_session_tool_summary(self, session_id: str) -> SessionToolSummary:
        """Get tool usage summary for a session."""
        pass
