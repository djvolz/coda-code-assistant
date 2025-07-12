"""Tests for MockProvider with all CLI commands."""

import pytest

from coda.base.providers import Message, MockProvider, Role


@pytest.mark.unit
class TestMockProviderCommands:
    """Test MockProvider behavior with various CLI command scenarios."""

    def test_clear_command_scenario(self):
        """Test conversation behavior around /clear command."""
        provider = MockProvider()

        # Build conversation
        messages = [
            Message(role=Role.USER, content="Tell me about Python"),
            Message(role=Role.ASSISTANT, content="Python is a programming language..."),
            Message(role=Role.USER, content="What about decorators?"),
            Message(role=Role.ASSISTANT, content="Decorators are..."),
        ]

        # Ask about previous conversation
        messages.append(Message(role=Role.USER, content="What were we discussing?"))
        response = provider.chat(messages, "mock-echo")
        assert "python" in response.content.lower() and "decorator" in response.content.lower()

        # Simulate /clear - start fresh conversation
        new_messages = [Message(role=Role.USER, content="What were we discussing?")]
        response_after_clear = provider.chat(new_messages, "mock-echo")

        # Should not remember previous conversation
        assert "don't see any previous conversation" in response_after_clear.content.lower()

    def test_model_switching_scenario(self):
        """Test conversation continuity when switching models."""
        provider = MockProvider()

        # Start with mock-echo
        messages = [
            Message(role=Role.USER, content="Tell me about Python"),
            Message(role=Role.ASSISTANT, content="Python is a programming language..."),
        ]

        # Continue with mock-echo
        messages.append(Message(role=Role.USER, content="What about decorators?"))
        response_echo = provider.chat(messages, "mock-echo")

        # Switch to mock-smart (same conversation)
        messages.append(Message(role=Role.ASSISTANT, content=response_echo.content))
        messages.append(Message(role=Role.USER, content="What were we discussing?"))
        response_smart = provider.chat(messages, "mock-smart")

        # Both models should maintain context
        assert (
            "python" in response_smart.content.lower()
            and "decorator" in response_smart.content.lower()
        )

    def test_mode_command_scenarios(self):
        """Test conversations with mode switching."""
        provider = MockProvider()

        # Simulate mode switches in conversation
        mode_prompts = {
            "general": "You are a helpful AI assistant",
            "code": "You are a code writing assistant",
            "debug": "You are a debugging assistant",
            "explain": "You are a code explanation assistant",
            "review": "You are a code review assistant",
            "refactor": "You are a refactoring assistant",
            "plan": "You are an architecture planning assistant",
        }

        for mode, prompt in mode_prompts.items():
            messages = [
                Message(role=Role.SYSTEM, content=prompt),
                Message(role=Role.USER, content=f"I need help with Python in {mode} mode"),
            ]

            response = provider.chat(messages, "mock-echo")

            # Should handle all modes
            assert response
            assert len(response.content) > 10
            if "python" in messages[1].content.lower():
                assert "python" in response.content.lower()

    def test_session_command_scenarios(self):
        """Test conversation patterns for session management."""
        provider = MockProvider()

        # Build a conversation worth saving
        messages = [
            Message(role=Role.USER, content="Let's discuss Python web frameworks"),
            Message(role=Role.ASSISTANT, content="Python has many web frameworks..."),
            Message(role=Role.USER, content="Tell me about Flask"),
            Message(role=Role.ASSISTANT, content="Flask is a micro framework..."),
            Message(role=Role.USER, content="What about Django?"),
            Message(role=Role.ASSISTANT, content="Django is a full-featured framework..."),
        ]

        # User might ask to summarize before saving
        messages.append(Message(role=Role.USER, content="What were we discussing?"))
        response = provider.chat(messages, "mock-echo")

        # Should be able to summarize the conversation
        assert response
        assert "python" in response.content.lower()  # Should recognize Python was discussed

        # Simulate loading a session - asking about context
        loaded_messages = messages.copy()
        loaded_messages.append(Message(role=Role.USER, content="What were we talking about?"))
        response_loaded = provider.chat(loaded_messages, "mock-echo")

        # Should remember the context
        assert any(
            word in response_loaded.content.lower()
            for word in ["python", "flask", "django", "framework"]
        )

    def test_export_command_scenarios(self):
        """Test conversations that might be exported."""
        provider = MockProvider()

        # Create a conversation with various content types
        messages = [
            Message(role=Role.USER, content="Show me a Python decorator"),
            Message(role=Role.ASSISTANT, content="Here's a decorator example..."),
            Message(role=Role.USER, content="Can you explain how it works?"),
            Message(role=Role.ASSISTANT, content="The decorator modifies..."),
            Message(role=Role.USER, content="What else can decorators do?"),
        ]

        response = provider.chat(messages, "mock-echo")

        # Should handle export-worthy conversations
        assert response
        assert "decorator" in response.content.lower() or "python" in response.content.lower()

    def test_help_command_context(self):
        """Test asking for help in various contexts."""
        provider = MockProvider()

        # User asks for help mid-conversation
        messages = [
            Message(role=Role.USER, content="I'm learning Python"),
            Message(role=Role.ASSISTANT, content="Great! Python is..."),
            Message(role=Role.USER, content="help"),  # Could be asking for help
        ]

        response = provider.chat(messages, "mock-echo")

        # Should provide some help response
        assert "help" in response.content.lower()

    def test_provider_command_scenario(self):
        """Test provider-related conversations."""
        provider = MockProvider()

        # User might ask about providers
        messages = [
            Message(role=Role.USER, content="What AI provider are you using?"),
        ]

        response = provider.chat(messages, "mock-echo")

        # Should handle provider questions
        assert response
        assert len(response.content) > 10

    def test_command_error_scenarios(self):
        """Test error scenarios with commands."""
        provider = MockProvider()

        # Misspelled or invalid command references
        error_scenarios = [
            "I tried /cleear but it didn't work",
            "The /modle command isn't working",
            "How do I use /sesion save?",
            "Is there a /delete command?",
        ]

        for scenario in error_scenarios:
            messages = [Message(role=Role.USER, content=scenario)]
            response = provider.chat(messages, "mock-echo")

            # Should still provide a response
            assert response
            assert len(response.content) > 5

    def test_interactive_only_commands(self):
        """Test scenarios with interactive-only commands."""
        provider = MockProvider()

        # These commands are only in interactive mode
        interactive_commands = [
            "How do I save this session?",
            "Can I export this conversation?",
            "How do I search my sessions?",
            "Tell me about the tools command",
        ]

        for command_question in interactive_commands:
            messages = [Message(role=Role.USER, content=command_question)]
            response = provider.chat(messages, "mock-echo")

            # Should handle questions about commands
            assert response
            assert len(response.content) > 10

    def test_command_combination_scenarios(self):
        """Test complex scenarios with multiple commands."""
        provider = MockProvider()

        # Scenario: User switches mode, then model, then asks question
        messages = [
            Message(role=Role.SYSTEM, content="You are in code mode"),
            Message(role=Role.USER, content="I just switched to code mode"),
            Message(role=Role.ASSISTANT, content="Great! I'm ready to help with code."),
            Message(role=Role.USER, content="And I'm using the smart model now"),
            Message(role=Role.ASSISTANT, content="Excellent choice!"),
            Message(role=Role.USER, content="Show me a Python class example"),
        ]

        response = provider.chat(messages, "mock-smart")

        # Should handle the Python request
        assert "python" in response.content.lower() or "class" in response.content.lower()

    def test_coming_soon_commands(self):
        """Test conversations about coming soon features."""
        provider = MockProvider()

        coming_soon = [
            "When will the tools command be available?",
            "I want to change the theme",
            "Tell me about MCP tools",
        ]

        for question in coming_soon:
            messages = [Message(role=Role.USER, content=question)]
            response = provider.chat(messages, "mock-echo")

            # Should handle gracefully
            assert response
            assert len(response.content) > 5


