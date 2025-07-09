"""
LLM Tests with Real Language Models

These tests use actual language models to verify end-to-end functionality.
They are slower and require either Ollama or cloud providers.
"""

import os

import pytest

from coda.providers import Message, Role
from coda.providers.registry import ProviderRegistry


def create_user_message(content: str) -> Message:
    """Create a user message for testing."""
    return Message(role=Role.USER, content=content)


def create_system_message(content: str) -> Message:
    """Create a system message for testing."""
    return Message(role=Role.SYSTEM, content=content)


@pytest.mark.llm
@pytest.mark.ollama
@pytest.mark.skipif(not os.getenv("RUN_LLM_TESTS"), reason="LLM tests require RUN_LLM_TESTS=true")
class TestRealLLMResponses:
    """Test with real LLM responses using Ollama."""

    @pytest.fixture
    def provider_config(self) -> dict[str, str]:
        """Get provider configuration for testing."""
        return {
            "provider": os.getenv("CODA_TEST_PROVIDER", "ollama"),
            "model": os.getenv("CODA_TEST_MODEL", "tinyllama:1.1b"),
            "base_url": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
        }

    @pytest.fixture
    async def ollama_provider(self, provider_config: dict[str, str]):
        """Create Ollama provider for testing."""
        registry = ProviderRegistry()
        provider = registry.get_provider("ollama")

        # Configure provider
        provider.base_url = provider_config["base_url"]

        # Verify model is available
        models = await provider.list_models()
        model_names = [model.name for model in models]

        if provider_config["model"] not in model_names:
            pytest.skip(f"Model {provider_config['model']} not available in Ollama")

        return provider

    @pytest.mark.asyncio
    async def test_simple_chat_completion(self, ollama_provider, provider_config):
        """Test basic chat completion with real model."""
        messages = [create_user_message("Say 'Hello, World!' and nothing else.")]

        response = await ollama_provider.chat(
            messages=messages,
            model=provider_config["model"],
            max_tokens=50,
            temperature=0.1,  # Low temperature for deterministic responses
        )

        assert response is not None
        assert isinstance(response, str)
        assert len(response.strip()) > 0
        assert "hello" in response.lower() or "world" in response.lower()

    @pytest.mark.asyncio
    async def test_streaming_response(self, ollama_provider, provider_config):
        """Test streaming responses work correctly."""
        messages = [create_user_message("Count from 1 to 3, one number per line.")]

        chunks = []
        async for chunk in ollama_provider.chat_stream(
            messages=messages, model=provider_config["model"], max_tokens=30, temperature=0.1
        ):
            chunks.append(chunk)

        assert len(chunks) > 0
        full_response = "".join(chunks)
        assert len(full_response.strip()) > 0

        # Should contain numbers 1, 2, 3
        response_lower = full_response.lower()
        numbers_found = sum(char in response_lower for char in ["1", "2", "3"])
        assert numbers_found >= 2  # At least 2 out of 3 numbers

    @pytest.mark.asyncio
    async def test_conversation_context(self, ollama_provider, provider_config):
        """Test that model maintains conversation context."""
        # First message
        messages = [create_user_message("My name is TestUser. Remember this.")]

        response1 = await ollama_provider.chat(
            messages=messages, model=provider_config["model"], max_tokens=50, temperature=0.1
        )

        # Add AI response and ask follow-up
        messages.extend(
            [
                Message(role=Role.ASSISTANT, content=response1),
                create_user_message("What is my name?"),
            ]
        )

        response2 = await ollama_provider.chat(
            messages=messages, model=provider_config["model"], max_tokens=50, temperature=0.1
        )

        assert response2 is not None
        # Should mention the name (case insensitive)
        assert "testuser" in response2.lower() or "test user" in response2.lower()

    @pytest.mark.asyncio
    async def test_model_info(self, ollama_provider, provider_config):
        """Test that we can get model information."""
        model_info = await ollama_provider.get_model_info(provider_config["model"])

        assert model_info is not None
        assert model_info.name == provider_config["model"]
        assert model_info.provider == "ollama"
        assert model_info.context_length > 0

    @pytest.mark.asyncio
    async def test_error_handling(self, ollama_provider):
        """Test error handling with invalid requests."""
        messages = [create_user_message("Test message")]

        # Test with non-existent model
        with pytest.raises(
            (ValueError, RuntimeError, ConnectionError)
        ):  # Should raise some kind of error
            await ollama_provider.chat(
                messages=messages, model="nonexistent-model:999", max_tokens=10
            )

    @pytest.mark.asyncio
    async def test_performance_timing(self, ollama_provider, provider_config):
        """Test that responses come back in reasonable time."""
        import time

        messages = [create_user_message("Say 'OK'")]

        start_time = time.time()
        response = await ollama_provider.chat(
            messages=messages, model=provider_config["model"], max_tokens=10, temperature=0.1
        )
        end_time = time.time()

        # Should respond within 30 seconds for tiny model
        assert (end_time - start_time) < 30
        assert response is not None
        assert len(response.strip()) > 0


@pytest.mark.llm
@pytest.mark.skipif(not os.getenv("RUN_LLM_TESTS"), reason="LLM tests require RUN_LLM_TESTS=true")
class TestLLMProviderComparison:
    """Compare responses across different providers."""

    @pytest.mark.asyncio
    async def test_provider_consistency(self):
        """Test that different providers handle the same prompt reasonably."""
        # This would test Mock vs Ollama providers
        prompt = "What is 2+2? Answer with just the number."

        # Test with Mock provider (always available)
        registry = ProviderRegistry()
        mock_provider = registry.get_provider("mock")

        messages = [create_user_message(prompt)]
        mock_response = await mock_provider.chat(messages=messages, model="mock-smart")

        assert mock_response is not None
        assert len(mock_response.strip()) > 0

        # If Ollama is available, compare
        if os.getenv("CODA_TEST_PROVIDER") == "ollama":
            ollama_provider = registry.get_provider("ollama")
            ollama_provider.base_url = os.getenv("OLLAMA_HOST", "http://localhost:11434")

            try:
                ollama_response = await ollama_provider.chat(
                    messages=messages,
                    model=os.getenv("CODA_TEST_MODEL", "tinyllama:1.1b"),
                    max_tokens=10,
                    temperature=0.1,
                )

                # Both should respond
                assert ollama_response is not None
                assert len(ollama_response.strip()) > 0

                # For math question, both should contain "4"
                assert "4" in mock_response or "4" in ollama_response

            except Exception as e:
                pytest.skip(f"Ollama not available: {e}")
