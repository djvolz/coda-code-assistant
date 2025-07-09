"""Tests for embedding providers."""

import numpy as np
import pytest

from coda.embeddings import (
    EmbeddingProviderFactory,
    MockEmbeddingProvider,
    OllamaEmbeddingProvider,
    SentenceTransformersProvider,
)


@pytest.mark.asyncio
async def test_mock_provider():
    """Test mock embedding provider."""
    provider = MockEmbeddingProvider(dimension=768)

    # Test single embedding
    result = await provider.embed_text("Hello world")
    assert result.text == "Hello world"
    assert result.embedding.shape == (768,)
    assert result.model == "mock-768d"

    # Test batch embedding
    texts = ["Hello", "World", "Test"]
    results = await provider.embed_batch(texts)
    assert len(results) == 3
    assert all(r.embedding.shape == (768,) for r in results)

    # Test model info
    info = provider.get_model_info()
    assert info["dimension"] == 768
    assert info["provider"] == "mock"

    # Test list models
    models = await provider.list_models()
    assert len(models) >= 3
    assert any(m["id"] == "mock-768d" for m in models)


@pytest.mark.asyncio
async def test_sentence_transformers_provider():
    """Test sentence-transformers provider."""
    provider = SentenceTransformersProvider(model_id="all-MiniLM-L6-v2")

    # Test single embedding
    result = await provider.embed_text("Python programming")
    assert result.text == "Python programming"
    assert result.embedding.shape == (384,)  # MiniLM-L6 has 384 dimensions
    assert result.model == "all-MiniLM-L6-v2"

    # Test batch embedding
    texts = ["Machine learning", "Data science", "AI"]
    results = await provider.embed_batch(texts)
    assert len(results) == 3
    assert all(r.embedding.shape == (384,) for r in results)

    # Test normalization
    for r in results:
        norm = np.linalg.norm(r.embedding)
        assert abs(norm - 1.0) < 0.001  # Should be unit normalized

    # Test similarity
    sim = provider.similarity(results[0].embedding, results[1].embedding)
    assert -1.0 <= sim <= 1.0


@pytest.mark.asyncio
async def test_ollama_provider_mock():
    """Test Ollama provider with mocked responses."""
    # This test doesn't require Ollama to be running
    provider = OllamaEmbeddingProvider(model_id="test-model")

    # Test model info
    info = provider.get_model_info()
    assert info["provider"] == "ollama"
    assert info["base_url"] == "http://localhost:11434"

    # Test list models
    models = await provider.list_models()
    assert len(models) >= 6  # At least the known models
    assert any(m["id"] == "mxbai-embed-large" for m in models)


def test_embedding_provider_factory():
    """Test the embedding provider factory."""
    # Test listing providers
    providers = EmbeddingProviderFactory.list_providers()
    assert "mock" in providers
    assert "sentence-transformers" in providers
    assert "ollama" in providers
    assert "oci" in providers

    # Test creating providers
    mock = EmbeddingProviderFactory.create_provider("mock")
    assert isinstance(mock, MockEmbeddingProvider)

    st = EmbeddingProviderFactory.create_provider("sentence-transformers")
    assert isinstance(st, SentenceTransformersProvider)

    ollama = EmbeddingProviderFactory.create_provider("ollama")
    assert isinstance(ollama, OllamaEmbeddingProvider)

    # Test aliases
    local = EmbeddingProviderFactory.create_provider("local")
    assert isinstance(local, SentenceTransformersProvider)

    sbert = EmbeddingProviderFactory.create_provider("sbert")
    assert isinstance(sbert, SentenceTransformersProvider)

    # Test invalid provider
    with pytest.raises(ValueError, match="Unknown provider type"):
        EmbeddingProviderFactory.create_provider("invalid")


def test_provider_info():
    """Test getting provider information."""
    # Test each provider
    for provider_type in ["mock", "sentence-transformers", "ollama", "oci"]:
        info = EmbeddingProviderFactory.get_provider_info(provider_type)
        assert "description" in info
        assert "requires_auth" in info
        assert "requires_internet" in info
        assert "default_model" in info
        assert "example_models" in info


@pytest.mark.asyncio
async def test_deterministic_mock_embeddings():
    """Test that mock embeddings are deterministic."""
    provider = MockEmbeddingProvider(dimension=768)

    # Same text should produce same embedding
    text = "Deterministic test"
    result1 = await provider.embed_text(text)
    result2 = await provider.embed_text(text)

    assert np.allclose(result1.embedding, result2.embedding)

    # Different text should produce different embedding
    result3 = await provider.embed_text("Different text")
    assert not np.allclose(result1.embedding, result3.embedding)
