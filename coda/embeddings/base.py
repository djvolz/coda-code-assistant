"""
Base classes for embedding providers.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""

    text: str
    embedding: np.ndarray
    model: str
    metadata: dict[str, Any] | None = None

    @property
    def dimension(self) -> int:
        """Get the dimension of the embedding vector."""
        return len(self.embedding)


class BaseEmbeddingProvider(ABC):
    """Abstract base class for embedding providers."""

    def __init__(self, model_id: str):
        """Initialize the embedding provider.

        Args:
            model_id: The model identifier to use for embeddings
        """
        self.model_id = model_id

    @abstractmethod
    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult containing the text and its embedding
        """
        pass

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts.

        Default implementation processes texts sequentially.
        Providers can override for optimized batch processing.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResults
        """
        results = []
        for text in texts:
            result = await self.embed_text(text)
            results.append(result)
        return results

    @abstractmethod
    async def list_models(self) -> list[dict[str, Any]]:
        """List available embedding models.

        Returns:
            List of model information dictionaries
        """
        pass

    @abstractmethod
    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model.

        Returns:
            Dictionary with model information (dimension, max_tokens, etc.)
        """
        pass

    def similarity(self, embedding1: np.ndarray, embedding2: np.ndarray) -> float:
        """Calculate cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        # Normalize vectors
        norm1 = np.linalg.norm(embedding1)
        norm2 = np.linalg.norm(embedding2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        # Calculate cosine similarity
        return np.dot(embedding1, embedding2) / (norm1 * norm2)
