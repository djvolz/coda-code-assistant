"""Integration tests for auto-save functionality with MockProvider."""

import tempfile
from pathlib import Path

import pytest

from coda.providers import Message, MockProvider, Role
from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestAutoSaveWithMockProvider:
    """Test auto-save functionality with MockProvider conversations."""

    @pytest.fixture
    def temp_db_path(self):
        """Create temporary database path."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)
        yield db_path
        if db_path.exists():
            db_path.unlink()

    @pytest.fixture
    def session_manager(self, temp_db_path):
        """Create session manager with temporary database."""
        db = SessionDatabase(temp_db_path)
        manager = SessionManager(db)
        yield manager
        db.close()

    @pytest.fixture
    def mock_provider(self):
        """Create mock provider for testing."""
        return MockProvider()

    @pytest.fixture
    def session_commands(self, session_manager):
        """Create session commands instance."""
        return SessionCommands(session_manager)

    def test_auto_save_with_python_conversation(self, session_commands, mock_provider):
        """Test auto-save triggers with a Python programming conversation."""
        # Simulate user asking about Python
        session_commands.add_message(
            role="user",
            content="What is Python?",
            metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
        )

        # Get MockProvider response
        messages = [Message(role=Role.USER, content="What is Python?")]
        response = mock_provider.chat(messages, "mock-echo")

        # Add assistant response
        session_commands.add_message(
            role="assistant",
            content=response,
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Verify auto-save triggered
        assert session_commands.current_session_id is not None

        # Verify conversation was saved correctly
        session = session_commands.manager.get_session(session_commands.current_session_id)
        assert session.name.startswith("auto-")

        messages = session_commands.manager.get_messages(session.id)
        assert len(messages) == 2
        assert "high-level programming language" in messages[1].content

    def test_auto_save_preserves_conversation_memory(self, session_commands, mock_provider):
        """Test that auto-saved sessions preserve conversation context."""
        # Build a conversation about decorators
        conversation_flow = [
            ("Tell me about decorators", "user"),
            (None, "assistant"),  # Will be filled by MockProvider
            ("What is Python?", "user"),
            (None, "assistant"),  # Will be filled by MockProvider
            ("What were we discussing?", "user"),
            (None, "assistant"),  # Will be filled by MockProvider
        ]

        mock_messages = []

        for content, role in conversation_flow:
            if role == "user":
                # Add user message
                session_commands.add_message(
                    role="user",
                    content=content,
                    metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
                )
                mock_messages.append(Message(role=Role.USER, content=content))
            else:
                # Get MockProvider response
                response = mock_provider.chat(mock_messages, "mock-echo")

                # Add assistant response
                session_commands.add_message(
                    role="assistant",
                    content=response,
                    metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
                )
                mock_messages.append(Message(role=Role.ASSISTANT, content=response))

        # Verify session was auto-saved
        assert session_commands.current_session_id is not None

        # Load the session and verify memory
        saved_messages = session_commands.manager.get_messages(session_commands.current_session_id)
        assert len(saved_messages) == 6

        # The final response should mention previous topics
        final_response = saved_messages[-1].content
        assert "decorator" in final_response.lower() or "python" in final_response.lower()

    def test_auto_save_with_different_modes(self, session_commands, mock_provider):
        """Test auto-save works with different developer modes."""
        modes = ["code", "debug", "explain"]

        for mode in modes:
            # Reset for each mode test
            session_commands.current_session_id = None
            session_commands.current_messages = []
            session_commands._has_user_message = False

            # Add messages
            session_commands.add_message(
                role="user",
                content="Hello",
                metadata={"mode": mode, "provider": "mock", "model": "mock-echo"},
            )

            # Get MockProvider response
            messages = [Message(role=Role.USER, content="Hello")]
            response = mock_provider.chat(messages, "mock-echo")

            session_commands.add_message(
                role="assistant",
                content=response,
                metadata={"provider": "mock", "model": "mock-echo", "mode": mode},
            )

            # Verify auto-save triggered
            assert session_commands.current_session_id is not None

            # Verify mode was saved
            session = session_commands.manager.get_session(session_commands.current_session_id)
            assert session.mode == mode

    def test_no_auto_save_with_incomplete_exchange(self, session_commands, mock_provider):
        """Test that auto-save doesn't trigger without complete exchange."""
        # Only add user message
        session_commands.add_message(
            role="user",
            content="What is Python?",
            metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
        )

        # No auto-save should occur
        assert session_commands.current_session_id is None

        # Add another user message (still no assistant)
        session_commands.add_message(
            role="user",
            content="Tell me more",
            metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
        )

        # Still no auto-save
        assert session_commands.current_session_id is None

    def test_session_continuity_after_auto_save(self, session_commands, mock_provider):
        """Test that conversation continues properly after auto-save."""
        # Initial exchange to trigger auto-save
        session_commands.add_message(
            role="user",
            content="What is Python?",
            metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
        )

        messages = [Message(role=Role.USER, content="What is Python?")]
        response1 = mock_provider.chat(messages, "mock-echo")

        session_commands.add_message(
            role="assistant",
            content=response1,
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Capture session ID
        session_id = session_commands.current_session_id
        assert session_id is not None

        # Continue conversation
        session_commands.add_message(
            role="user",
            content="What were we discussing?",
            metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
        )

        # Build full message history for MockProvider
        messages = [
            Message(role=Role.USER, content="What is Python?"),
            Message(role=Role.ASSISTANT, content=response1),
            Message(role=Role.USER, content="What were we discussing?"),
        ]
        response2 = mock_provider.chat(messages, "mock-echo")

        session_commands.add_message(
            role="assistant",
            content=response2,
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Verify same session is used
        assert session_commands.current_session_id == session_id

        # Verify memory response
        assert "Python" in response2

        # Verify all messages saved
        saved_messages = session_commands.manager.get_messages(session_id)
        assert len(saved_messages) == 4

    @pytest.mark.asyncio
    async def test_streaming_with_auto_save(self, session_commands, mock_provider):
        """Test auto-save works with streaming responses."""
        # Add user message
        session_commands.add_message(
            role="user",
            content="Hello",
            metadata={"mode": "general", "provider": "mock", "model": "mock-echo"},
        )

        # Simulate streaming response collection
        messages = [Message(role=Role.USER, content="Hello")]
        chunks = []
        async for chunk in mock_provider.achat_stream(messages, "mock-echo"):
            chunks.append(chunk.content)

        full_response = "".join(chunks)

        # Add complete response
        session_commands.add_message(
            role="assistant",
            content=full_response,
            metadata={"provider": "mock", "model": "mock-echo", "mode": "general"},
        )

        # Verify auto-save
        assert session_commands.current_session_id is not None

        # Verify correct response saved
        saved_messages = session_commands.manager.get_messages(session_commands.current_session_id)
        assert saved_messages[1].content == "Hello! How can I help you today?"
