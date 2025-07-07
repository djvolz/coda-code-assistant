"""
Tests for OCI embedding provider.
"""

import pytest
import numpy as np
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from coda.embeddings.oci import OCIEmbeddingProvider
from coda.embeddings.base import EmbeddingResult


class TestOCIEmbeddingProvider:
    """Tests for OCI embedding provider."""
    
    @pytest.fixture
    def mock_config(self):
        """Create mock configuration."""
        config = Mock()
        config.oci_compartment_id = "test-compartment-id"
        config.oci_config_file = "~/.oci/config"
        config.oci_profile = "DEFAULT"
        return config
        
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
        
    def test_init_with_short_name(self, mock_config):
        """Test initialization with short model name."""
        provider = OCIEmbeddingProvider("multilingual-e5", config=mock_config)
        assert provider.model_id == "multilingual-e5-base"
        
    def test_init_with_full_name(self, mock_config):
        """Test initialization with full model name."""
        provider = OCIEmbeddingProvider("cohere.embed-multilingual-v3.0", config=mock_config)
        assert provider.model_id == "cohere.embed-multilingual-v3.0"
        
    @pytest.mark.asyncio
    async def test_embed_text(self, mock_config, mock_oci_client):
        """Test embedding a single text."""
        provider = OCIEmbeddingProvider("multilingual-e5", config=mock_config)
        provider._client = mock_oci_client
        
        result = await provider.embed_text("Hello world")
        
        assert isinstance(result, EmbeddingResult)
        assert result.text == "Hello world"
        assert isinstance(result.embedding, np.ndarray)
        assert result.model == "multilingual-e5-base"
        assert result.metadata["provider"] == "oci"
        
    @pytest.mark.asyncio
    async def test_embed_batch(self, mock_config, mock_oci_client):
        """Test embedding a batch of texts."""
        provider = OCIEmbeddingProvider("multilingual-e5", config=mock_config)
        provider._client = mock_oci_client
        
        texts = ["Hello world", "How are you?"]
        results = await provider.embed_batch(texts)
        
        assert len(results) == 2
        assert all(isinstance(r, EmbeddingResult) for r in results)
        assert results[0].text == "Hello world"
        assert results[1].text == "How are you?"
        
    @pytest.mark.asyncio
    async def test_list_models(self, mock_config):
        """Test listing available models."""
        provider = OCIEmbeddingProvider(config=mock_config)
        
        models = await provider.list_models()
        
        assert len(models) > 0
        assert any(m["short_name"] == "multilingual-e5" for m in models)
        assert any(m["short_name"] == "cohere-embed" for m in models)
        
        # Check model info
        e5_model = next(m for m in models if m["short_name"] == "multilingual-e5")
        assert e5_model["dimension"] == 768
        assert e5_model["multilingual"] is True
        
    def test_get_model_info(self, mock_config):
        """Test getting current model info."""
        provider = OCIEmbeddingProvider("multilingual-e5", config=mock_config)
        
        info = provider.get_model_info()
        
        assert info["id"] == "multilingual-e5-base"
        assert info["provider"] == "oci"
        assert info["dimension"] == 768
        assert info["max_tokens"] == 512
        assert info["multilingual"] is True
        
    def test_similarity_calculation(self, mock_config):
        """Test cosine similarity calculation."""
        provider = OCIEmbeddingProvider(config=mock_config)
        
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
    async def test_error_handling(self, mock_config):
        """Test error handling in embed operations."""
        provider = OCIEmbeddingProvider("multilingual-e5", config=mock_config)
        
        # Mock client that raises an error
        mock_client = Mock()
        mock_client.embed_text.side_effect = Exception("API Error")
        provider._client = mock_client
        
        with pytest.raises(Exception) as exc_info:
            await provider.embed_text("Test text")
            
        assert "API Error" in str(exc_info.value)