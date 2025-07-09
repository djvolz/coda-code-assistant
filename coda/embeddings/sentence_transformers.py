"""
Sentence Transformers embedding provider for local embeddings.

This provider uses the sentence-transformers library to generate embeddings
locally without requiring external API calls.
"""

import asyncio
from typing import Any

from .base import BaseEmbeddingProvider, EmbeddingResult


class SentenceTransformersProvider(BaseEmbeddingProvider):
    """Embedding provider using sentence-transformers models."""

    # Popular models with their dimensions
    MODELS = {
        "all-MiniLM-L6-v2": {
            "dimension": 384,
            "description": "Fast and lightweight model, good for semantic search",
            "max_tokens": 256,
        },
        "all-mpnet-base-v2": {
            "dimension": 768,
            "description": "High-quality model, best for semantic search quality",
            "max_tokens": 384,
        },
        "all-MiniLM-L12-v2": {
            "dimension": 384,
            "description": "Balanced model between speed and quality",
            "max_tokens": 256,
        },
        "multi-qa-mpnet-base-dot-v1": {
            "dimension": 768,
            "description": "Optimized for semantic search with dot-product",
            "max_tokens": 512,
        },
        "all-distilroberta-v1": {
            "dimension": 768,
            "description": "RoBERTa-based model with good quality",
            "max_tokens": 512,
        },
        "paraphrase-multilingual-mpnet-base-v2": {
            "dimension": 768,
            "description": "Multilingual model supporting 50+ languages",
            "max_tokens": 128,
        },
    }

    def __init__(
        self,
        model_id: str = "all-MiniLM-L6-v2",
        device: str | None = None,
        batch_size: int = 32,
        show_progress: bool = False,
        normalize_embeddings: bool = True,
    ):
        """Initialize sentence-transformers provider.

        Args:
            model_id: Model name from sentence-transformers
            device: Device to use ('cuda', 'cpu', or None for auto)
            batch_size: Batch size for encoding
            show_progress: Whether to show progress bar
            normalize_embeddings: Whether to normalize embeddings to unit length
        """
        super().__init__(model_id)
        self.device = device
        self.batch_size = batch_size
        self.show_progress = show_progress
        self.normalize_embeddings = normalize_embeddings
        self._model: Any = None  # Type: SentenceTransformer when loaded
        self._model_info = self.MODELS.get(
            model_id,
            {
                "dimension": None,  # Will be set after loading
                "description": f"Custom model: {model_id}",
                "max_tokens": 512,
            },
        )

    def _ensure_model_loaded(self):
        """Lazy load the model on first use."""
        if self._model is None:
            try:
                from sentence_transformers import SentenceTransformer
            except ImportError:
                raise ImportError(
                    "sentence-transformers is not installed. "
                    "Install it with: pip install sentence-transformers"
                ) from None

            # Load model
            self._model = SentenceTransformer(self.model_id, device=self.device)

            # Update dimension if not known
            if self._model_info["dimension"] is None:
                # Get dimension by encoding a test string
                test_embedding = self._model.encode(
                    "test", normalize_embeddings=self.normalize_embeddings, show_progress_bar=False
                )
                self._model_info["dimension"] = len(test_embedding)

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult containing the text and its embedding
        """
        self._ensure_model_loaded()

        # Run encoding in executor to avoid blocking
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                text,
                normalize_embeddings=self.normalize_embeddings,
                show_progress_bar=False,
                convert_to_numpy=True,
            ),
        )

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model_id,
            metadata={
                "provider": "sentence-transformers",
                "dimension": len(embedding),
                "normalized": self.normalize_embeddings,
            },
        )

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts with optimized batch processing.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResults
        """
        self._ensure_model_loaded()

        # Run batch encoding in executor
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(
            None,
            lambda: self._model.encode(
                texts,
                batch_size=self.batch_size,
                normalize_embeddings=self.normalize_embeddings,
                show_progress_bar=self.show_progress,
                convert_to_numpy=True,
            ),
        )

        # Create results
        results = []
        for text, embedding in zip(texts, embeddings, strict=False):
            results.append(
                EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model=self.model_id,
                    metadata={
                        "provider": "sentence-transformers",
                        "dimension": len(embedding),
                        "normalized": self.normalize_embeddings,
                    },
                )
            )

        return results

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model.

        Returns:
            Dictionary with model information
        """
        self._ensure_model_loaded()

        return {
            "id": self.model_id,
            "provider": "sentence-transformers",
            "dimension": self._model_info["dimension"],
            "description": self._model_info["description"],
            "max_tokens": self._model_info.get("max_tokens", 512),
            "device": str(self._model.device) if self._model else self.device,
            "normalize_embeddings": self.normalize_embeddings,
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """List available sentence-transformers models.

        Returns:
            List of model information dictionaries
        """
        models = []
        for model_id, info in self.MODELS.items():
            models.append(
                {
                    "id": model_id,
                    "provider": "sentence-transformers",
                    "dimension": info["dimension"],
                    "description": info["description"],
                    "max_tokens": info["max_tokens"],
                }
            )

        # Add note about custom models
        models.append(
            {
                "id": "custom",
                "provider": "sentence-transformers",
                "dimension": "varies",
                "description": "Any model from https://huggingface.co/sentence-transformers",
                "max_tokens": "varies",
            }
        )

        return models
