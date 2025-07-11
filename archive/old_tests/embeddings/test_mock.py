"""Tests for the mock embedding provider."""

import numpy as np
import pytest

from coda.embeddings import MockEmbeddingProvider


@pytest.mark.asyncio
async def test_mock_provider_initialization():
    """Test mock provider initialization with different dimensions."""
    # Default dimension
    provider = MockEmbeddingProvider()
    assert provider.dimension == 768
    assert provider.model_id == "mock-768d"

    # Custom dimension
    provider_1024 = MockEmbeddingProvider(dimension=1024)
    assert provider_1024.dimension == 1024
    assert provider_1024.model_id == "mock-1024d"

    # Custom model ID
    provider_custom = MockEmbeddingProvider(dimension=512, model_id="test-model")
    assert provider_custom.dimension == 512
    assert provider_custom.model_id == "test-model"


@pytest.mark.asyncio
async def test_mock_provider_embed_text():
    """Test single text embedding."""
    provider = MockEmbeddingProvider(dimension=384)

    # Embed text
    result = await provider.embed_text("Hello, world!")

    # Check result structure
    assert result.text == "Hello, world!"
    assert result.model == "mock-384d"
    assert isinstance(result.embedding, np.ndarray)
    assert result.embedding.shape == (384,)
    assert result.metadata["provider"] == "mock"
    assert result.metadata["dimension"] == 384

    # Check normalization
    norm = np.linalg.norm(result.embedding)
    assert abs(norm - 1.0) < 0.001  # Should be normalized


@pytest.mark.asyncio
async def test_mock_provider_deterministic():
    """Test that embeddings are deterministic for same text."""
    provider = MockEmbeddingProvider()

    text = "Deterministic test"

    # Generate embeddings multiple times
    result1 = await provider.embed_text(text)
    result2 = await provider.embed_text(text)
    result3 = await provider.embed_text(text)

    # Should be identical
    np.testing.assert_array_equal(result1.embedding, result2.embedding)
    np.testing.assert_array_equal(result2.embedding, result3.embedding)


@pytest.mark.asyncio
async def test_mock_provider_different_texts():
    """Test that different texts produce different embeddings."""
    provider = MockEmbeddingProvider()

    # Different texts
    result1 = await provider.embed_text("First text")
    result2 = await provider.embed_text("Second text")
    result3 = await provider.embed_text("First text")  # Same as first

    # Different texts should have different embeddings
    assert not np.array_equal(result1.embedding, result2.embedding)

    # Same text should have same embedding
    np.testing.assert_array_equal(result1.embedding, result3.embedding)


@pytest.mark.asyncio
async def test_mock_provider_batch_embedding():
    """Test batch embedding using inherited implementation."""
    provider = MockEmbeddingProvider(dimension=256)

    texts = ["Text 1", "Text 2", "Text 3"]
    results = await provider.embed_batch(texts)

    assert len(results) == 3
    for i, result in enumerate(results):
        assert result.text == texts[i]
        assert result.embedding.shape == (256,)
        assert result.model == "mock-256d"


@pytest.mark.asyncio
async def test_mock_provider_delay():
    """Test delay simulation."""
    import time

    # Provider with delay
    provider = MockEmbeddingProvider(delay=0.1)

    start = time.time()
    await provider.embed_text("Test with delay")
    elapsed = time.time() - start

    # Should have taken at least 0.1 seconds
    assert elapsed >= 0.1


@pytest.mark.asyncio
async def test_mock_provider_model_info():
    """Test model info retrieval."""
    provider = MockEmbeddingProvider(dimension=512)

    info = provider.get_model_info()

    assert info["id"] == "mock-512d"
    assert info["dimensions"] == 512
    assert info["provider"] == "mock"
    assert "description" in info
    assert info["max_tokens"] == 8192
    assert info["languages"] == ["any"]


@pytest.mark.asyncio
async def test_mock_provider_list_models():
    """Test listing available models."""
    provider = MockEmbeddingProvider()

    models = await provider.list_models()

    assert len(models) == 3

    # Check model dimensions
    dimensions = [m["dimensions"] for m in models]
    assert 384 in dimensions
    assert 768 in dimensions
    assert 1024 in dimensions

    # Check all models have required fields
    for model in models:
        assert "id" in model
        assert "dimensions" in model
        assert "description" in model
        assert "max_tokens" in model
        assert "languages" in model
