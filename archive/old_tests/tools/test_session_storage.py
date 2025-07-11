"""
Tests for tool session storage functionality.

This module tests the storage format and management of tool invocations
within sessions for replay, search, and analytics.
"""

import uuid
from datetime import datetime, timedelta

import pytest

from coda.providers import MockProvider
from coda.tools.session_storage import (
    SessionToolSummary,
    ToolInvocation,
    ToolInvocationFilter,
    ToolInvocationStatus,
    ToolResult,
    create_tool_invocation,
    update_invocation_result,
)


class TestToolInvocation:
    """Test ToolInvocation model."""

    def test_tool_invocation_creation(self):
        """Test creating a tool invocation."""
        invocation = ToolInvocation(
            invocation_id="test-123",
            session_id="session-456",
            tool_name="read_file",
            tool_category="filesystem",
            arguments={"filepath": "/test/file.txt"},
            status=ToolInvocationStatus.PENDING,
        )

        assert invocation.invocation_id == "test-123"
        assert invocation.session_id == "session-456"
        assert invocation.tool_name == "read_file"
        assert invocation.tool_category == "filesystem"
        assert invocation.arguments["filepath"] == "/test/file.txt"
        assert invocation.status == ToolInvocationStatus.PENDING
        assert invocation.tool_server == "builtin"

    def test_tool_invocation_duration(self):
        """Test calculating tool execution duration."""
        now = datetime.utcnow()
        invocation = ToolInvocation(
            invocation_id="test-123",
            session_id="session-456",
            tool_name="shell_execute",
            tool_category="system",
            arguments={"command": "sleep 2"},
            started_at=now,
            completed_at=now + timedelta(seconds=2.5),
        )

        duration = invocation.duration_seconds()
        assert duration == 2.5

    def test_tool_invocation_dangerous_check(self):
        """Test checking if invocation was dangerous."""
        # Non-dangerous invocation
        invocation1 = ToolInvocation(
            invocation_id="test-1",
            session_id="session-1",
            tool_name="read_file",
            tool_category="filesystem",
            arguments={},
        )
        assert not invocation1.is_dangerous()

        # Dangerous invocation with approval
        invocation2 = ToolInvocation(
            invocation_id="test-2",
            session_id="session-1",
            tool_name="shell_execute",
            tool_category="system",
            arguments={"command": "rm -rf /tmp/test"},
            user_approved=True,
            approval_prompt="This command will delete files. Continue?",
        )
        assert invocation2.is_dangerous()

    def test_tool_invocation_search_text(self):
        """Test generating searchable text from invocation."""
        result = ToolResult(success=True, result="File contents: Hello World", tool="read_file")

        invocation = ToolInvocation(
            invocation_id="test-123",
            session_id="session-456",
            tool_name="read_file",
            tool_category="filesystem",
            arguments={"filepath": "/test/hello.txt"},
            result=result,
            tags=["test", "documentation"],
        )

        search_text = invocation.to_search_text()
        assert "read_file" in search_text
        assert "filesystem" in search_text
        assert "/test/hello.txt" in search_text
        assert "Hello World" in search_text
        assert "test" in search_text
        assert "documentation" in search_text


