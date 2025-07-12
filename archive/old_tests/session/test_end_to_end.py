"""End-to-end tests demonstrating complete session functionality."""

import tempfile
from pathlib import Path

import pytest

from coda.providers import Message, MockProvider, Role
from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestSessionEndToEnd:
    """End-to-end tests for session management functionality."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    def test_complete_session_lifecycle_with_conversation_continuity(self, temp_db_path):
        """
        Test the complete session lifecycle including the key fix:
        conversation continuity after loading sessions.

        This test demonstrates that the original issue is resolved:
        - Save conversation
        - Clear conversation (AI loses memory)
        - Load conversation (AI regains memory)
        - Continue conversation naturally
        """
        # Initialize components
        db = SessionDatabase(temp_db_path)
        manager = SessionManager(db)
        commands = SessionCommands(manager)
        provider = MockProvider()

        try:
            # === STEP 1: Create conversation ===
            print("\n🎬 STEP 1: Creating conversation about Python")

            # Simulate CLI conversation state
            cli_messages = []

            # User asks about Python
            user_msg1 = Message(role=Role.USER, content="What is Python?")
            cli_messages.append(user_msg1)

            # AI responds (using full conversation context)
            ai_response1 = provider.chat(cli_messages, "mock-echo")
            assistant_msg1 = Message(role=Role.ASSISTANT, content=ai_response1)
            cli_messages.append(assistant_msg1)

            # User asks about decorators
            user_msg2 = Message(role=Role.USER, content="Tell me about Python decorators")
            cli_messages.append(user_msg2)

            # AI responds with context
            ai_response2 = provider.chat(cli_messages, "mock-echo")
            assistant_msg2 = Message(role=Role.ASSISTANT, content=ai_response2)
            cli_messages.append(assistant_msg2)

            print(f"  Created conversation with {len(cli_messages)} messages")
            print("  AI knows about: Python, decorators")

            # Track in session commands
            commands.add_message("user", user_msg1.content, {"provider": "mock"})
            commands.add_message("assistant", ai_response1, {"provider": "mock"})
            commands.add_message("user", user_msg2.content, {"provider": "mock"})
            commands.add_message("assistant", ai_response2, {"provider": "mock"})

            # === STEP 2: Save session ===
            print("\n💾 STEP 2: Saving session to database")

            session = manager.create_session(
                name="Python Tutorial",
                provider="mock",
                model="mock-echo",
                description="Testing conversation continuity",
            )

            # Save all messages to database
            for msg_data in commands.current_messages:
                manager.add_message(
                    session_id=session.id,
                    role=msg_data["role"],
                    content=msg_data["content"],
                    metadata=msg_data.get("metadata", {}),
                    provider=msg_data["metadata"].get("provider"),
                    model=msg_data["metadata"].get("model"),
                )

            commands.current_session_id = session.id
            print(f"  Session saved: {session.name} (ID: {session.id[:8]}...)")

            # === STEP 3: Clear conversation (lose memory) ===
            print("\n🧹 STEP 3: Clearing conversation (AI loses memory)")

            # Clear everything
            cli_messages.clear()
            commands.clear_conversation()

            # Test that AI has no memory
            test_msg = Message(role=Role.USER, content="What were we discussing about decorators?")
            no_memory_response = provider.chat([test_msg], "mock-echo")

            has_memory = any(
                word in no_memory_response.content.lower() for word in ["python", "decorator"]
            )
            assert not has_memory, (
                f"AI should have no memory after clear: {no_memory_response.content}"
            )

            print(f"  ✓ AI has no memory: '{no_memory_response.content[:50]}...'")

            # === STEP 4: Load session (restore memory) ===
            print("\n📂 STEP 4: Loading session (AI regains memory)")

            # Load session (simulating the CLI integration)
            manager.get_session(session.id)
            messages_from_db = manager.get_messages(session.id)

            # Convert to CLI format and restore
            commands.current_messages = []
            for msg in messages_from_db:
                commands.current_messages.append(
                    {
                        "role": msg.role,
                        "content": msg.content,
                        "metadata": {"provider": msg.provider, "model": msg.model},
                    }
                )

            commands.current_session_id = session.id
            commands._messages_loaded = True

            # Get messages for CLI (this is the key fix)
            restored_messages = commands.get_loaded_messages_for_cli()
            cli_messages.clear()
            cli_messages.extend(restored_messages)

            print(f"  ✓ Restored {len(cli_messages)} messages to CLI")

            # === STEP 5: Test memory restoration ===
            print("\n🧠 STEP 5: Testing AI memory restoration")

            # Ask about previous conversation
            memory_test = Message(
                role=Role.USER, content="What were we discussing about decorators?"
            )
            cli_messages.append(memory_test)

            # AI should now remember the context
            memory_response = provider.chat(cli_messages, "mock-echo")

            has_context = any(
                word in memory_response.content.lower()
                for word in ["python", "decorator", "function"]
            )
            assert has_context, f"AI should remember context after load: {memory_response.content}"

            print(f"  ✓ AI remembers context: '{memory_response.content[:50]}...'")

            # === STEP 6: Continue conversation naturally ===
            print("\n💬 STEP 6: Continuing conversation naturally")

            # Remove test message, add AI response
            cli_messages.pop()
            cli_messages.append(Message(role=Role.ASSISTANT, content=memory_response.content))

            # Ask follow-up question
            followup = Message(role=Role.USER, content="Can you show me a decorator example?")
            cli_messages.append(followup)

            followup_response = provider.chat(cli_messages, "mock-echo")

            # Should continue conversation about decorators
            continues_topic = any(
                word in followup_response.content.lower() for word in ["decorator", "python", "@"]
            )
            assert continues_topic, f"Should continue decorator topic: {followup_response.content}"

            print(f"  ✓ Conversation continues: '{followup_response.content[:50]}...'")

            # === STEP 7: Verify session integrity ===
            print("\n🔍 STEP 7: Verifying session integrity")

            # Check session data
            saved_messages = manager.get_messages(session.id)
            assert len(saved_messages) == 4, "Should have 4 saved messages"

            # Check export functionality
            json_export = manager.export_session(session.id, "json")
            assert "Python" in json_export and "decorator" in json_export

            # Check search functionality
            search_results = manager.search_sessions("decorator")
            assert len(search_results) >= 1, "Should find at least one session in search"
            # Verify our named session is in the results
            named_session_found = any(
                session.name == "Python Tutorial" for session, _ in search_results
            )
            assert named_session_found, "Should find our named session in search results"

            print("  ✓ Session integrity verified")

            print("\n🎉 SUCCESS: Complete session lifecycle with conversation continuity!")
            print("     The original issue has been resolved:")
            print("     ✓ Sessions save correctly")
            print("     ✓ Conversations clear completely")
            print("     ✓ Sessions load with full context restoration")
            print("     ✓ AI remembers previous conversations")
            print("     ✓ Conversations continue naturally")

            return True

        finally:
            db.close()

    def test_session_branching_preserves_context(self, temp_db_path):
        """Test that session branching maintains conversation context."""
        db = SessionDatabase(temp_db_path)
        manager = SessionManager(db)
        provider = MockProvider()

        try:
            # Create original session
            session = manager.create_session("Original", "mock", "mock-echo")

            # Add conversation
            manager.add_message(session.id, "user", "What is Python?")
            msg1_response = manager.add_message(
                session.id, "assistant", "Python is a programming language"
            )
            manager.add_message(session.id, "user", "What about JavaScript?")
            manager.add_message(session.id, "assistant", "JavaScript is for web development")

            # Create branch from first answer (to include both Q&A)
            branch = manager.create_session(
                "Python Focus",
                "mock",
                "mock-echo",
                parent_id=session.id,
                branch_point_message_id=msg1_response.id,
            )

            # Get branch context
            context, _ = manager.get_session_context(branch.id)
            assert len(context) == 2  # Up to branch point

            # Test AI context in branch
            messages = [Message(role=Role(msg["role"]), content=msg["content"]) for msg in context]
            messages.append(Message(role=Role.USER, content="Tell me more about Python decorators"))

            response = provider.chat(messages, "mock-echo")

            # Should focus on Python (not JavaScript)
            assert "python" in response.content.lower()
            assert "javascript" not in response.content.lower()

        finally:
            db.close()

    def test_mock_provider_conversation_patterns(self, temp_db_path):
        """Test mock provider's conversation awareness patterns."""
        provider = MockProvider()

        # Test topic recognition
        messages = [Message(role=Role.USER, content="Tell me about Python")]
        response = provider.chat(messages, "mock-echo")
        assert "python" in response.content.lower() and "programming" in response.content.lower()

        # Test memory questions
        conversation = [
            Message(role=Role.USER, content="What is Python?"),
            Message(role=Role.ASSISTANT, content="Python is a language"),
            Message(role=Role.USER, content="What about decorators?"),
            Message(role=Role.ASSISTANT, content="Decorators modify functions"),
            Message(role=Role.USER, content="What were we discussing?"),
        ]

        memory_response = provider.chat(conversation, "mock-echo")
        assert any(word in memory_response.content.lower() for word in ["python", "decorator"])

        # Test context building
        assert provider.conversation_history == conversation
