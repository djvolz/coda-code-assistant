"""Standalone vector search and embeddings module for Coda.

This module provides comprehensive vector-based search capabilities including:
- Text chunking and preprocessing for embeddings
- Multiple embedding provider backends
- Vector storage and similarity search
- Semantic/vector search coordination

The module is designed to be fully independent and can be copy-pasted
to other projects without any Coda-specific dependencies.

Example usage:
    from coda.search.vector_search import SemanticSearchManager
    from coda.search.vector_search.embeddings.mock import MockEmbeddingProvider

    # Create provider and search manager
    provider = MockEmbeddingProvider(dimension=768)
    search = SemanticSearchManager(embedding_provider=provider)

    # Index and search content
    await search.index_content(["Document content here"])
    results = await search.search("query", k=5)
"""

# Core search functionality
from .chunking import Chunk, CodeChunker, TextChunker

# Embedding providers
from .embeddings.base import BaseEmbeddingProvider
from .embeddings.mock import MockEmbeddingProvider
from .manager import SemanticSearchManager

# Vector stores
from .vector_stores.base import BaseVectorStore, SearchResult
from .vector_stores.faiss_store import FAISSVectorStore

# Optional providers (conditionally imported)
try:
    from .embeddings.oci import OCIEmbeddingProvider
except ImportError:
    OCIEmbeddingProvider = None

try:
    from .embeddings.ollama import OllamaEmbeddingProvider
except ImportError:
    OllamaEmbeddingProvider = None

try:
    from .embeddings.sentence_transformers import SentenceTransformersProvider
except ImportError:
    SentenceTransformersProvider = None

__all__ = [
    # Core components
    "SemanticSearchManager",
    "Chunk",
    "TextChunker",
    "CodeChunker",
    # Base classes
    "BaseEmbeddingProvider",
    "BaseVectorStore",
    "SearchResult",
    # Always available providers
    "MockEmbeddingProvider",
    "FAISSVectorStore",
    # Optional providers (may be None if dependencies not available)
    "OCIEmbeddingProvider",
    "OllamaEmbeddingProvider",
    "SentenceTransformersProvider",
]
