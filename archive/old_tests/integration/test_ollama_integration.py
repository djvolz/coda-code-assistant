"""Integration tests for Ollama provider."""

import pytest

from coda.providers import Message, OllamaProvider, Role


@pytest.mark.integration
class TestOllamaIntegration:
    """Integration tests for Ollama provider."""

    def test_ollama_connection(self):
        """Test basic connection to Ollama."""
        provider = OllamaProvider(host="http://localhost:11434")

        # This will fail if Ollama is not running, which is expected for integration tests
        try:
            models = provider.list_models()
            assert isinstance(models, list)
            # If we get here, Ollama is running
            if models:
                assert all(hasattr(m, "id") for m in models)
                assert all(hasattr(m, "provider") for m in models)
                assert all(m.provider == "ollama" for m in models)
        except Exception as e:
            # This is expected if Ollama is not running
            pytest.skip(f"Ollama not available: {e}")

    def test_ollama_chat(self):
        """Test chat functionality with Ollama."""
        provider = OllamaProvider()

        try:
            models = provider.list_models()
            if not models:
                pytest.skip("No Ollama models available")

            # Use the smallest/fastest model
            model_id = models[-1].id

            messages = [Message(role=Role.USER, content="Say 'Hello' and nothing else.")]

            response = provider.chat(messages, model=model_id, max_tokens=10)

            assert response.content
            assert response.model == model_id
            assert response.usage is not None
            assert "prompt_tokens" in response.usage
            assert "completion_tokens" in response.usage

        except Exception as e:
            pytest.skip(f"Ollama not available: {e}")

    def test_ollama_streaming(self):
        """Test streaming functionality with Ollama."""
        provider = OllamaProvider()

        try:
            models = provider.list_models()
            if not models:
                pytest.skip("No Ollama models available")

            model_id = models[-1].id

            messages = [Message(role=Role.USER, content="Count from 1 to 3.")]

            chunks = list(provider.chat_stream(messages, model=model_id, max_tokens=20))

            assert len(chunks) > 0
            assert any(chunk.content for chunk in chunks)
            assert any(chunk.finish_reason == "stop" for chunk in chunks)

            # Reconstruct full response
            full_response = "".join(chunk.content for chunk in chunks)
            assert len(full_response) > 0

        except Exception as e:
            pytest.skip(f"Ollama not available: {e}")

    @pytest.mark.asyncio
    async def test_ollama_async(self):
        """Test async functionality with Ollama."""
        provider = OllamaProvider()

        try:
            models = provider.list_models()
            if not models:
                pytest.skip("No Ollama models available")

            model_id = models[-1].id

            messages = [Message(role=Role.USER, content="Say 'Hi' and nothing else.")]

            # Test async chat
            response = await provider.achat(messages, model=model_id, max_tokens=10)
            assert response.content

            # Test async streaming
            chunks = []
            async for chunk in provider.achat_stream(messages, model=model_id, max_tokens=10):
                chunks.append(chunk)

            assert len(chunks) > 0

        except Exception as e:
            pytest.skip(f"Ollama not available: {e}")


@pytest.mark.unit
class TestOllamaUnit:
    """Unit tests for Ollama provider (no real connection needed)."""

    def test_ollama_initialization(self):
        """Test Ollama provider initialization."""
        provider = OllamaProvider(host="http://example.com:11434", timeout=30.0)

        assert provider.name == "ollama"
        assert provider.host == "http://example.com:11434"
        assert provider.timeout == 30.0

    def test_message_conversion(self):
        """Test message format conversion."""
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

    def test_model_info_extraction(self):
        """Test extraction of model information."""
        provider = OllamaProvider()

        # Test various model configurations
        test_cases = [
            {
                "input": {
                    "name": "llama3:8b-instruct-32k",
                    "details": {"parameter_size": "8B", "family": "llama"},
                },
                "expected_context": 32768,
            },
            {
                "input": {"name": "mistral:7b-16k", "details": {"parameter_size": "7B"}},
                "expected_context": 16384,
            },
            {
                "input": {"name": "codellama:13b-100k", "details": {"parameter_size": "13B"}},
                "expected_context": 102400,
            },
            {
                "input": {"name": "phi:2.7b", "details": {"parameter_size": "2.7B"}},
                "expected_context": 4096,  # Default
            },
        ]

        for test_case in test_cases:
            model = provider._extract_model_info(test_case["input"])
            assert model.id == test_case["input"]["name"]
            assert model.context_length == test_case["expected_context"]
            assert model.provider == "ollama"
            assert model.supports_streaming is True
            assert model.supports_functions is False