class TestSessionToolSummary:
    """Test SessionToolSummary model."""

    def create_test_invocations(self) -> list[ToolInvocation]:
        """Create test invocations for summary testing."""
        base_time = datetime.utcnow()
        invocations = []

        # Successful file read
        inv1 = ToolInvocation(
            invocation_id="inv-1",
            session_id="session-1",
            tool_name="read_file",
            tool_category="filesystem",
            arguments={"filepath": "/test/file1.txt"},
            status=ToolInvocationStatus.COMPLETED,
            created_at=base_time,
            started_at=base_time,
            completed_at=base_time + timedelta(seconds=0.5),
            result=ToolResult(success=True, result="Content", tool="read_file"),
        )
        invocations.append(inv1)

        # Failed shell command
        inv2 = ToolInvocation(
            invocation_id="inv-2",
            session_id="session-1",
            tool_name="shell_execute",
            tool_category="system",
            arguments={"command": "invalid_command"},
            status=ToolInvocationStatus.FAILED,
            created_at=base_time + timedelta(minutes=1),
            started_at=base_time + timedelta(minutes=1),
            completed_at=base_time + timedelta(minutes=1, seconds=1),
            result=ToolResult(success=False, error="Command not found", tool="shell_execute"),
        )
        invocations.append(inv2)

        # Dangerous command with approval
        inv3 = ToolInvocation(
            invocation_id="inv-3",
            session_id="session-1",
            tool_name="shell_execute",
            tool_category="system",
            arguments={"command": "rm file.txt"},
            status=ToolInvocationStatus.COMPLETED,
            created_at=base_time + timedelta(minutes=2),
            started_at=base_time + timedelta(minutes=2),
            completed_at=base_time + timedelta(minutes=2, seconds=0.2),
            result=ToolResult(success=True, result="File deleted", tool="shell_execute"),
            user_approved=True,
        )
        invocations.append(inv3)

        # Another file operation
        inv4 = ToolInvocation(
            invocation_id="inv-4",
            session_id="session-1",
            tool_name="write_file",
            tool_category="filesystem",
            arguments={"filepath": "/test/output.txt", "content": "Test"},
            status=ToolInvocationStatus.COMPLETED,
            created_at=base_time + timedelta(minutes=3),
            started_at=base_time + timedelta(minutes=3),
            completed_at=base_time + timedelta(minutes=3, seconds=0.3),
            result=ToolResult(success=True, result="File written", tool="write_file"),
        )
        invocations.append(inv4)

        return invocations

    def test_session_summary_from_invocations(self):
        """Test creating session summary from invocations."""
        invocations = self.create_test_invocations()
        summary = SessionToolSummary.from_invocations("session-1", invocations)

        assert summary.session_id == "session-1"
        assert summary.total_invocations == 4
        assert summary.successful_invocations == 3
        assert summary.failed_invocations == 1
        assert summary.dangerous_invocations == 1

        assert "filesystem" in summary.categories_used
        assert "system" in summary.categories_used

        assert "read_file" in summary.tools_used
        assert "shell_execute" in summary.tools_used
        assert "write_file" in summary.tools_used

        assert summary.tool_usage_count["shell_execute"] == 2
        assert summary.tool_usage_count["read_file"] == 1
        assert summary.tool_usage_count["write_file"] == 1

        # Check timing
        assert summary.total_execution_time == 0.5 + 1.0 + 0.2 + 0.3

    def test_empty_session_summary(self):
        """Test creating summary with no invocations."""
        summary = SessionToolSummary.from_invocations("session-empty", [])

        assert summary.session_id == "session-empty"
        assert summary.total_invocations == 0
        assert summary.successful_invocations == 0
        assert summary.failed_invocations == 0
        assert summary.first_invocation is None
        assert summary.last_invocation is None


