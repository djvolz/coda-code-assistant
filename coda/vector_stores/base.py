"""
Base classes for vector storage backends.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class SearchResult:
    """Result from a vector similarity search."""

    id: str
    text: str
    score: float
    metadata: dict[str, Any] | None = None


class BaseVectorStore(ABC):
    """Abstract base class for vector storage backends."""

    def __init__(self, dimension: int, index_type: str = "flat"):
        """Initialize vector store.

        Args:
            dimension: Dimension of vectors to store
            index_type: Type of index to use (flat, ivf, hnsw, etc.)
        """
        self.dimension = dimension
        self.index_type = index_type

    @abstractmethod
    async def add_vectors(
        self,
        texts: list[str],
        embeddings: list[np.ndarray],
        ids: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
    ) -> list[str]:
        """Add vectors to the store.

        Args:
            texts: Original texts
            embeddings: Vector embeddings
            ids: Optional IDs for the vectors
            metadata: Optional metadata for each vector

        Returns:
            List of IDs for the added vectors
        """
        pass

    @abstractmethod
    async def search(
        self, query_embedding: np.ndarray, k: int = 10, filter: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """Search for similar vectors.

        Args:
            query_embedding: Query vector
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of search results ordered by similarity
        """
        pass

    @abstractmethod
    async def delete_vectors(self, ids: list[str]) -> int:
        """Delete vectors by ID.

        Args:
            ids: List of vector IDs to delete

        Returns:
            Number of vectors deleted
        """
        pass

    @abstractmethod
    async def update_vectors(
        self,
        ids: list[str],
        embeddings: list[np.ndarray] | None = None,
        texts: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
    ) -> int:
        """Update existing vectors.

        Args:
            ids: IDs of vectors to update
            embeddings: New embeddings (if provided)
            texts: New texts (if provided)
            metadata: New metadata (if provided)

        Returns:
            Number of vectors updated
        """
        pass

    @abstractmethod
    async def get_vector_count(self) -> int:
        """Get total number of vectors in store.

        Returns:
            Number of vectors
        """
        pass

    @abstractmethod
    async def clear(self) -> int:
        """Clear all vectors from store.

        Returns:
            Number of vectors removed
        """
        pass

    @abstractmethod
    async def save_index(self, path: str) -> None:
        """Save index to disk.

        Args:
            path: Path to save the index
        """
        pass

    @abstractmethod
    async def load_index(self, path: str) -> None:
        """Load index from disk.

        Args:
            path: Path to load the index from
        """
        pass

    async def hybrid_search(
        self,
        query_embedding: np.ndarray,
        query_text: str,
        k: int = 10,
        vector_weight: float = 0.7,
        keyword_weight: float = 0.3,
        filter: dict[str, Any] | None = None,
    ) -> list[SearchResult]:
        """Perform hybrid search combining vector and keyword search.

        Args:
            query_embedding: Query vector
            query_text: Query text for keyword search
            k: Number of results to return
            vector_weight: Weight for vector similarity (0-1)
            keyword_weight: Weight for keyword match (0-1)
            filter: Optional metadata filter

        Returns:
            List of search results
        """
        # Default implementation: just use vector search
        # Subclasses can override for true hybrid search
        return await self.search(query_embedding, k, filter)
