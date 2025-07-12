"""🔧 BASE MODULE
Comprehensive Search Module

This module provides both repository search and semantic search capabilities:

## Repository Mapping (map/)
- Repository structure analysis
- Tree-sitter code parsing
- Dependency graph generation
- Multi-language support

## Vector Search (vector_search/)
- Text chunking and preprocessing for embeddings
- Multiple embedding providers
- Vector storage and similarity search
- Semantic/vector search coordination

The module is designed to be fully independent and can be copy-pasted
to other projects without any Coda-specific dependencies.

Example usage:
    # Repository analysis
    from coda.search.map import RepoMap
    repo = RepoMap("/path/to/project")
    analysis = repo.analyze()

    # Vector search
    from coda.search.vector_search import SemanticSearchManager
    from coda.search.vector_search.embeddings.mock import MockEmbeddingProvider

    provider = MockEmbeddingProvider(dimension=768)
    search = SemanticSearchManager(embedding_provider=provider)
"""

# Repository mapping components
from .map import DependencyGraph, RepoMap, TreeSitterAnalyzer

# Vector search components
from .vector_search import SemanticSearchManager
from .vector_search.chunking import Chunk, CodeChunker, TextChunker
from .vector_search.embeddings.base import BaseEmbeddingProvider
from .vector_search.embeddings.mock import MockEmbeddingProvider
from .vector_search.vector_stores.base import BaseVectorStore, SearchResult
from .vector_search.vector_stores.faiss_store import FAISSVectorStore

# Optional vector search providers (conditionally imported)
try:
    from .vector_search.embeddings.oci import OCIEmbeddingProvider
except ImportError:
    OCIEmbeddingProvider = None

try:
    from .vector_search.embeddings.ollama import OllamaEmbeddingProvider
except ImportError:
    OllamaEmbeddingProvider = None

try:
    from .vector_search.embeddings.sentence_transformers import SentenceTransformersProvider
except ImportError:
    SentenceTransformersProvider = None

__all__ = [
    # Repository mapping
    "RepoMap",
    "TreeSitterAnalyzer",
    "DependencyGraph",
    # Vector search core
    "SemanticSearchManager",
    "Chunk",
    "TextChunker",
    "CodeChunker",
    # Vector search base classes
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
