"""Simple integration test for tool call storage."""

import pytest

from coda.session.database import SessionDatabase
from coda.session.manager import SessionManager
from coda.session.tool_storage import format_tool_calls_for_storage


class TestToolStorageSimple:
    """Simple test for tool storage functionality."""

    @pytest.mark.integration
    def test_tool_storage_basic_flow(self, tmp_path):
        """Test basic tool storage flow."""
        # Create database and manager
        db_path = tmp_path / "test_tools.db"
        db = SessionDatabase(db_path)
        manager = SessionManager(db)

        # Create a session
        session = manager.create_session(
            name="Tool Test", provider="test", model="test-model", mode="code"
        )

        # Add a message with tool calls
        tool_calls = [
            {"id": "tc1", "name": "read_file", "arguments": {"path": "test.py"}},
            {
                "id": "tc2",
                "name": "write_file",
                "arguments": {"path": "out.txt", "content": "test"},
            },
        ]

        # Format tool calls for storage
        formatted_calls = format_tool_calls_for_storage(tool_calls)

        # Add message with tool calls
        manager.add_message(
            session_id=session.id,
            role="assistant",
            content="I'll help you with those files.",
            tool_calls=formatted_calls,
        )

        # Add tool results
        manager.add_message(
            session_id=session.id,
            role="tool",
            content="File content: print('hello')",
            metadata={"tool_call_id": "tc1"},
        )

        manager.add_message(
            session_id=session.id,
            role="tool",
            content="File written successfully",
            metadata={"tool_call_id": "tc2"},
        )

        # Test retrieval
        tool_history = manager.get_tool_history(session.id)
        assert len(tool_history) == 3  # 1 call message + 2 results

        # Test summary
        summary = manager.get_session_tools_summary(session.id)
        assert summary["total_tool_calls"] == 2
        assert summary["unique_tools"] == 2
        assert summary["tool_counts"]["read_file"] == 1
        assert summary["tool_counts"]["write_file"] == 1

        # Verify the tool calls were properly stored
        messages = manager.get_messages(session.id)
        tool_msg = next(msg for msg in messages if msg.tool_calls)
        assert len(tool_msg.tool_calls) == 2
        assert tool_msg.tool_calls[0]["name"] == "read_file"
        assert tool_msg.tool_calls[1]["name"] == "write_file"

    @pytest.mark.integration
    def test_tool_storage_with_objects(self, tmp_path):
        """Test tool storage with object-based tool calls."""
        from types import SimpleNamespace

        # Create database and manager
        db_path = tmp_path / "test_tools_obj.db"
        db = SessionDatabase(db_path)
        manager = SessionManager(db)

        # Create a session
        session = manager.create_session(
            name="Tool Object Test", provider="test", model="test-model"
        )

        # Create tool call objects
        tool_calls = [
            SimpleNamespace(id="obj_tc1", name="list_files", arguments={"directory": "/home/user"})
        ]

        # Format and store
        formatted_calls = format_tool_calls_for_storage(tool_calls)

        manager.add_message(
            session_id=session.id,
            role="assistant",
            content="Listing files...",
            tool_calls=formatted_calls,
        )

        # Verify
        messages = manager.get_messages(session.id)
        tool_msg = next(msg for msg in messages if msg.tool_calls)
        assert tool_msg.tool_calls[0]["id"] == "obj_tc1"
        assert tool_msg.tool_calls[0]["name"] == "list_files"
        assert tool_msg.tool_calls[0]["arguments"]["directory"] == "/home/user"

    @pytest.mark.integration
    def test_session_tools_command_display(self, tmp_path):
        """Test the session tools command display functionality."""
        from coda.session.commands import SessionCommands

        # Create database and manager
        db_path = tmp_path / "test_tools_cmd.db"
        db = SessionDatabase(db_path)
        manager = SessionManager(db)

        # Create session commands
        commands = SessionCommands(manager)

        # Create a session with tool usage
        session = manager.create_session(
            name="Tool Command Test", provider="test", model="test-model"
        )

        commands.current_session_id = session.id

        # Add tool usage
        manager.add_message(
            session.id,
            "assistant",
            "Executing tools...",
            tool_calls=[
                {"id": "t1", "name": "search", "arguments": {"query": "test"}},
                {"id": "t2", "name": "search", "arguments": {"query": "demo"}},
                {"id": "t3", "name": "read", "arguments": {"file": "test.py"}},
            ],
        )

        # Add results
        for tid in ["t1", "t2", "t3"]:
            manager.add_message(
                session.id, "tool", f"Result for {tid}", metadata={"tool_call_id": tid}
            )

        # Test command - should not return error
        result = commands.handle_session_command(["tools"])
        assert result is None  # Success - no error message

        # Test summary data
        summary = manager.get_session_tools_summary(session.id)
        assert summary["total_tool_calls"] == 3
        assert summary["unique_tools"] == 2
        assert summary["tool_counts"]["search"] == 2
        assert summary["tool_counts"]["read"] == 1
        assert summary["most_used"] == "search"