class TestToolInvocationFilter:
    """Test ToolInvocationFilter functionality."""

    def create_test_invocation(self, **kwargs) -> ToolInvocation:
        """Create a test invocation with custom attributes."""
        defaults = {
            "invocation_id": str(uuid.uuid4()),
            "session_id": "session-1",
            "tool_name": "test_tool",
            "tool_category": "test",
            "arguments": {},
            "status": ToolInvocationStatus.COMPLETED,
            "created_at": datetime.utcnow(),
        }
        defaults.update(kwargs)
        return ToolInvocation(**defaults)

    def test_filter_by_session(self):
        """Test filtering by session ID."""
        inv1 = self.create_test_invocation(session_id="session-1")
        inv2 = self.create_test_invocation(session_id="session-2")

        filter = ToolInvocationFilter(session_ids=["session-1"])
        assert filter.matches(inv1)
        assert not filter.matches(inv2)

    def test_filter_by_tool(self):
        """Test filtering by tool name and category."""
        inv1 = self.create_test_invocation(tool_name="read_file", tool_category="filesystem")
        inv2 = self.create_test_invocation(tool_name="shell_execute", tool_category="system")

        # Filter by name
        filter1 = ToolInvocationFilter(tool_names=["read_file"])
        assert filter1.matches(inv1)
        assert not filter1.matches(inv2)

        # Filter by category
        filter2 = ToolInvocationFilter(tool_categories=["system"])
        assert not filter2.matches(inv1)
        assert filter2.matches(inv2)

    def test_filter_by_status(self):
        """Test filtering by invocation status."""
        inv1 = self.create_test_invocation(
            status=ToolInvocationStatus.COMPLETED,
            result=ToolResult(success=True, result="OK", tool="test"),
        )
        inv2 = self.create_test_invocation(
            status=ToolInvocationStatus.FAILED,
            result=ToolResult(success=False, error="Error", tool="test"),
        )

        # Filter by status
        filter1 = ToolInvocationFilter(statuses=[ToolInvocationStatus.COMPLETED])
        assert filter1.matches(inv1)
        assert not filter1.matches(inv2)

        # Filter by success
        filter2 = ToolInvocationFilter(success_only=True)
        assert filter2.matches(inv1)
        assert not filter2.matches(inv2)

        # Filter by failure
        filter3 = ToolInvocationFilter(failed_only=True)
        assert not filter3.matches(inv1)
        assert filter3.matches(inv2)

    def test_filter_by_time(self):
        """Test filtering by time constraints."""
        now = datetime.utcnow()
        inv1 = self.create_test_invocation(
            created_at=now - timedelta(hours=2),
            started_at=now - timedelta(hours=2),
            completed_at=now - timedelta(hours=2) + timedelta(seconds=5),
        )
        inv2 = self.create_test_invocation(
            created_at=now - timedelta(minutes=30),
            started_at=now - timedelta(minutes=30),
            completed_at=now - timedelta(minutes=30) + timedelta(seconds=1),
        )

        # Filter by creation time
        filter1 = ToolInvocationFilter(created_after=now - timedelta(hours=1))
        assert not filter1.matches(inv1)
        assert filter1.matches(inv2)

        # Filter by duration
        filter2 = ToolInvocationFilter(duration_min=2.0, duration_max=10.0)
        assert filter2.matches(inv1)  # 5 seconds
        assert not filter2.matches(inv2)  # 1 second

    def test_filter_by_content(self):
        """Test filtering by content search."""
        inv1 = self.create_test_invocation(
            tool_name="read_file",
            arguments={"filepath": "/test/data.json"},
            result=ToolResult(success=True, result='{"key": "value"}', tool="read_file"),
            tags=["json", "test"],
        )
        inv2 = self.create_test_invocation(
            tool_name="write_file", arguments={"filepath": "/test/output.txt"}, tags=["output"]
        )

        # Search text filter
        filter1 = ToolInvocationFilter(search_text="json")
        assert filter1.matches(inv1)  # Found in filepath and tags
        assert not filter1.matches(inv2)

        # Tag filter
        filter2 = ToolInvocationFilter(tags=["test"])
        assert filter2.matches(inv1)
        assert not filter2.matches(inv2)

    def test_filter_dangerous_only(self):
        """Test filtering dangerous invocations only."""
        inv1 = self.create_test_invocation(tool_name="read_file", user_approved=None)
        inv2 = self.create_test_invocation(
            tool_name="shell_execute", user_approved=True, approval_prompt="Delete files?"
        )

        filter = ToolInvocationFilter(dangerous_only=True)
        assert not filter.matches(inv1)
        assert filter.matches(inv2)


