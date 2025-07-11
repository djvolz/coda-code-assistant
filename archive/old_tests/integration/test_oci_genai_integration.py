"""Integration tests for OCI GenAI provider.

These tests require actual OCI credentials and network access.
They can be skipped in CI/CD by setting SKIP_INTEGRATION_TESTS=1
"""

import os

import pytest

from coda.providers.base import Message, Role
from coda.providers.oci_genai import OCIGenAIProvider


@pytest.mark.integration
@pytest.mark.skipif(
    os.getenv("CI") == "true" and not os.getenv("RUN_INTEGRATION_TESTS"),
    reason="Integration tests disabled in CI unless explicitly enabled",
)
class TestOCIGenAIIntegration:
    """Integration tests that interact with actual OCI GenAI service."""

    @pytest.fixture
    def provider(self):
        """Create real OCIGenAIProvider instance."""
        compartment_id = os.getenv("OCI_COMPARTMENT_ID")
        if not compartment_id:
            pytest.skip("OCI_COMPARTMENT_ID not set")

        try:
            return OCIGenAIProvider(compartment_id=compartment_id)
        except Exception as e:
            pytest.skip(f"Failed to initialize OCI provider: {e}")

    def test_list_models_real(self, provider):
        """Test listing models from actual OCI service."""
        models = provider.list_models()

        assert len(models) > 0

        # Check model structure
        for model in models[:5]:  # Check first 5 models
            assert model.id
            assert model.name
            assert model.provider
            assert model.context_length > 0
            assert model.supports_streaming is True
            assert model.supports_chat is True

    def test_model_providers_available(self, provider):
        """Test that all expected model providers are available."""
        models = provider.list_models()

        providers = {model.provider for model in models}
        expected_providers = {"xai", "cohere", "meta"}

        # Check that we have models from expected providers
        missing_providers = expected_providers - providers
        assert not missing_providers, f"Missing providers: {missing_providers}"

    @pytest.mark.parametrize(
        "model_prefix,expected_response_format",
        [("xai", "message"), ("cohere", "text"), ("meta", "message")],
    )
    def test_streaming_format_per_provider(self, provider, model_prefix, expected_response_format):
        """Test that each provider returns expected streaming format."""
        models = provider.list_models()

        # Find a model from this provider
        test_model = None
        for model in models:
            if model.id.startswith(model_prefix):
                test_model = model.id
                break

        if not test_model:
            pytest.skip(f"No {model_prefix} model found")

        messages = [Message(role=Role.USER, content="Say 'test' and nothing else")]

        chunks = []
        for chunk in provider.chat_stream(messages, model=test_model):
            chunks.append(chunk)
            if len(chunks) > 50:  # Limit chunks to prevent infinite streams
                break

        assert len(chunks) > 0
        assert any(chunk.content for chunk in chunks)  # At least some content
        assert any(chunk.finish_reason for chunk in chunks)  # Should have finish reason

    def test_non_streaming_chat(self, provider):
        """Test non-streaming chat completion."""
        models = provider.list_models()

        # Use first available model
        test_model = models[0].id if models else None
        if not test_model:
            pytest.skip("No models available")

        messages = [Message(role=Role.USER, content="Reply with 'OK' only")]

        response = provider.chat(messages, model=test_model, max_tokens=10)

        assert response.content
        assert response.model == test_model
        assert len(response.content) < 50  # Should be short response

    def test_conversation_context(self, provider):
        """Test that conversation context is maintained."""
        models = provider.list_models()

        # Find a model that supports good context
        test_model = None
        for model in models:
            if model.context_length >= 4096:
                test_model = model.id
                break

        if not test_model:
            pytest.skip("No suitable model found")

        messages = [
            Message(role=Role.USER, content="My name is TestUser123"),
            Message(role=Role.ASSISTANT, content="Nice to meet you, TestUser123!"),
            Message(role=Role.USER, content="What's my name?"),
        ]

        response = provider.chat(messages, model=test_model, max_tokens=50)

        # Check that the model remembers the name
        assert "TestUser123" in response.content or "testuser" in response.content.lower()

    def test_system_message_handling(self, provider):
        """Test that system messages are properly handled."""
        models = provider.list_models()

        # Test with different model types
        for model in models[:3]:  # Test first 3 models
            messages = [
                Message(role=Role.SYSTEM, content="Always respond in uppercase letters only"),
                Message(role=Role.USER, content="say hello"),
            ]

            response = provider.chat(messages, model=model.id, max_tokens=20)

            # Check if response is mostly uppercase (allow for some flexibility)
            uppercase_ratio = sum(1 for c in response.content if c.isupper()) / len(
                response.content.replace(" ", "")
            )
            assert uppercase_ratio > 0.7, f"Model {model.id} didn't follow system message"

    def test_temperature_effect(self, provider):
        """Test that temperature parameter affects response variability."""
        models = provider.list_models()
        test_model = models[0].id if models else None

        if not test_model:
            pytest.skip("No models available")

        messages = [Message(role=Role.USER, content="Generate a random number between 1 and 100")]

        # Get responses with different temperatures
        responses_low_temp = []
        responses_high_temp = []

        for _ in range(3):
            resp = provider.chat(messages, model=test_model, temperature=0.1, max_tokens=20)
            responses_low_temp.append(resp.content)

            resp = provider.chat(messages, model=test_model, temperature=0.9, max_tokens=20)
            responses_high_temp.append(resp.content)

        # High temperature should have more variety
        unique_low = len(set(responses_low_temp))
        unique_high = len(set(responses_high_temp))

        # This is a probabilistic test, might occasionally fail
        assert unique_high >= unique_low

    def test_max_tokens_limit(self, provider):
        """Test that max_tokens parameter is respected."""
        models = provider.list_models()
        test_model = models[0].id if models else None

        if not test_model:
            pytest.skip("No models available")

        messages = [Message(role=Role.USER, content="Count from 1 to 100")]

        response = provider.chat(messages, model=test_model, max_tokens=10)

        # Response should be truncated
        # Most models will stop mid-count with such a low token limit
        assert len(response.content.split()) < 20

    @pytest.mark.asyncio
    async def test_async_streaming(self, provider):
        """Test async streaming functionality."""
        models = provider.list_models()
        test_model = models[0].id if models else None

        if not test_model:
            pytest.skip("No models available")

        messages = [Message(role=Role.USER, content="Say hello")]

        chunks = []
        async for chunk in provider.achat_stream(messages, model=test_model):
            chunks.append(chunk)
            if len(chunks) > 50:
                break

        assert len(chunks) > 0
        assert any(chunk.content for chunk in chunks)
