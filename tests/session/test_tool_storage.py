"""Test tool call storage in sessions."""

import pytest

from coda.session.database import SessionDatabase
from coda.session.manager import SessionManager
from coda.session.tool_storage import format_tool_calls_for_storage, format_tool_result_for_storage


class TestToolStorage:
    """Test tool storage functionality."""

    @pytest.fixture
    def session_manager(self, tmp_path):
        """Create a test session manager."""
        db_path = tmp_path / "test_tools.db"
        db = SessionDatabase(db_path)
        return SessionManager(db)

    def test_format_tool_calls_object(self):
        """Test formatting tool calls from objects."""

        # Mock tool call object
        class MockToolCall:
            def __init__(self, id, name, arguments):
                self.id = id
                self.name = name
                self.arguments = arguments

        tool_calls = [
            MockToolCall("call1", "read_file", {"path": "/test.txt"}),
            MockToolCall("call2", "write_file", {"path": "/out.txt", "content": "data"}),
        ]

        formatted = format_tool_calls_for_storage(tool_calls)

        assert len(formatted) == 2
        assert formatted[0] == {
            "id": "call1",
            "name": "read_file",
            "arguments": {"path": "/test.txt"},
        }
        assert formatted[1] == {
            "id": "call2",
            "name": "write_file",
            "arguments": {"path": "/out.txt", "content": "data"},
        }

    def test_format_tool_calls_dict(self):
        """Test formatting tool calls from dictionaries."""
        tool_calls = [
            {"id": "call1", "name": "search", "arguments": {"query": "test"}},
            {"id": "call2", "name": "fetch", "arguments": {"url": "http://example.com"}},
        ]

        formatted = format_tool_calls_for_storage(tool_calls)

        assert formatted == tool_calls

    def test_format_tool_result(self):
        """Test formatting tool results."""

        # Object result
        class MockResult:
            def __init__(self, tool_call_id, content, is_error=False):
                self.tool_call_id = tool_call_id
                self.content = content
                self.is_error = is_error

        result = MockResult("call1", "File content here", False)
        formatted = format_tool_result_for_storage(result)

        assert formatted == {
            "tool_call_id": "call1",
            "content": "File content here",
            "is_error": False,
        }

        # Dict result
        dict_result = {"tool_call_id": "call2", "content": "Error occurred", "is_error": True}
        formatted = format_tool_result_for_storage(dict_result)
        assert formatted == dict_result

    def test_store_tool_calls_in_session(self, session_manager):
        """Test storing tool calls in a session."""
        # Create session
        session = session_manager.create_session(
            name="Tool Test Session",
            provider="test",
            model="test-model",
            mode="code",
        )

        # Add user message
        session_manager.add_message(
            session_id=session.id,
            role="user",
            content="Read the README file",
        )

        # Add assistant message with tool calls
        tool_calls = [
            {
                "id": "tc_001",
                "name": "read_file",
                "arguments": {"path": "README.md"},
            }
        ]
        session_manager.add_message(
            session_id=session.id,
            role="assistant",
            content="I'll read the README file for you.",
            tool_calls=tool_calls,
        )

        # Add tool result
        session_manager.add_message(
            session_id=session.id,
            role="tool",
            content="# Project README\n\nThis is the content of the README file.",
            metadata={"tool_call_id": "tc_001"},
        )

        # Add final assistant response
        session_manager.add_message(
            session_id=session.id,
            role="assistant",
            content="The README file contains a project description.",
        )

        # Verify messages were stored
        messages = session_manager.get_messages(session.id)
        assert len(messages) == 4

        # Check tool call message
        tool_msg = messages[1]
        assert tool_msg.role == "assistant"
        assert tool_msg.tool_calls == tool_calls

        # Check tool result message
        result_msg = messages[2]
        assert result_msg.role == "tool"
        assert result_msg.message_metadata["tool_call_id"] == "tc_001"

    def test_get_tool_history(self, session_manager):
        """Test retrieving tool history."""
        # Create session with tool interactions
        session = session_manager.create_session(
            name="Tool History Test",
            provider="test",
            model="test-model",
        )

        # Add messages with tools
        session_manager.add_message(session.id, "user", "Analyze these files")

        session_manager.add_message(
            session.id,
            "assistant",
            "I'll analyze the files.",
            tool_calls=[
                {"id": "t1", "name": "list_files", "arguments": {"path": "."}},
                {"id": "t2", "name": "read_file", "arguments": {"path": "main.py"}},
            ],
        )

        session_manager.add_message(
            session.id, "tool", "file1.py\nfile2.py\nmain.py", metadata={"tool_call_id": "t1"}
        )

        session_manager.add_message(
            session.id, "tool", "def main():\n    pass", metadata={"tool_call_id": "t2"}
        )

        # Get tool history
        history = session_manager.get_tool_history(session.id)

        assert len(history) == 3  # 1 call message + 2 result messages
        assert history[0]["type"] == "call"
        assert len(history[0]["tool_calls"]) == 2
        assert history[1]["type"] == "result"
        assert history[2]["type"] == "result"

    def test_get_session_tools_summary(self, session_manager):
        """Test getting tool usage summary."""
        session = session_manager.create_session(
            name="Tool Summary Test",
            provider="test",
            model="test-model",
        )

        # Add multiple tool uses
        for i in range(3):
            session_manager.add_message(
                session.id,
                "assistant",
                f"Using tools {i}",
                tool_calls=[{"id": f"r{i}", "name": "read_file", "arguments": {}}],
            )

        session_manager.add_message(
            session.id,
            "assistant",
            "Writing file",
            tool_calls=[{"id": "w1", "name": "write_file", "arguments": {}}],
        )

        session_manager.add_message(
            session.id,
            "assistant",
            "Another read",
            tool_calls=[{"id": "r3", "name": "read_file", "arguments": {}}],
        )

        # Get summary
        summary = session_manager.get_session_tools_summary(session.id)

        assert summary["total_tool_calls"] == 5
        assert summary["unique_tools"] == 2
        assert summary["tool_counts"]["read_file"] == 4
        assert summary["tool_counts"]["write_file"] == 1
        assert summary["most_used"] == "read_file"
