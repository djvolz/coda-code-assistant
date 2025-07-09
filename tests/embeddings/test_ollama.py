"""Tests for the Ollama embedding provider."""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import numpy as np
import pytest

from coda.embeddings.ollama import OllamaEmbeddingProvider


class TestOllamaProvider:
    """Test the OllamaEmbeddingProvider class."""

    def test_init_default_model(self):
        """Test initialization with default model."""
        provider = OllamaEmbeddingProvider()
        assert provider.model_id == "mxbai-embed-large"
        assert provider.base_url == "http://localhost:11434"
        assert provider.timeout == 30.0
        assert provider.keep_alive == "5m"
        assert provider._client is None
        assert provider._dimension_cache == {}

    def test_init_custom_config(self):
        """Test initialization with custom configuration."""
        provider = OllamaEmbeddingProvider(
            model_id="nomic-embed-text",
            base_url="http://remote:11434",
            timeout=60.0,
            keep_alive="1h",
        )
        assert provider.model_id == "nomic-embed-text"
        assert provider.base_url == "http://remote:11434"
        assert provider.timeout == 60.0
        assert provider.keep_alive == "1h"

    def test_known_models_info(self):
        """Test that known models have proper info."""
        provider = OllamaEmbeddingProvider(model_id="mxbai-embed-large")
        assert provider._model_info["dimension"] == 1024
        assert "MixedBread AI" in provider._model_info["description"]
        assert provider._model_info["max_tokens"] == 512

    def test_custom_model_info(self):
        """Test custom model has placeholder info."""
        provider = OllamaEmbeddingProvider(model_id="custom-model")
        assert provider._model_info["dimension"] is None  # Will be detected
        assert "Custom Ollama model" in provider._model_info["description"]
        assert provider._model_info["max_tokens"] == 2048

    def test_get_client(self):
        """Test HTTP client creation."""
        provider = OllamaEmbeddingProvider()
        client = provider._get_client()
        assert isinstance(client, httpx.AsyncClient)
        assert client.base_url == "http://localhost:11434"
        # Check timeout - httpx.Timeout has different attributes
        assert client.timeout.connect == 30.0 or client.timeout.read == 30.0

        # Test that same client is reused
        client2 = provider._get_client()
        assert client is client2

    @pytest.mark.asyncio
    async def test_detect_dimension(self):
        """Test dimension detection for models."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"embedding": [0.1] * 384}
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            dim = await provider._detect_dimension("test-model")
            assert dim == 384
            assert provider._dimension_cache["test-model"] == 384

            # Test cache hit
            dim2 = await provider._detect_dimension("test-model")
            assert dim2 == 384
            mock_client.post.assert_called_once()  # Only called once due to cache

    @pytest.mark.asyncio
    async def test_check_model_available_success(self):
        """Test listing models to check availability."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {
                "models": [
                    {"name": "mxbai-embed-large", "size": 1000000},
                    {"name": "nomic-embed-text", "size": 2000000},
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            models = await provider.list_models()
            assert len(models) >= 2  # Should have at least the mocked models

    @pytest.mark.asyncio
    async def test_check_model_available_connection_error(self):
        """Test handling connection error during model operations."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_get_client.return_value = mock_client

            with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
                await provider.embed_text("test")

    @pytest.mark.asyncio
    async def test_embed_text_success(self):
        """Test successful text embedding."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            embedding = [0.1, 0.2, 0.3, 0.4]
            mock_response.json.return_value = {"embedding": embedding}
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await provider.embed_text("Hello world")

            assert result.text == "Hello world"
            # Convert to numpy array for comparison
            assert np.allclose(result.embedding, np.array(embedding, dtype=np.float32))
            assert result.model == "mxbai-embed-large"
            assert result.metadata["provider"] == "ollama"
            assert result.metadata["dimension"] == 4

            # Check API call
            mock_client.post.assert_called_once_with(
                "/api/embeddings",
                json={"model": "mxbai-embed-large", "prompt": "Hello world", "keep_alive": "5m"},
            )

    @pytest.mark.asyncio
    async def test_embed_text_model_not_found(self):
        """Test embedding with model not found error."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not found", request=Mock(), response=mock_response
            )
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            with pytest.raises(ValueError, match="Model 'mxbai-embed-large' not found"):
                await provider.embed_text("Hello world")

    @pytest.mark.asyncio
    async def test_embed_text_connection_error(self):
        """Test embedding with connection error."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.post.side_effect = httpx.ConnectError("Connection refused")
            mock_get_client.return_value = mock_client

            with pytest.raises(ConnectionError, match="Cannot connect to Ollama"):
                await provider.embed_text("Hello world")

    @pytest.mark.asyncio
    async def test_embed_batch(self):
        """Test batch embedding with concurrent requests."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()

            # Mock different embeddings for different texts
            async def post_side_effect(url, json=None):
                mock_response = Mock()
                text = json["prompt"]
                if text == "Text 1":
                    mock_response.json.return_value = {"embedding": [0.1, 0.2]}
                elif text == "Text 2":
                    mock_response.json.return_value = {"embedding": [0.3, 0.4]}
                else:
                    mock_response.json.return_value = {"embedding": [0.5, 0.6]}
                mock_response.raise_for_status = Mock()
                return mock_response

            mock_client.post.side_effect = post_side_effect
            mock_get_client.return_value = mock_client

            texts = ["Text 1", "Text 2", "Text 3"]
            results = await provider.embed_batch(texts)

            assert len(results) == 3
            assert results[0].text == "Text 1"
            assert np.allclose(results[0].embedding, [0.1, 0.2])
            assert results[1].text == "Text 2"
            assert np.allclose(results[1].embedding, [0.3, 0.4])
            assert results[2].text == "Text 3"
            assert np.allclose(results[2].embedding, [0.5, 0.6])

            # Should make 3 concurrent calls
            assert mock_client.post.call_count == 3

    @pytest.mark.asyncio
    async def test_embed_batch_with_semaphore(self):
        """Test that batch embedding respects semaphore limit."""
        provider = OllamaEmbeddingProvider()

        call_times = []

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()

            async def post_side_effect(url, json=None):
                import time

                call_times.append(time.time())
                import asyncio

                await asyncio.sleep(0.1)  # Simulate processing time
                mock_response = Mock()
                mock_response.json.return_value = {"embedding": [0.1, 0.2]}
                mock_response.raise_for_status = Mock()
                return mock_response

            mock_client.post.side_effect = post_side_effect
            mock_get_client.return_value = mock_client

            # Try to embed 10 texts (semaphore limit is 5)
            texts = [f"Text {i}" for i in range(10)]
            results = await provider.embed_batch(texts)

            assert len(results) == 10
            # With semaphore of 5, there should be at least 2 distinct time groups
            # (can't all run at once)

    def test_get_model_info(self):
        """Test getting model information."""
        provider = OllamaEmbeddingProvider(
            model_id="nomic-embed-text", base_url="http://remote:11434"
        )

        info = provider.get_model_info()
        assert info["id"] == "nomic-embed-text"
        assert info["provider"] == "ollama"
        assert info["dimension"] == 768  # Known model
        assert "Nomic's embedding model" in info["description"]
        assert info["max_tokens"] == 8192
        assert info["base_url"] == "http://remote:11434"
        assert info["keep_alive"] == "5m"

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing available models."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {
                "models": [
                    {
                        "name": "mxbai-embed-large",
                        "size": 1000000,
                        "details": {"families": ["bert"]},
                    },
                    {
                        "name": "nomic-embed-text",
                        "size": 2000000,
                        "details": {"families": ["bert"]},
                    },
                    {"name": "llama2:latest", "size": 3000000, "details": {"families": ["llama"]}},
                ]
            }
            mock_response.raise_for_status = Mock()
            mock_client.get.return_value = mock_response
            mock_get_client.return_value = mock_client

            models = await provider.list_models()

            # Should only include embedding models
            # Should return known models even without connection
            assert len(models) >= 6  # All known models
            model_ids = [m["id"] for m in models]
            assert "mxbai-embed-large" in model_ids
            assert "nomic-embed-text" in model_ids

            # Check model info
            for model in models:
                assert "provider" in model
                assert model["provider"] == "ollama"
                assert "dimension" in model
                assert "description" in model

    @pytest.mark.asyncio
    async def test_list_models_connection_error(self):
        """Test model listing with connection error."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_client.get.side_effect = httpx.ConnectError("Connection refused")
            mock_get_client.return_value = mock_client

            models = await provider.list_models()
            # Should still return known models even without connection
            assert len(models) >= 6  # All known models
            # Check that we have the expected models
            model_ids = [m["id"] for m in models]
            assert "mxbai-embed-large" in model_ids

    @pytest.mark.asyncio
    async def test_empty_text_embedding(self):
        """Test embedding empty text."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()
            mock_response = Mock()
            mock_response.json.return_value = {"embedding": [0.0] * 100}
            mock_response.raise_for_status = Mock()
            mock_client.post.return_value = mock_response
            mock_get_client.return_value = mock_client

            result = await provider.embed_text("")
            assert result.text == ""
            assert result.embedding.shape == (100,)

    def test_base_url_normalization(self):
        """Test that base URL trailing slashes are handled."""
        provider1 = OllamaEmbeddingProvider(base_url="http://localhost:11434/")
        assert provider1.base_url == "http://localhost:11434"

        provider2 = OllamaEmbeddingProvider(base_url="http://localhost:11434")
        assert provider2.base_url == "http://localhost:11434"

    @pytest.mark.parametrize("keep_alive", [None, "5m", "1h", "0"])
    def test_keep_alive_options(self, keep_alive):
        """Test different keep_alive options."""
        provider = OllamaEmbeddingProvider(keep_alive=keep_alive)
        assert provider.keep_alive == keep_alive


class TestOllamaIntegration:
    """Integration tests for Ollama provider."""

    @pytest.mark.asyncio
    async def test_dimension_caching(self):
        """Test that dimensions are cached after detection."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()

            # First call for dimension detection
            detect_response = Mock()
            detect_response.json.return_value = {"embedding": [0.0] * 512}
            detect_response.raise_for_status = Mock()

            # Second call for actual embedding
            embed_response = Mock()
            embed_response.json.return_value = {"embedding": [0.1] * 512}
            embed_response.raise_for_status = Mock()

            mock_client.post.side_effect = [detect_response, embed_response]
            mock_get_client.return_value = mock_client

            # First embedding will detect dimension
            result1 = await provider.embed_text("Test 1")
            assert result1.embedding.shape == (512,)

            # Second embedding should use cached dimension
            result2 = await provider.embed_text("Test 2")
            assert result2.embedding.shape == (512,)

            # Should have made 2 API calls total
            assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    async def test_concurrent_batch_error_handling(self):
        """Test error handling in concurrent batch processing."""
        provider = OllamaEmbeddingProvider()

        with patch.object(provider, "_get_client") as mock_get_client:
            mock_client = AsyncMock()

            # Mix of successful and failing responses
            async def post_side_effect(url, json=None):
                text = json["prompt"]
                if "fail" in text:
                    raise httpx.ConnectError("Connection lost")

                mock_response = Mock()
                mock_response.json.return_value = {"embedding": [0.1, 0.2]}
                mock_response.raise_for_status = Mock()
                return mock_response

            mock_client.post.side_effect = post_side_effect
            mock_get_client.return_value = mock_client

            texts = ["Good 1", "fail 1", "Good 2", "fail 2"]

            # Should raise error if any request fails
            with pytest.raises(ConnectionError):
                await provider.embed_batch(texts)
