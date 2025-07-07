"""
Mock embedding provider for testing and development.

This provider generates deterministic embeddings based on text content,
useful for testing without external dependencies.
"""

import hashlib
import numpy as np
from typing import List

from .base import BaseEmbeddingProvider, EmbeddingResult


class MockEmbeddingProvider(BaseEmbeddingProvider):
    """Mock embedding provider that generates deterministic embeddings."""
    
    def __init__(self, dimension: int = 768):
        """Initialize mock provider.
        
        Args:
            dimension: Embedding dimension (default: 768)
        """
        self.dimension = dimension
        self.model_id = f"mock-{dimension}d"
        
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
        
        return EmbeddingResult(
            text=text,
            embedding=embedding,
            model=self.model_id,
            metadata={
                "provider": "mock",
                "dimension": self.dimension
            }
        )
        
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Generate mock embeddings for multiple texts.
        
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
        
    def get_model_info(self) -> dict:
        """Get information about the mock model.
        
        Returns:
            Dictionary with model information
        """
        return {
            "model_id": self.model_id,
            "dimension": self.dimension,
            "provider": "mock",
            "description": "Mock embedding provider for testing"
        }
        
    async def list_models(self) -> List[dict]:
        """List available mock models.
        
        Returns:
            List of model information dictionaries
        """
        return [
            {
                "model_id": "mock-768d",
                "dimension": 768,
                "description": "Mock 768-dimensional embeddings"
            },
            {
                "model_id": "mock-1024d", 
                "dimension": 1024,
                "description": "Mock 1024-dimensional embeddings"
            }
        ]