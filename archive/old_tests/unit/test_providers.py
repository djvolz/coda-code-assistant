"""Unit tests for provider implementations."""

from unittest.mock import Mock, patch

import pytest

from coda.base.providers import (
    ChatCompletion,
    LiteLLMProvider,
    Message,
    OllamaProvider,
    Role,
)


@pytest.mark.unit
class TestLiteLLMProvider:
    """Test LiteLLM provider."""

    def test_init(self):
        """Test provider initialization."""
        provider = LiteLLMProvider(
            api_base="http://localhost:8000",
            api_key="test-key",
            default_model="gpt-4",
        )

        assert provider.name == "litellm"
        assert provider.default_model == "gpt-4"

    def test_convert_messages(self):
        """Test message conversion."""
        provider = LiteLLMProvider()

        messages = [
            Message(role=Role.SYSTEM, content="You are helpful"),
            Message(role=Role.USER, content="Hello", name="user1"),
            Message(role=Role.ASSISTANT, content="Hi there"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 3
        assert converted[0] == {"role": "system", "content": "You are helpful"}
        assert converted[1] == {"role": "user", "content": "Hello", "name": "user1"}
        assert converted[2] == {"role": "assistant", "content": "Hi there"}

    @patch("coda.providers.litellm_provider.completion")
    def test_chat(self, mock_completion):
        """Test chat completion."""
        # Mock response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        mock_response.id = "test-id"
        mock_response.created = 1234567890

        mock_completion.return_value = mock_response

        # Test chat
        provider = LiteLLMProvider()
        messages = [Message(role=Role.USER, content="Hello")]

        result = provider.chat(messages, model="gpt-3.5-turbo")

        assert isinstance(result, ChatCompletion)
        assert result.content == "Test response"
        assert result.model == "gpt-3.5-turbo"
        assert result.finish_reason == "stop"
        assert result.usage["total_tokens"] == 30

        # Check call arguments
        mock_completion.assert_called_once()
        call_args = mock_completion.call_args[1]
        assert call_args["model"] == "gpt-3.5-turbo"
        assert call_args["stream"] is False

    @patch("coda.providers.litellm_provider.completion")
    def test_chat_stream(self, mock_completion):
        """Test streaming chat."""
        # Mock streaming chunks
        chunks = []
        for text in ["Hello", " world", "!"]:
            chunk = Mock()
            chunk.choices = [Mock()]
            chunk.choices[0].delta.content = text
            chunk.choices[0].finish_reason = None
            chunk.id = f"chunk-{text}"
            chunks.append(chunk)

        # Add final chunk
        final_chunk = Mock()
        final_chunk.choices = [Mock()]
        final_chunk.choices[0].delta.content = ""
        final_chunk.choices[0].finish_reason = "stop"
        chunks.append(final_chunk)

        mock_completion.return_value = iter(chunks)

        # Test streaming
        provider = LiteLLMProvider()
        messages = [Message(role=Role.USER, content="Hello")]

        chunks_list = list(provider.chat_stream(messages, model="gpt-3.5-turbo"))

        assert len(chunks_list) == 4
        assert chunks_list[0].content == "Hello"
        assert chunks_list[1].content == " world"
        assert chunks_list[2].content == "!"
        assert chunks_list[3].finish_reason == "stop"

    def test_list_models(self):
        """Test model listing."""
        provider = LiteLLMProvider()
        models = provider.list_models()

        assert len(models) > 0
        assert any(m.id == "gpt-3.5-turbo" for m in models)
        assert any(m.provider == "openai" for m in models)
        assert any(m.provider == "anthropic" for m in models)


@pytest.mark.unit
class TestOllamaProvider:
    """Test Ollama provider."""

    def test_init(self):
        """Test provider initialization."""
        provider = OllamaProvider(
            host="http://localhost:11434",
            timeout=60.0,
        )

        assert provider.name == "ollama"
        assert provider.host == "http://localhost:11434"
        assert provider.timeout == 60.0

    def test_convert_messages(self):
        """Test message conversion."""
        provider = OllamaProvider()

        messages = [
            Message(role=Role.SYSTEM, content="You are helpful"),
            Message(role=Role.USER, content="Hello"),
            Message(role=Role.ASSISTANT, content="Hi there"),
        ]

        converted = provider._convert_messages(messages)

        assert len(converted) == 3
        assert converted[0] == {"role": "system", "content": "You are helpful"}
        assert converted[1] == {"role": "user", "content": "Hello"}
        assert converted[2] == {"role": "assistant", "content": "Hi there"}

    @patch("httpx.Client")
    def test_chat(self, mock_client_class):
        """Test chat completion."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "message": {"content": "Test response"},
            "prompt_eval_count": 10,
            "eval_count": 20,
            "total_duration": 1000000000,
            "load_duration": 100000000,
            "prompt_eval_duration": 200000000,
            "eval_duration": 700000000,
        }

        mock_client = Mock()
        mock_client.post.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Test chat
        provider = OllamaProvider()
        messages = [Message(role=Role.USER, content="Hello")]

        result = provider.chat(messages, model="llama3")

        assert isinstance(result, ChatCompletion)
        assert result.content == "Test response"
        assert result.model == "llama3"
        assert result.usage["total_tokens"] == 30

        # Check API call
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert call_args[0][0] == "http://localhost:11434/api/chat"
        assert call_args[1]["json"]["model"] == "llama3"
        assert call_args[1]["json"]["stream"] is False

    @patch("httpx.Client")
    def test_list_models(self, mock_client_class):
        """Test model listing."""
        # Mock response
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {
                    "name": "llama3:latest",
                    "size": 4661226112,
                    "digest": "abc123",
                    "details": {
                        "parameter_size": "7B",
                        "family": "llama",
                        "format": "gguf",
                    },
                },
                {
                    "name": "mistral:latest",
                    "size": 3825912832,
                    "digest": "def456",
                    "details": {
                        "parameter_size": "7B",
                        "family": "mistral",
                    },
                },
            ]
        }

        mock_client = Mock()
        mock_client.get.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Test listing
        provider = OllamaProvider()
        models = provider.list_models()

        assert len(models) == 2
        assert models[0].id == "llama3:latest"
        assert models[0].provider == "ollama"
        assert models[0].metadata["parameter_size"] == "7B"
        assert models[1].id == "mistral:latest"

    def test_extract_model_info(self):
        """Test model info extraction."""
        provider = OllamaProvider()

        # Test various model names
        test_cases = [
            ("llama3:32k", 32768),
            ("mistral:7b-16k", 16384),
            ("codellama:100k", 102400),
            ("phi:latest", 4096),  # Default
        ]

        for model_name, expected_context in test_cases:
            model_data = {"name": model_name, "details": {"parameter_size": "7B"}}
            model = provider._extract_model_info(model_data)
            assert model.context_length == expected_context
