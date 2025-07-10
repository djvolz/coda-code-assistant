"""Tests for the sentence-transformers embedding provider."""

from unittest.mock import Mock, patch

import numpy as np
import pytest

from coda.embeddings.sentence_transformers import SentenceTransformersProvider


class TestSentenceTransformersProvider:
    """Test the SentenceTransformersProvider class."""

    def test_init_default_model(self):
        """Test initialization with default model."""
        provider = SentenceTransformersProvider()
        assert provider.model_id == "all-MiniLM-L6-v2"
        assert provider.device is None
        assert provider.batch_size == 32
        assert provider.show_progress is False
        assert provider.normalize_embeddings is True
        assert provider._model is None  # Lazy loading

    def test_init_custom_model(self):
        """Test initialization with custom model."""
        provider = SentenceTransformersProvider(
            model_id="all-mpnet-base-v2",
            device="cuda",
            batch_size=64,
            show_progress=True,
            normalize_embeddings=False,
        )
        assert provider.model_id == "all-mpnet-base-v2"
        assert provider.device == "cuda"
        assert provider.batch_size == 64
        assert provider.show_progress is True
        assert provider.normalize_embeddings is False

    def test_known_models_info(self):
        """Test that known models have proper info."""
        provider = SentenceTransformersProvider(model_id="all-MiniLM-L6-v2")
        assert provider._model_info["dimension"] == 384
        assert "Fast and lightweight" in provider._model_info["description"]
        assert provider._model_info["max_tokens"] == 256

    def test_custom_model_info(self):
        """Test custom model has placeholder info."""
        provider = SentenceTransformersProvider(model_id="custom-model")
        assert provider._model_info["dimension"] is None  # Will be detected
        assert "Custom model" in provider._model_info["description"]
        assert provider._model_info["max_tokens"] == 512

    @patch("sentence_transformers.SentenceTransformer")
    def test_ensure_model_loaded(self, mock_st_class):
        """Test lazy model loading."""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1] * 384)
        mock_st_class.return_value = mock_model

        provider = SentenceTransformersProvider()
        assert provider._model is None

        provider._ensure_model_loaded()
        assert provider._model is mock_model
        mock_st_class.assert_called_once_with("all-MiniLM-L6-v2", device=None)

        # Test dimension detection for unknown model
        assert provider._model_info["dimension"] == 384

    def test_ensure_model_loaded_import_error(self):
        """Test handling of missing sentence-transformers library."""
        # Mock the import to fail
        with patch.dict("sys.modules", {"sentence_transformers": None}):
            provider = SentenceTransformersProvider()
            with pytest.raises(ImportError, match="sentence-transformers is not installed"):
                provider._ensure_model_loaded()

    @pytest.mark.asyncio
    @patch("sentence_transformers.SentenceTransformer")
    async def test_embed_text(self, mock_st_class):
        """Test embedding a single text."""
        mock_model = Mock()
        mock_embedding = np.array([0.1, 0.2, 0.3])
        mock_model.encode.return_value = mock_embedding
        mock_st_class.return_value = mock_model

        provider = SentenceTransformersProvider()
        result = await provider.embed_text("Hello world")

        assert result.text == "Hello world"
        assert np.array_equal(result.embedding, mock_embedding)
        assert result.model == "all-MiniLM-L6-v2"
        assert result.metadata["provider"] == "sentence-transformers"
        assert result.metadata["dimension"] == 3
        assert result.metadata["normalized"] is True

        mock_model.encode.assert_called_once()
        call_args = mock_model.encode.call_args
        assert call_args[0][0] == "Hello world"
        assert call_args[1]["normalize_embeddings"] is True
        assert call_args[1]["show_progress_bar"] is False
        assert call_args[1]["convert_to_numpy"] is True

    @pytest.mark.asyncio
    @patch("sentence_transformers.SentenceTransformer")
    async def test_embed_batch(self, mock_st_class):
        """Test embedding a batch of texts."""
        mock_model = Mock()
        mock_embeddings = np.array([[0.1, 0.2, 0.3], [0.4, 0.5, 0.6], [0.7, 0.8, 0.9]])
        mock_model.encode.return_value = mock_embeddings
        mock_st_class.return_value = mock_model

        provider = SentenceTransformersProvider(batch_size=2, show_progress=True)
        texts = ["Text 1", "Text 2", "Text 3"]
        results = await provider.embed_batch(texts)

        assert len(results) == 3
        for i, result in enumerate(results):
            assert result.text == texts[i]
            assert np.array_equal(result.embedding, mock_embeddings[i])
            assert result.model == "all-MiniLM-L6-v2"
            assert result.metadata["provider"] == "sentence-transformers"
            assert result.metadata["dimension"] == 3
            assert result.metadata["normalized"] is True

        mock_model.encode.assert_called_once()
        call_args = mock_model.encode.call_args
        assert call_args[0][0] == texts
        assert call_args[1]["batch_size"] == 2
        assert call_args[1]["normalize_embeddings"] is True
        assert call_args[1]["show_progress_bar"] is True
        assert call_args[1]["convert_to_numpy"] is True

    @pytest.mark.asyncio
    async def test_embed_empty_text(self):
        """Test embedding empty text."""
        with patch("sentence_transformers.SentenceTransformer") as mock_st_class:
            mock_model = Mock()
            mock_model.encode.return_value = np.zeros(384)
            mock_st_class.return_value = mock_model

            provider = SentenceTransformersProvider()
            result = await provider.embed_text("")

            assert result.text == ""
            assert result.embedding.shape == (384,)

    @pytest.mark.asyncio
    async def test_embed_empty_batch(self):
        """Test embedding empty batch."""
        provider = SentenceTransformersProvider()
        results = await provider.embed_batch([])
        assert results == []

    @patch("sentence_transformers.SentenceTransformer")
    def test_get_model_info(self, mock_st_class):
        """Test getting model information."""
        mock_model = Mock()
        mock_model.device = "cuda:0"
        mock_model.encode.return_value = np.zeros(768)
        mock_st_class.return_value = mock_model

        provider = SentenceTransformersProvider(
            model_id="all-mpnet-base-v2", device="cuda", normalize_embeddings=False
        )
        provider._ensure_model_loaded()

        info = provider.get_model_info()
        assert info["id"] == "all-mpnet-base-v2"
        assert info["provider"] == "sentence-transformers"
        assert info["dimension"] == 768
        assert "High-quality model" in info["description"]
        assert info["max_tokens"] == 384
        assert info["device"] == "cuda:0"
        assert info["normalize_embeddings"] is False

    @pytest.mark.asyncio
    async def test_list_models(self):
        """Test listing available models."""
        provider = SentenceTransformersProvider()
        models = await provider.list_models()

        assert len(models) > 5  # Should have several models plus custom

        # Check known models
        model_ids = [m["id"] for m in models]
        assert "all-MiniLM-L6-v2" in model_ids
        assert "all-mpnet-base-v2" in model_ids
        assert "paraphrase-multilingual-mpnet-base-v2" in model_ids
        assert "custom" in model_ids

        # Check model info structure
        for model in models:
            if model["id"] != "custom":
                assert "provider" in model
                assert "dimension" in model
                assert "description" in model
                assert "max_tokens" in model
                assert model["provider"] == "sentence-transformers"

    @pytest.mark.asyncio
    @patch("asyncio.get_event_loop")
    @patch("sentence_transformers.SentenceTransformer")
    async def test_async_execution(self, mock_st_class, mock_get_loop):
        """Test that encoding runs in executor for async compatibility."""
        mock_model = Mock()
        mock_model.encode.return_value = np.array([0.1, 0.2, 0.3])
        mock_st_class.return_value = mock_model

        mock_loop = Mock()
        # Create a future that will resolve to the numpy array
        import asyncio

        future = asyncio.Future()
        future.set_result(np.array([0.1, 0.2, 0.3]))
        mock_loop.run_in_executor.return_value = future
        mock_get_loop.return_value = mock_loop

        provider = SentenceTransformersProvider()
        result = await provider.embed_text("Test")

        # Verify it used the executor
        mock_loop.run_in_executor.assert_called_once()
        assert result.embedding.shape == (3,)

    @pytest.mark.parametrize(
        "model_id,expected_dim",
        [
            ("all-MiniLM-L6-v2", 384),
            ("all-mpnet-base-v2", 768),
            ("all-MiniLM-L12-v2", 384),
            ("multi-qa-mpnet-base-dot-v1", 768),
            ("all-distilroberta-v1", 768),
            ("paraphrase-multilingual-mpnet-base-v2", 768),
        ],
    )
    def test_known_model_dimensions(self, model_id, expected_dim):
        """Test that known models have correct dimensions."""
        provider = SentenceTransformersProvider(model_id=model_id)
        assert provider._model_info["dimension"] == expected_dim

    def test_device_selection(self):
        """Test device selection options."""
        # Auto device (None)
        provider1 = SentenceTransformersProvider(device=None)
        assert provider1.device is None

        # CPU
        provider2 = SentenceTransformersProvider(device="cpu")
        assert provider2.device == "cpu"

        # CUDA
        provider3 = SentenceTransformersProvider(device="cuda")
        assert provider3.device == "cuda"

        # Specific CUDA device
        provider4 = SentenceTransformersProvider(device="cuda:1")
        assert provider4.device == "cuda:1"