class TestToolInvocationHelpers:
    """Test helper functions for tool invocations."""

    def test_create_tool_invocation(self):
        """Test creating a new tool invocation."""
        invocation = create_tool_invocation(
            session_id="session-123",
            tool_name="read_file",
            arguments={"filepath": "/test.txt"},
            tool_category="filesystem",
            message_id="msg-456",
            context={"user": "test_user"},
            tags=["test", "read"],
        )

        assert invocation.session_id == "session-123"
        assert invocation.tool_name == "read_file"
        assert invocation.arguments["filepath"] == "/test.txt"
        assert invocation.tool_category == "filesystem"
        assert invocation.message_id == "msg-456"
        assert invocation.context["user"] == "test_user"
        assert "test" in invocation.tags
        assert invocation.status == ToolInvocationStatus.PENDING
        assert invocation.invocation_id is not None

    def test_update_invocation_result(self):
        """Test updating invocation with result."""
        invocation = create_tool_invocation(
            session_id="session-123",
            tool_name="read_file",
            arguments={"filepath": "/test.txt"},
            tool_category="filesystem",
        )

        start_time = datetime.utcnow()
        end_time = start_time + timedelta(seconds=1)

        result = ToolResult(
            success=True, result="File contents", tool="read_file", metadata={"size": 1024}
        )

        updated = update_invocation_result(
            invocation, result, started_at=start_time, completed_at=end_time
        )

        assert updated.result == result
        assert updated.status == ToolInvocationStatus.COMPLETED
        assert updated.started_at == start_time
        assert updated.completed_at == end_time
        assert updated.duration_seconds() == 1.0

    def test_update_invocation_with_failure(self):
        """Test updating invocation with failed result."""
        invocation = create_tool_invocation(
            session_id="session-123",
            tool_name="shell_execute",
            arguments={"command": "invalid"},
            tool_category="system",
        )

        result = ToolResult(success=False, error="Command not found", tool="shell_execute")

        updated = update_invocation_result(invocation, result)

        assert updated.result == result
        assert updated.status == ToolInvocationStatus.FAILED
        assert updated.completed_at is not None


class TestToolSessionIntegration:
    """Test integration with session management."""

    @pytest.fixture
    def mock_provider(self):
        """Create a MockProvider instance."""
        return MockProvider()

    @pytest.mark.asyncio
    async def test_tool_invocation_with_mock_provider(self, mock_provider):
        """Test tool invocations work with MockProvider context."""
        # Create invocation
        invocation = create_tool_invocation(
            session_id="test-session",
            tool_name="get_current_time",
            arguments={},
            tool_category="system",
        )

        # Simulate tool execution
        from coda.tools import execute_tool

        result = await execute_tool("get_current_time", {})

        # Update invocation with result
        updated = update_invocation_result(invocation, result)

        assert updated.status == ToolInvocationStatus.COMPLETED
        assert updated.result.success
        assert "Current time" in updated.result.result

    def test_session_summary_statistics(self):
        """Test calculating comprehensive session statistics."""
        invocations = []
        base_time = datetime.utcnow()

        # Create varied invocations
        for i in range(10):
            tool_name = ["read_file", "write_file", "shell_execute"][i % 3]
            category = "filesystem" if "file" in tool_name else "system"
            success = i % 4 != 0  # Every 4th fails

            inv = ToolInvocation(
                invocation_id=f"inv-{i}",
                session_id="session-stats",
                tool_name=tool_name,
                tool_category=category,
                arguments={"test": i},
                status=ToolInvocationStatus.COMPLETED if success else ToolInvocationStatus.FAILED,
                created_at=base_time + timedelta(minutes=i),
                started_at=base_time + timedelta(minutes=i),
                completed_at=base_time + timedelta(minutes=i, seconds=i * 0.5),
                result=ToolResult(
                    success=success,
                    result="OK" if success else None,
                    error=None if success else "Failed",
                    tool=tool_name,
                ),
                user_approved=True if tool_name == "shell_execute" and i % 2 == 0 else None,
            )
            invocations.append(inv)

        summary = SessionToolSummary.from_invocations("session-stats", invocations)

        assert summary.total_invocations == 10
        assert summary.successful_invocations == 7  # 75% success rate
        assert summary.failed_invocations == 3
        assert summary.dangerous_invocations == 2  # shell_execute with approval

        # Check tool distribution
        assert summary.tool_usage_count["read_file"] == 4
        assert summary.tool_usage_count["write_file"] == 3
        assert summary.tool_usage_count["shell_execute"] == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
