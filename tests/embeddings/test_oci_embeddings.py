"""
Tests for OCI embedding provider.
"""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from coda.embeddings.base import EmbeddingResult
from coda.embeddings.oci import OCIEmbeddingProvider


class TestOCIEmbeddingProvider:
    """Tests for OCI embedding provider."""

    @pytest.fixture
    def compartment_id(self):
        """Test compartment ID."""
        return "test-compartment-id"

    @pytest.fixture
    def mock_oci_client(self):
        """Create mock OCI client."""
        client = Mock()

        # Mock embed_text response
        response = Mock()
        response.data.embeddings = [
            [0.1, 0.2, 0.3] * 256,  # 768-dim embedding
            [0.4, 0.5, 0.6] * 256,
        ]
        client.embed_text.return_value = response

        return client

    def test_init_with_short_name(self, compartment_id):
        """Test initialization with short model name."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id, "multilingual-e5")
            # multilingual-e5 is now an alias for cohere.embed-multilingual-v3.0
            assert provider.model_id == "cohere.embed-multilingual-v3.0"

    def test_init_with_full_name(self, compartment_id):
        """Test initialization with full model name."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id, "cohere.embed-multilingual-v3.0")
            assert provider.model_id == "cohere.embed-multilingual-v3.0"

    @pytest.mark.asyncio
    async def test_embed_text(self, compartment_id, mock_oci_client):
        """Test embedding a single text."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id, "multilingual-e5")
            provider._client = mock_oci_client

            result = await provider.embed_text("Hello world")

            assert isinstance(result, EmbeddingResult)
            assert result.text == "Hello world"
            assert isinstance(result.embedding, np.ndarray)
            assert result.model == "cohere.embed-multilingual-v3.0"
            assert result.metadata["provider"] == "oci"

    @pytest.mark.asyncio
    async def test_embed_batch(self, compartment_id, mock_oci_client):
        """Test embedding a batch of texts."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id, "multilingual-e5")
            provider._client = mock_oci_client

        texts = ["Hello world", "How are you?"]
        results = await provider.embed_batch(texts)

        assert len(results) == 2
        assert all(isinstance(r, EmbeddingResult) for r in results)
        assert results[0].text == "Hello world"
        assert results[1].text == "How are you?"

    @pytest.mark.asyncio
    async def test_list_models(self, compartment_id):
        """Test listing available models."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id)

        models = await provider.list_models()

        assert len(models) > 0
        assert any(m["id"] == "cohere.embed-english-v3.0" for m in models)
        assert any(m["id"] == "cohere.embed-multilingual-v3.0" for m in models)

        # Check model info
        multilingual_model = next(m for m in models if m["id"] == "cohere.embed-multilingual-v3.0")
        assert multilingual_model["dimensions"] == 1024
        assert multilingual_model["languages"] == ["multilingual"]

    def test_get_model_info(self, compartment_id):
        """Test getting current model info."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id, "multilingual-e5")

        info = provider.get_model_info()

        assert info["id"] == "cohere.embed-multilingual-v3.0"
        assert info["provider"] == "oci"
        assert info["dimensions"] == 1024  # cohere.embed-multilingual-v3.0 has 1024 dimensions
        assert info["max_tokens"] == 512
        assert info["languages"] == ["multilingual"]

    def test_similarity_calculation(self, compartment_id):
        """Test cosine similarity calculation."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id)

        # Test with identical vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([1.0, 0.0, 0.0])
        sim = provider.similarity(vec1, vec2)
        assert pytest.approx(sim) == 1.0

        # Test with orthogonal vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([0.0, 1.0, 0.0])
        sim = provider.similarity(vec1, vec2)
        assert pytest.approx(sim) == 0.0

        # Test with opposite vectors
        vec1 = np.array([1.0, 0.0, 0.0])
        vec2 = np.array([-1.0, 0.0, 0.0])
        sim = provider.similarity(vec1, vec2)
        assert pytest.approx(sim) == -1.0

    @pytest.mark.asyncio
    async def test_error_handling(self, compartment_id):
        """Test error handling in embed operations."""
        with patch("oci.config.from_file", return_value={"region": "us-chicago-1"}):
            provider = OCIEmbeddingProvider(compartment_id, "multilingual-e5")

        # Mock client that raises an error
        mock_client = Mock()
        mock_client.embed_text.side_effect = Exception("API Error")
        provider._client = mock_client

        with pytest.raises(Exception) as exc_info:
            await provider.embed_text("Test text")

        assert "API Error" in str(exc_info.value)
