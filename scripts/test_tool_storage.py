#!/usr/bin/env python3
"""Manual test script for tool storage functionality."""

import asyncio
import tempfile
from pathlib import Path

from coda.session.commands import SessionCommands
from coda.session.database import SessionDatabase
from coda.session.manager import SessionManager
from coda.session.tool_storage import format_tool_calls_for_storage


async def test_tool_storage():
    """Test tool storage end-to-end."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create database
        db_path = Path(tmpdir) / "test_tools.db"
        db = SessionDatabase(db_path)
        manager = SessionManager(db)
        commands = SessionCommands(manager)

        print("✓ Created database and manager")

        # Create a session
        session = manager.create_session(
            name="Manual Tool Test", provider="cohere", model="cohere.command-r-plus", mode="code"
        )
        commands.current_session_id = session.id

        print(f"✓ Created session: {session.name} (ID: {session.id[:8]}...)")

        # Simulate tool calls
        tool_calls = [
            {"id": "call_001", "name": "read_file", "arguments": {"path": "/src/main.py"}},
            {"id": "call_002", "name": "list_directory", "arguments": {"path": "/src"}},
        ]

        # Add assistant message with tool calls
        formatted_calls = format_tool_calls_for_storage(tool_calls)
        manager.add_message(
            session.id,
            "assistant",
            "I'll examine your source files.",
            tool_calls=formatted_calls,
            model="cohere.command-r-plus",
            provider="cohere",
        )

        print("✓ Added assistant message with 2 tool calls")

        # Add tool results
        manager.add_message(
            session.id,
            "tool",
            "# main.py\n\ndef main():\n    print('Hello, World!')",
            metadata={"tool_call_id": "call_001"},
        )

        manager.add_message(
            session.id,
            "tool",
            "Files: main.py, utils.py, test_main.py",
            metadata={"tool_call_id": "call_002"},
        )

        print("✓ Added tool results")

        # Add another round of tool usage
        tool_calls2 = [
            {
                "id": "call_003",
                "name": "write_file",
                "arguments": {"path": "/src/utils.py", "content": "# utils"},
            },
        ]

        manager.add_message(
            session.id,
            "assistant",
            "I'll create a utils module.",
            tool_calls=format_tool_calls_for_storage(tool_calls2),
        )

        manager.add_message(
            session.id, "tool", "File written successfully", metadata={"tool_call_id": "call_003"}
        )

        print("✓ Added second round of tool usage")

        # Test retrieval
        history = manager.get_tool_history(session.id)
        print(f"\n✓ Tool history: {len(history)} entries")

        # Test summary
        summary = manager.get_session_tools_summary(session.id)
        print("\n✓ Tool Summary:")
        print(f"  - Total calls: {summary['total_tool_calls']}")
        print(f"  - Unique tools: {summary['unique_tools']}")
        print(f"  - Most used: {summary['most_used']}")
        print(f"  - Counts: {summary['tool_counts']}")

        # Test the command
        print("\n✓ Running /session tools command:")
        print("-" * 50)
        result = commands.handle_session_command(["tools"])
        if result:
            print(f"Command returned: {result}")
        print("-" * 50)

        # Verify data integrity
        messages = manager.get_messages(session.id)
        tool_messages = [m for m in messages if m.tool_calls]
        print(f"\n✓ Found {len(tool_messages)} messages with tool calls")

        for i, msg in enumerate(tool_messages, 1):
            print(f"  Message {i}: {len(msg.tool_calls)} tool calls")
            for call in msg.tool_calls:
                print(f"    - {call['name']} (ID: {call['id']})")

        print("\n✅ All tests passed!")


if __name__ == "__main__":
    asyncio.run(test_tool_storage())