class TestSentenceTransformersIntegration:
    """Integration tests with mocked dependencies."""

    @pytest.mark.asyncio
    @patch("sentence_transformers.SentenceTransformer")
    async def test_batch_processing_consistency(self, mock_st_class):
        """Test that batch processing gives same results as individual processing."""
        mock_model = Mock()

        # Mock different embeddings for different texts
        def encode_side_effect(texts, **kwargs):
            if isinstance(texts, str):
                texts = [texts]

            embeddings = []
            for text in texts:
                if text == "Text A":
                    embeddings.append([0.1, 0.2, 0.3])
                elif text == "Text B":
                    embeddings.append([0.4, 0.5, 0.6])
                else:
                    embeddings.append([0.7, 0.8, 0.9])

            return np.array(embeddings[0] if len(embeddings) == 1 else embeddings)

        mock_model.encode.side_effect = encode_side_effect
        mock_st_class.return_value = mock_model

        provider = SentenceTransformersProvider()

        # Embed individually
        result_a = await provider.embed_text("Text A")
        result_b = await provider.embed_text("Text B")

        # Embed as batch
        batch_results = await provider.embed_batch(["Text A", "Text B"])

        # Compare results
        assert np.array_equal(result_a.embedding, batch_results[0].embedding)
        assert np.array_equal(result_b.embedding, batch_results[1].embedding)

    @pytest.mark.asyncio
    @patch("sentence_transformers.SentenceTransformer")
    async def test_normalization_effect(self, mock_st_class):
        """Test that normalization setting is respected."""
        mock_model = Mock()
        mock_st_class.return_value = mock_model

        # Test with normalization
        provider1 = SentenceTransformersProvider(normalize_embeddings=True)
        mock_model.encode.return_value = np.array([3.0, 4.0])  # Length = 5
        await provider1.embed_text("Test")

        # Test without normalization
        provider2 = SentenceTransformersProvider(normalize_embeddings=False)
        mock_model.encode.return_value = np.array([3.0, 4.0])  # Same embedding
        await provider2.embed_text("Test")

        # Check that normalization flag was passed correctly
        calls = mock_model.encode.call_args_list
        assert calls[0][1]["normalize_embeddings"] is True
        assert calls[1][1]["normalize_embeddings"] is False
