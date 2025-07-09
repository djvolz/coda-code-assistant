"""
Mock embedding provider for testing and development.

This provider generates deterministic embeddings based on text content,
useful for testing without external dependencies.
"""

import asyncio
import hashlib
from typing import Any

import numpy as np

from .base import BaseEmbeddingProvider, EmbeddingResult


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Mock embedding provider that generates deterministic embeddings."""

    def __init__(self, dimension: int = 768, model_id: str = None, delay: float = 0.0):
        """Initialize mock provider.

        Args:
            dimension: Embedding dimension (default: 768)
            model_id: Optional model ID (default: mock-{dimension}d)
            delay: Optional delay in seconds to simulate API latency
        """
        self.dimension = dimension
        self.delay = delay
        super().__init__(model_id or f"mock-{dimension}d")

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Generate a mock embedding for text.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult with mock embedding
        """
        # Generate deterministic embedding based on text hash
        text_hash = hashlib.sha256(text.encode()).hexdigest()

        # Use hash to seed random number generator for consistency
        seed = int(text_hash[:8], 16)
        np.random.seed(seed)

        # Generate normalized random vector
        embedding = np.random.randn(self.dimension)
        embedding = embedding / np.linalg.norm(embedding)

        # Simulate API delay if configured
        if self.delay > 0:
            await asyncio.sleep(self.delay)

        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model_id,
            metadata={"provider": "mock", "dimension": self.dimension},
        )

    # embed_batch is inherited from base class

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the mock model.

        Returns:
            Dictionary with model information
        """
        return {
            "id": self.model_id,
            "dimension": self.dimension,  # Fixed: was "dimensions"
            "dimensions": self.dimension,  # Keep for backward compatibility
            "provider": "mock",
            "description": "Mock embedding provider for testing",
            "max_tokens": 8192,  # Arbitrary large value for testing
            "languages": ["any"],
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """List available mock models.

        Returns:
            List of model information dictionaries
        """
        return [
            {
                "id": "mock-384d",
                "dimensions": 384,
                "description": "Mock 384-dimensional embeddings (lightweight)",
                "max_tokens": 8192,
                "languages": ["any"],
            },
            {
                "id": "mock-768d",
                "dimensions": 768,
                "description": "Mock 768-dimensional embeddings (standard)",
                "max_tokens": 8192,
                "languages": ["any"],
            },
            {
                "id": "mock-1024d",
                "dimensions": 1024,
                "description": "Mock 1024-dimensional embeddings (high-quality)",
                "max_tokens": 8192,
                "languages": ["any"],
            },
        ]
