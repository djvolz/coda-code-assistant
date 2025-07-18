"""Unit tests for Claude Code provider."""

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from coda.base.providers.claude_code import ClaudeCodeProvider
from coda.base.providers.base import Message, Role, ChatCompletion


class TestClaudeCodeProvider:
    """Test Claude Code provider implementation."""

    @patch("shutil.which")
    def test_init_command_not_found(self, mock_which):
        """Test initialization fails when claude command not found."""
        mock_which.return_value = None
        
        with pytest.raises(ValueError, match="Claude CLI command 'claude' not found"):
            ClaudeCodeProvider()

    @patch("shutil.which")
    def test_init_custom_command(self, mock_which):
        """Test initialization with custom command."""
        mock_which.return_value = "/custom/path/claude"
        
        provider = ClaudeCodeProvider(command="/custom/path/claude")
        assert provider.command == "/custom/path/claude"
        assert provider.name == "claude-code"

    @patch("shutil.which")
    @patch.dict("os.environ", {"CLAUDE_CODE_COMMAND": "/env/path/claude"})
    def test_init_from_env(self, mock_which):
        """Test initialization from environment variable."""
        mock_which.return_value = "/env/path/claude"
        
        provider = ClaudeCodeProvider()
        assert provider.command == "/env/path/claude"

    def test_filter_system_prompt(self):
        """Test system prompt filtering."""
        provider = ClaudeCodeProvider.__new__(ClaudeCodeProvider)
        provider.command = "claude"
        
        messages = [
            Message(role=Role.SYSTEM, content="System prompt\n\n# Extensions\nExtension content\n# Next Section"),
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there"),
        ]
        
        system_prompt, filtered_messages = provider._filter_system_prompt(messages)
        
        assert system_prompt == "System prompt\n# Next Section"
        assert len(filtered_messages) == 2
        assert filtered_messages[0].role == Role.USER
        assert filtered_messages[1].role == Role.ASSISTANT

    def test_convert_messages_to_claude_format(self):
        """Test message conversion to Claude CLI format."""
        provider = ClaudeCodeProvider.__new__(ClaudeCodeProvider)
        
        messages = [
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there"),
        ]
        
        claude_messages = provider._convert_messages_to_claude_format(messages)
        
        assert len(claude_messages) == 2
        assert claude_messages[0]["role"] == "user"
        assert claude_messages[0]["content"][0]["type"] == "text"
        assert claude_messages[0]["content"][0]["text"] == "Hello"
        assert claude_messages[1]["role"] == "assistant"

    def test_parse_claude_response_array(self):
        """Test parsing Claude CLI response as JSON array."""
        provider = ClaudeCodeProvider.__new__(ClaudeCodeProvider)
        
        # Simulate Claude CLI output as JSON array
        output = json.dumps([
            {
                "type": "assistant",
                "message": {
                    "content": [
                        {"type": "text", "text": "Hello! How can I help you today?"}
                    ],
                    "usage": {
                        "input_tokens": 10,
                        "output_tokens": 8
                    }
                }
            }
        ])
        
        content, usage = provider._parse_claude_response(output)
        
        assert content == "Hello! How can I help you today?"
        assert usage["prompt_tokens"] == 10
        assert usage["completion_tokens"] == 8
        assert usage["total_tokens"] == 18

    def test_parse_claude_response_lines(self):
        """Test parsing Claude CLI response as JSON lines."""
        provider = ClaudeCodeProvider.__new__(ClaudeCodeProvider)
        
        # Simulate Claude CLI output as JSON lines
        output = """{"type": "assistant", "message": {"content": [{"type": "text", "text": "First line"}]}}
{"type": "assistant", "message": {"content": [{"type": "text", "text": "Second line"}]}}
{"type": "result", "usage": {"input_tokens": 5, "output_tokens": 4}}"""
        
        content, usage = provider._parse_claude_response(output)
        
        assert content == "First line\n\nSecond line"
        assert usage["prompt_tokens"] == 5
        assert usage["completion_tokens"] == 4

    def test_parse_claude_response_no_content(self):
        """Test parsing Claude CLI response with no content."""
        provider = ClaudeCodeProvider.__new__(ClaudeCodeProvider)
        
        output = json.dumps([{"type": "result", "usage": {}}])
        
        content, usage = provider._parse_claude_response(output)
        
        assert content == "No response content found"
        assert usage is None

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_chat(self, mock_which, mock_run):
        """Test chat method."""
        mock_which.return_value = "/usr/bin/claude"
        
        # Mock subprocess response
        mock_result = MagicMock()
        mock_result.stdout = json.dumps([
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "Test response"}],
                    "usage": {"input_tokens": 10, "output_tokens": 5}
                }
            }
        ])
        mock_result.returncode = 0
        mock_run.return_value = mock_result
        
        provider = ClaudeCodeProvider()
        messages = [Message(role=Role.USER, content="Test message")]
        
        completion = provider.chat(messages, model="claude-code-default")
        
        assert isinstance(completion, ChatCompletion)
        assert completion.content == "Test response"
        assert completion.model == "claude-code-default"
        assert completion.usage["total_tokens"] == 15
        
        # Check subprocess was called correctly
        mock_run.assert_called_once()
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == "/usr/bin/claude"
        assert "-p" in call_args
        assert "--output-format" in call_args
        assert "json" in call_args

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_chat_cli_error(self, mock_which, mock_run):
        """Test chat method with CLI error."""
        mock_which.return_value = "/usr/bin/claude"
        
        # Mock subprocess error
        mock_run.side_effect = subprocess.CalledProcessError(
            1, "claude", stderr="Authentication error"
        )
        
        provider = ClaudeCodeProvider()
        messages = [Message(role=Role.USER, content="Test message")]
        
        with pytest.raises(RuntimeError, match="Claude CLI failed"):
            provider.chat(messages, model="claude-code-default")

    def test_validate_model(self):
        """Test model validation."""
        provider = ClaudeCodeProvider.__new__(ClaudeCodeProvider)
        
        assert provider.validate_model("claude-code-default")
        assert provider.validate_model("default")
        assert provider.validate_model("claude-3-5-sonnet")
        assert provider.validate_model("anything")  # Should accept any model

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_list_models(self, mock_which, mock_run):
        """Test listing models."""
        mock_which.return_value = "/usr/bin/claude"
        
        # Mock help output
        help_result = MagicMock()
        help_result.stdout = "claude help text"
        help_result.returncode = 0
        
        # Mock model query output
        query_result = MagicMock()
        query_result.stdout = json.dumps([
            {
                "type": "assistant",
                "message": {
                    "content": [{"type": "text", "text": "ok"}],
                    "model": "claude-3-5-sonnet-20241022"
                }
            }
        ])
        query_result.returncode = 0
        
        mock_run.side_effect = [help_result, query_result]
        
        provider = ClaudeCodeProvider()
        models = provider.list_models()
        
        assert len(models) == 1
        assert models[0].id == "claude-3-5-sonnet-20241022"
        assert models[0].name == "claude-3-5-sonnet-20241022 (via Claude Code)"
        assert models[0].context_length == 200_000
        assert not models[0].supports_streaming
        
        # Check model is cached
        assert provider._cached_model_info is not None
        assert provider._cached_model_info.id == "claude-3-5-sonnet-20241022"

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_list_models_fallback(self, mock_which, mock_run):
        """Test listing models with fallback."""
        mock_which.return_value = "/usr/bin/claude"
        
        # Mock subprocess error
        mock_run.side_effect = Exception("CLI error")
        
        provider = ClaudeCodeProvider()
        models = provider.list_models()
        
        assert len(models) == 1
        assert models[0].id == "claude-code-default"
        assert models[0].name == "Claude (via Claude Code)"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])