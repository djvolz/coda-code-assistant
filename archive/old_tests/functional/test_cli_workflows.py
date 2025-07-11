"""Functional tests for end-to-end CLI workflows."""

import os
import tempfile
from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI


class TestCLIWorkflows:
    """Test complete user workflows in the CLI."""

    @pytest.fixture
    def cli_with_mocks(self):
        """Create a fully mocked InteractiveCLI for workflow testing."""
        with patch("coda.cli.interactive_cli.ModelManager") as mock_mm:
            # Mock model manager
            mock_mm.return_value.list_providers.return_value = ["openai", "anthropic"]
            mock_mm.return_value.list_models.return_value = ["gpt-4", "gpt-3.5-turbo"]
            mock_mm.return_value.validate_model.return_value = True

            cli = InteractiveCLI()

            # Mock session components
            cli.session_manager = Mock()
            cli.chat_session = Mock()
            cli.chat_session.send_message = Mock(return_value="AI response")

            # Mock prompt session
            with patch.object(cli, "_setup_prompt_sessions"):
                cli.prompt_session = Mock()
                cli.multiline_session = Mock()

            return cli

    def test_complete_conversation_workflow(self, cli_with_mocks):
        """Test a complete conversation workflow."""
        cli = cli_with_mocks

        # Simulate user inputs
        inputs = ["Hello, can you help me?", "Write a Python function", "/exit"]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "run"):
                # Start the CLI
                cli.run()

                # Verify conversation flow
                assert cli.chat_session.send_message.call_count == 2
                cli.chat_session.send_message.assert_any_call(
                    message="Hello, can you help me?", mode="default"
                )
                cli.chat_session.send_message.assert_any_call(
                    message="Write a Python function", mode="default"
                )

    def test_mode_switching_workflow(self, cli_with_mocks):
        """Test switching modes during conversation."""
        cli = cli_with_mocks

        # Simulate mode switching
        inputs = [
            "Normal chat message",
            "/mode code",
            "def hello_world():",
            "/mode shell",
            "ls -la",
            "/exit",
        ]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "_execute_command") as mock_exec:
                with patch("coda.cli.interactive_cli.print"):
                    # Mock command execution
                    def exec_side_effect(cmd):
                        if cmd == "/mode code":
                            cli.mode = "code"
                            return True
                        elif cmd == "/mode shell":
                            cli.mode = "shell"
                            return True
                        return False

                    mock_exec.side_effect = exec_side_effect

                    # Run workflow
                    cli.run()

                    # Verify mode changes
                    calls = cli.chat_session.send_message.call_args_list
                    assert calls[0][1]["mode"] == "default"
                    assert calls[1][1]["mode"] == "code"
                    assert calls[2][1]["mode"] == "shell"

    def test_model_selection_workflow(self, cli_with_mocks):
        """Test model selection during session."""
        cli = cli_with_mocks

        inputs = [
            "/model",  # List models
            "/model gpt-4",  # Select model
            "Test with new model",
            "/provider anthropic",  # Switch provider
            "/model claude-2",  # Select model from new provider
            "/exit",
        ]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "_execute_command") as mock_exec:
                with patch("coda.cli.interactive_cli.print") as mock_print:
                    # Mock command execution
                    def exec_side_effect(cmd):
                        if cmd == "/model":
                            mock_print("Available models: gpt-4, gpt-3.5-turbo")
                            return True
                        elif cmd == "/model gpt-4":
                            cli.current_model = "gpt-4"
                            return True
                        elif cmd == "/provider anthropic":
                            cli.current_provider = "anthropic"
                            cli.model_manager.list_models.return_value = [
                                "claude-2",
                                "claude-instant",
                            ]
                            return True
                        elif cmd == "/model claude-2":
                            cli.current_model = "claude-2"
                            return True
                        return False

                    mock_exec.side_effect = exec_side_effect

                    # Run workflow
                    cli.run()

                    # Verify model/provider changes
                    assert mock_exec.call_count >= 4
                    mock_exec.assert_any_call("/model")
                    mock_exec.assert_any_call("/model gpt-4")
                    mock_exec.assert_any_call("/provider anthropic")

    def test_session_export_workflow(self, cli_with_mocks):
        """Test session export functionality."""
        cli = cli_with_mocks
        temp_file = tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md")
        temp_file.close()

        try:
            inputs = ["First message", "Second message", f"/export {temp_file.name}", "/exit"]

            # Mock conversation history
            cli.chat_session.get_history.return_value = [
                {"role": "user", "content": "First message"},
                {"role": "assistant", "content": "First response"},
                {"role": "user", "content": "Second message"},
                {"role": "assistant", "content": "Second response"},
            ]

            with patch.object(cli, "get_input", side_effect=inputs):
                with patch.object(cli, "_execute_command") as mock_exec:
                    with patch("coda.cli.interactive_cli.print"):
                        # Mock export command
                        def exec_side_effect(cmd):
                            if cmd.startswith("/export"):
                                # Simulate export
                                with open(temp_file.name, "w") as f:
                                    f.write("# Conversation Export\n\n")
                                    for msg in cli.chat_session.get_history():
                                        f.write(f"**{msg['role']}**: {msg['content']}\n\n")
                                return True
                            return False

                        mock_exec.side_effect = exec_side_effect

                        # Run workflow
                        cli.run()

                        # Verify export was called
                        mock_exec.assert_any_call(f"/export {temp_file.name}")

                        # Check file was created
                        assert os.path.exists(temp_file.name)
                        with open(temp_file.name) as f:
                            content = f.read()
                            assert "Conversation Export" in content
        finally:
            os.unlink(temp_file.name)

    def test_multiline_code_input_workflow(self, cli_with_mocks):
        """Test multiline code input workflow."""
        cli = cli_with_mocks

        # Simulate multiline code input
        code_lines = [
            "```python",
            "def fibonacci(n):",
            "    if n <= 1:",
            "        return n",
            "    return fibonacci(n-1) + fibonacci(n-2)",
            "```",
        ]

        inputs = [
            "I need help with a function",
            "```python",  # Start multiline
            *code_lines[1:-1],  # Code lines
            "```",  # End multiline
            "/exit",
        ]

        with patch.object(cli, "get_input") as mock_input:
            # Setup multiline behavior
            call_count = 0

            def get_input_side_effect():
                nonlocal call_count
                if call_count < len(inputs):
                    result = inputs[call_count]
                    call_count += 1

                    # Simulate multiline mode
                    if result == "```python" and call_count == 2:
                        # Return the full multiline block
                        return "\n".join(code_lines)
                    elif call_count > 2 and call_count < 8:
                        # Skip the multiline portion
                        call_count = 8
                        return inputs[7] if 7 < len(inputs) else None

                    return result
                return None

            mock_input.side_effect = get_input_side_effect

            # Run workflow
            cli.run()

            # Verify multiline code was sent
            calls = cli.chat_session.send_message.call_args_list
            assert any("def fibonacci" in str(call) for call in calls)

    def test_interrupt_handling_workflow(self, cli_with_mocks):
        """Test interrupt handling during conversation."""
        cli = cli_with_mocks

        inputs = [
            "Start a conversation",
            KeyboardInterrupt(),  # Simulate Ctrl+C
            "Continue after interrupt",
            "/exit",
        ]

        with patch.object(cli, "get_input") as mock_input:
            # Handle the interrupt
            call_count = 0

            def get_input_side_effect():
                nonlocal call_count
                if call_count < len(inputs):
                    inp = inputs[call_count]
                    call_count += 1
                    if isinstance(inp, type) and issubclass(inp, KeyboardInterrupt):
                        return None  # Interrupt returns None
                    return inp
                return None

            mock_input.side_effect = get_input_side_effect

            with patch("coda.cli.interactive_cli.print"):
                # Run workflow
                cli.run()

                # Should handle interrupt gracefully
                assert cli.chat_session.send_message.call_count == 2
                # Verify both messages were sent (before and after interrupt)
                calls = [call[0][0] for call in cli.chat_session.send_message.call_args_list]
                assert "Start a conversation" in calls
                assert "Continue after interrupt" in calls

    def test_theme_switching_workflow(self, cli_with_mocks):
        """Test theme switching during session."""
        cli = cli_with_mocks

        inputs = [
            "/theme",  # List themes
            "/theme dark",  # Switch theme
            "Continue with dark theme",
            "/theme reset",  # Reset theme
            "/exit",
        ]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "_execute_command") as mock_exec:
                with patch("coda.cli.interactive_cli.print") as mock_print:
                    # Mock theme commands
                    def exec_side_effect(cmd):
                        if cmd == "/theme":
                            mock_print("Available themes: default, dark, light, monokai")
                            return True
                        elif cmd == "/theme dark":
                            cli.theme_manager.set_theme("dark")
                            return True
                        elif cmd == "/theme reset":
                            cli.theme_manager.reset_theme()
                            return True
                        return False

                    mock_exec.side_effect = exec_side_effect
                    cli.theme_manager = Mock()

                    # Run workflow
                    cli.run()

                    # Verify theme changes
                    cli.theme_manager.set_theme.assert_called_with("dark")
                    cli.theme_manager.reset_theme.assert_called_once()

    def test_help_navigation_workflow(self, cli_with_mocks):
        """Test help command navigation."""
        cli = cli_with_mocks

        inputs = [
            "/help",  # General help
            "/help model",  # Specific command help
            "/help theme",  # Another command help
            "/exit",
        ]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "_execute_command") as mock_exec:
                with patch("coda.cli.interactive_cli.print"):
                    mock_exec.return_value = True

                    # Run workflow
                    cli.run()

                    # Verify help commands
                    assert mock_exec.call_count >= 3
                    mock_exec.assert_any_call("/help")
                    mock_exec.assert_any_call("/help model")
                    mock_exec.assert_any_call("/help theme")

    def test_error_recovery_workflow(self, cli_with_mocks):
        """Test error recovery in conversation."""
        cli = cli_with_mocks

        # Make send_message fail once then succeed
        cli.chat_session.send_message.side_effect = [
            Exception("Network error"),
            "Recovery response",
            "Normal response",
        ]

        inputs = ["Message that will fail", "Retry message", "Normal message", "/exit"]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch("coda.cli.interactive_cli.print") as mock_print:
                # Run workflow
                cli.run()

                # Should recover from error
                assert cli.chat_session.send_message.call_count == 3
                # Verify error was printed
                error_prints = [
                    call for call in mock_print.call_args_list if "Network error" in str(call)
                ]
                assert len(error_prints) > 0

    def test_session_persistence_workflow(self, cli_with_mocks):
        """Test session saving and loading workflow."""
        cli = cli_with_mocks
        session_id = "test_session_123"

        inputs = [
            "/session new",  # Create new session
            "Message in new session",
            f"/session save {session_id}",  # Save session
            "/session list",  # List sessions
            f"/session load {session_id}",  # Load session
            "Continue in loaded session",
            "/exit",
        ]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "_execute_command") as mock_exec:
                # Mock session commands
                saved_sessions = {}

                def exec_side_effect(cmd):
                    if cmd == "/session new":
                        cli.chat_session = Mock()
                        cli.chat_session.send_message = Mock(return_value="Response")
                        return True
                    elif cmd.startswith("/session save"):
                        session_name = cmd.split()[-1]
                        saved_sessions[session_name] = cli.chat_session
                        return True
                    elif cmd.startswith("/session load"):
                        session_name = cmd.split()[-1]
                        if session_name in saved_sessions:
                            cli.chat_session = saved_sessions[session_name]
                        return True
                    elif cmd == "/session list":
                        return True
                    return False

                mock_exec.side_effect = exec_side_effect

                # Run workflow
                cli.run()

                # Verify session commands
                mock_exec.assert_any_call("/session new")
                mock_exec.assert_any_call(f"/session save {session_id}")
                mock_exec.assert_any_call(f"/session load {session_id}")

    @pytest.mark.parametrize(
        "workflow_type", ["quick_question", "code_review", "debugging_session", "learning_tutorial"]
    )
    def test_common_workflow_patterns(self, cli_with_mocks, workflow_type):
        """Test common usage patterns."""
        cli = cli_with_mocks

        workflows = {
            "quick_question": ["What is Python?", "/exit"],
            "code_review": ["/mode code", "Review this: def add(a,b): return a+b", "/exit"],
            "debugging_session": [
                "/mode shell",
                "python --version",
                "/mode code",
                "Fix this error: NameError",
                "/exit",
            ],
            "learning_tutorial": [
                "Teach me about decorators",
                "Show me an example",
                "Explain how it works",
                "/exit",
            ],
        }

        inputs = workflows[workflow_type]

        with patch.object(cli, "get_input", side_effect=inputs):
            with patch.object(cli, "_execute_command", return_value=True):
                # Run workflow
                cli.run()

                # Verify appropriate number of messages sent
                expected_messages = len([i for i in inputs if not i.startswith("/")])
                assert cli.chat_session.send_message.call_count == expected_messages
