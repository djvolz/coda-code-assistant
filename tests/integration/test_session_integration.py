"""Integration tests for session management with mock provider."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI
from coda.providers import Message, MockProvider, Role
from coda.session import SessionCommands, SessionDatabase, SessionManager


class TestSessionIntegration:
    """Test complete session management integration."""

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
    def cli_with_sessions(self, session_manager):
        """Create CLI with session management."""
        cli = InteractiveCLI()
        cli.session_commands = SessionCommands(session_manager)
        return cli

    def test_mock_provider_basic_functionality(self, mock_provider):
        """Test that mock provider works correctly."""
        # Test basic chat
        messages = [Message(role=Role.USER, content="Hello")]
        response = mock_provider.chat(messages, "mock-echo")
        assert "Hello" in response

        # Test context awareness
        messages.append(Message(role=Role.ASSISTANT, content=response))
        messages.append(Message(role=Role.USER, content="What is Python?"))

        response2 = mock_provider.chat(messages, "mock-echo")
        assert "Python" in response2
        assert "programming language" in response2.lower()

    def test_mock_provider_conversation_memory(self, mock_provider):
        """Test mock provider remembers conversation context."""
        # Start conversation about Python
        messages = [
            Message(role=Role.USER, content="Tell me about Python"),
            Message(role=Role.ASSISTANT, content="Python is a programming language"),
            Message(role=Role.USER, content="What about decorators?"),
            Message(role=Role.ASSISTANT, content="Decorators modify functions"),
            Message(role=Role.USER, content="What were we discussing about decorators?"),
        ]

        response = mock_provider.chat(messages, "mock-echo")
        assert "decorator" in response.lower()
        assert "python" in response.lower()

    def test_session_save_and_load_complete_flow(self, session_manager, mock_provider):
        """Test complete save/load flow with actual conversation."""
        # Simulate a conversation
        session = session_manager.create_session(
            name="Python Discussion",
            provider="mock",
            model="mock-echo",
            description="Testing session save/load",
        )

        # Add conversation messages
        session_manager.add_message(
            session.id,
            "user",
            "What is Python?",
            metadata={"provider": "mock", "model": "mock-echo"},
        )
        session_manager.add_message(
            session.id,
            "assistant",
            "Python is a programming language",
            metadata={"provider": "mock", "model": "mock-echo"},
        )
        session_manager.add_message(
            session.id,
            "user",
            "Tell me about decorators",
            metadata={"provider": "mock", "model": "mock-echo"},
        )
        session_manager.add_message(
            session.id,
            "assistant",
            "Decorators are functions that modify other functions",
            metadata={"provider": "mock", "model": "mock-echo"},
        )

        # Test context retrieval
        context, truncated = session_manager.get_session_context(session.id)
        assert len(context) == 4
        assert not truncated

        # Test that context contains proper conversation flow
        assert context[0]["role"] == "user"
        assert "Python" in context[0]["content"]
        assert context[1]["role"] == "assistant"
        assert context[2]["role"] == "user"
        assert "decorator" in context[2]["content"]
        assert context[3]["role"] == "assistant"

        # Test context would work with mock provider
        messages = [Message(role=Role(msg["role"]), content=msg["content"]) for msg in context]

        # Add new question about previous conversation
        messages.append(
            Message(role=Role.USER, content="What were we discussing about decorators?")
        )

        # Mock provider should remember the context
        response = mock_provider.chat(messages, "mock-echo")
        assert "decorator" in response.lower()

    def test_session_commands_integration(self, session_manager):
        """Test session commands with full integration."""
        commands = SessionCommands(session_manager)

        # Simulate adding messages from CLI
        commands.add_message(
            "user",
            "Hello, I need help with Python",
            {"provider": "mock", "model": "mock-echo", "mode": "general"},
        )
        commands.add_message(
            "assistant",
            "Hello! I can help you with Python.",
            {"provider": "mock", "model": "mock-echo"},
        )

        assert len(commands.current_messages) == 2

        # Mock user input for save command (avoid interactive prompts)
        with patch("rich.prompt.Prompt.ask") as mock_prompt:
            mock_prompt.side_effect = ["Test Session", "A test session"]

            # Save session
            result = commands.handle_session_command(["save", "Python Help Session"])
            assert "Session saved" in result
            assert commands.current_session_id is not None

        # Verify session was saved
        saved_session = session_manager.get_session(commands.current_session_id)
        assert saved_session.name == "Python Help Session"

        # Clear conversation
        commands.clear_conversation()
        assert len(commands.current_messages) == 0
        assert commands.current_session_id is None

        # Load session back
        commands._load_session(["Python Help Session"])

        # Verify messages were restored
        assert len(commands.current_messages) == 2
        assert commands.current_messages[0]["content"] == "Hello, I need help with Python"
        assert commands.current_messages[1]["content"] == "Hello! I can help you with Python."

        # Test CLI message conversion
        commands._messages_loaded = True  # Simulate load flag
        cli_messages = commands.get_loaded_messages_for_cli()

        assert len(cli_messages) == 2
        assert cli_messages[0].role == Role.USER
        assert cli_messages[1].role == Role.ASSISTANT

    def test_conversation_continuity_after_load(self, session_manager, mock_provider):
        """Test that conversation context is properly restored for AI."""
        # Create session with conversation about Python
        session = session_manager.create_session(
            name="Python Context Test", provider="mock", model="mock-echo"
        )

        # Build conversation
        conversation = [
            ("user", "What is Python?"),
            ("assistant", "Python is a high-level programming language"),
            ("user", "Tell me about decorators"),
            ("assistant", "Decorators in Python are functions that modify other functions"),
        ]

        for role, content in conversation:
            session_manager.add_message(session.id, role, content)

        # Get context as if loading session
        context, _ = session_manager.get_session_context(session.id)

        # Convert to Message objects (as CLI would do)
        messages = [Message(role=Role(msg["role"]), content=msg["content"]) for msg in context]

        # Add new question that requires context
        messages.append(
            Message(role=Role.USER, content="What were we discussing about decorators?")
        )

        # Test that mock provider can answer based on context
        response = mock_provider.chat(messages, "mock-echo")

        # Should reference previous conversation
        assert "decorator" in response.lower()
        assert "python" in response.lower() or "we were discussing" in response.lower()

    def test_session_branching_with_conversation_continuity(self, session_manager, mock_provider):
        """Test session branching maintains proper conversation flow."""
        # Create original session
        session = session_manager.create_session(
            name="Original Session", provider="mock", model="mock-echo"
        )

        # Add initial conversation
        messages = [
            session_manager.add_message(session.id, "user", "What is Python?"),
            session_manager.add_message(
                session.id, "assistant", "Python is a programming language"
            ),
            session_manager.add_message(session.id, "user", "What about JavaScript?"),
            session_manager.add_message(
                session.id, "assistant", "JavaScript is used for web development"
            ),
        ]

        # Create branch from second message
        branch = session_manager.create_session(
            name="Python Focus Branch",
            provider="mock",
            model="mock-echo",
            parent_id=session.id,
            branch_point_message_id=messages[1].id,
        )

        # Verify branch has correct messages
        branch_messages = session_manager.get_messages(branch.id)
        assert len(branch_messages) == 2  # Up to branch point
        assert branch_messages[0].content == "What is Python?"
        assert branch_messages[1].content == "Python is a programming language"

        # Test that branch context works with AI
        context, _ = session_manager.get_session_context(branch.id)
        messages = [Message(role=Role(msg["role"]), content=msg["content"]) for msg in context]

        # Continue conversation in branch
        messages.append(
            Message(role=Role.USER, content="Can you tell me more about Python decorators?")
        )

        response = mock_provider.chat(messages, "mock-echo")
        assert "python" in response.lower()
        assert "decorator" in response.lower()

    def test_export_and_conversation_reconstruction(self, session_manager):
        """Test that exported sessions can be used to reconstruct conversations."""
        # Create session with multi-turn conversation
        session = session_manager.create_session(
            name="Export Test Session", provider="mock", model="mock-echo"
        )

        conversation_data = [
            ("user", "Hello, I'm learning Python"),
            ("assistant", "Great! I can help you learn Python."),
            ("user", "What are decorators?"),
            ("assistant", "Decorators are a way to modify functions in Python"),
            ("user", "Can you show me an example?"),
            ("assistant", "Sure! Here's a simple decorator: @property"),
        ]

        for role, content in conversation_data:
            session_manager.add_message(session.id, role, content)

        # Export in different formats
        json_export = session_manager.export_session(session.id, "json")
        md_export = session_manager.export_session(session.id, "markdown")

        # Verify exports contain conversation
        assert "learning Python" in json_export
        assert "decorators" in json_export
        assert "@property" in json_export

        assert "learning Python" in md_export
        assert "decorators" in md_export
        assert "👤 User" in md_export  # Markdown formatting
        assert "🤖 Assistant" in md_export

    def test_full_cli_session_workflow(self, temp_db_path):
        """Test complete CLI workflow with session management."""
        # This test simulates the actual CLI workflow

        # Create components
        db = SessionDatabase(temp_db_path)
        session_manager = SessionManager(db)
        session_commands = SessionCommands(session_manager)

        # Simulate CLI conversation state
        cli_messages = []

        try:
            # Step 1: Start conversation
            user_msg = Message(role=Role.USER, content="What is Python?")
            cli_messages.append(user_msg)

            # Simulate session commands tracking
            session_commands.add_message(
                "user", "What is Python?", {"provider": "mock", "model": "mock-echo"}
            )

            # Simulate AI response
            ai_response = "Python is a programming language"
            assistant_msg = Message(role=Role.ASSISTANT, content=ai_response)
            cli_messages.append(assistant_msg)

            session_commands.add_message(
                "assistant", ai_response, {"provider": "mock", "model": "mock-echo"}
            )

            # Step 2: Save session
            with patch("rich.prompt.Prompt.ask", return_value=""):
                result = session_commands.handle_session_command(["save", "Test Workflow"])
                assert "Session saved" in result

            session_id = session_commands.current_session_id
            assert session_id is not None

            # Step 3: Continue conversation
            user_msg2 = Message(role=Role.USER, content="Tell me about decorators")
            cli_messages.append(user_msg2)
            session_commands.add_message("user", "Tell me about decorators", {})

            # Step 4: Clear conversation (simulate /clear)
            cli_messages.clear()
            session_commands.clear_conversation()

            assert len(cli_messages) == 0
            assert len(session_commands.current_messages) == 0

            # Step 5: Load session back (simulate /session load)
            session_commands._load_session(["Test Workflow"])

            # Step 6: Get restored messages for CLI
            session_commands._messages_loaded = True
            restored_messages = session_commands.get_loaded_messages_for_cli()

            # Step 7: Restore to CLI messages (as the integration does)
            cli_messages.clear()
            cli_messages.extend(restored_messages)

            # Verify conversation was restored
            assert len(cli_messages) == 3  # 2 from saved session + 1 from before save
            assert cli_messages[0].role == Role.USER
            assert "Python" in cli_messages[0].content
            assert cli_messages[1].role == Role.ASSISTANT
            assert cli_messages[2].role == Role.USER
            assert "decorator" in cli_messages[2].content

            # Step 8: Test that AI would have context
            mock_provider = MockProvider()
            cli_messages.append(Message(role=Role.USER, content="What were we discussing?"))

            response = mock_provider.chat(cli_messages, "mock-echo")
            assert "python" in response.lower() or "decorator" in response.lower()

        finally:
            db.close()

    @pytest.mark.asyncio
    async def test_async_cli_integration(self, temp_db_path):
        """Test async CLI integration with session management."""
        # Create mock CLI components

        # This would be a more complex test simulating the actual async CLI flow
        # For now, we verify the basic integration points work

        db = SessionDatabase(temp_db_path)
        manager = SessionManager(db)
        commands = SessionCommands(manager)

        # Test that async operations work with session commands
        mock_cli = Mock()
        mock_cli.session_commands = commands
        mock_cli.current_mode = Mock()
        mock_cli.current_mode.value = "general"

        # Simulate message addition during conversation
        commands.add_message("user", "Test async", {"provider": "mock"})

        # Test async-safe operations
        assert len(commands.current_messages) == 1

        db.close()


@pytest.mark.integration
class TestSessionEndToEnd:
    """End-to-end tests for complete session functionality."""

    def test_complete_session_lifecycle(self):
        """Test complete session lifecycle from creation to deletion."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = Path(f.name)

        try:
            # Initialize
            db = SessionDatabase(db_path)
            manager = SessionManager(db)
            commands = SessionCommands(manager)
            MockProvider()

            # 1. Create and populate session
            commands.add_message("user", "Hello Python world", {})
            commands.add_message("assistant", "Hello! Ready to help with Python.", {})

            # 2. Save session
            with patch("rich.prompt.Prompt.ask", return_value=""):
                commands.handle_session_command(["save", "Lifecycle Test"])

            session_id = commands.current_session_id

            # 3. Test search
            results = manager.search_sessions("Python")
            assert len(results) == 1

            # 4. Test export
            export_data = manager.export_session(session_id, "json")
            assert "Python world" in export_data

            # 5. Test branching
            messages = manager.get_messages(session_id)
            branch = manager.create_session(
                name="Branch Test",
                provider="mock",
                model="mock-echo",
                parent_id=session_id,
                branch_point_message_id=messages[0].id,
            )

            # 6. Test context management
            context, truncated = manager.get_session_context(session_id, max_tokens=50)
            assert not truncated or len(context) < 2

            # 7. Test archive
            manager.archive_session(branch.id)
            archived = manager.get_session(branch.id)
            assert archived.status == "archived"

            # 8. Test delete
            manager.delete_session(branch.id, hard_delete=True)
            deleted = manager.get_session(branch.id)
            assert deleted is None

            print("✅ Complete session lifecycle test passed!")

        finally:
            db.close()
            db_path.unlink()