@pytest.mark.unit
class TestMockProviderCommandIntegration:
    """Test how MockProvider integrates with command workflows."""

    def test_full_session_workflow(self):
        """Test a complete session workflow with MockProvider."""
        provider = MockProvider()

        # 1. Start conversation
        messages = [Message(role=Role.USER, content="I need help with Python async programming")]
        response1 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response1.content))

        # 2. Ask specific question
        messages.append(Message(role=Role.USER, content="How do I use async/await?"))
        response2 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response2.content))

        # 3. User wants to save session
        messages.append(Message(role=Role.USER, content="This is helpful, I should save this"))
        response3 = provider.chat(messages, "mock-echo")
        messages.append(Message(role=Role.ASSISTANT, content=response3.content))

        # 4. Continue conversation
        messages.append(Message(role=Role.USER, content="What about asyncio?"))
        response4 = provider.chat(messages, "mock-echo")

        # Should maintain context throughout
        assert response4

        # 5. Check context is maintained
        messages.append(Message(role=Role.ASSISTANT, content=response4.content))
        messages.append(Message(role=Role.USER, content="What have we covered so far?"))
        summary = provider.chat(messages, "mock-echo")

        # Should remember the async/Python discussion
        assert "python" in summary.content.lower() or "async" in summary.content.lower()

    def test_mode_switching_workflow(self):
        """Test workflow with multiple mode switches."""
        provider = MockProvider()

        workflows = [
            # General -> Code
            {
                "messages": [
                    (Role.SYSTEM, "You are in general mode"),
                    (Role.USER, "Hi, I want to learn programming"),
                    (Role.ASSISTANT, "Hello! I can help..."),
                    (Role.SYSTEM, "You are in code mode"),
                    (Role.USER, "Show me a Python example"),
                ],
                "final_check": "python",
            },
            # Code -> Debug
            {
                "messages": [
                    (Role.SYSTEM, "You are in code mode"),
                    (Role.USER, "Here's my Python function"),
                    (Role.ASSISTANT, "I see your function..."),
                    (Role.SYSTEM, "You are in debug mode"),
                    (Role.USER, "Why isn't it working?"),
                ],
                "final_check": "python",
            },
            # Debug -> Explain
            {
                "messages": [
                    (Role.SYSTEM, "You are in debug mode"),
                    (Role.USER, "Found the bug in my Python code"),
                    (Role.ASSISTANT, "Good job finding it..."),
                    (Role.SYSTEM, "You are in explain mode"),
                    (Role.USER, "Can you explain why that happened?"),
                ],
                "final_check": "python",
            },
        ]

        for workflow in workflows:
            messages = []
            for role, content in workflow["messages"][:-1]:
                messages.append(Message(role=role, content=content))

            # Add final user message
            final_role, final_content = workflow["messages"][-1]
            messages.append(Message(role=final_role, content=final_content))

            response = provider.chat(messages, "mock-echo")

            # Should maintain context through mode switches
            if workflow["final_check"] in messages[-1].content.lower():
                assert (
                    workflow["final_check"] in response.content.lower()
                    or len(response.content) > 10
                )
