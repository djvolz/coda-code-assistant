"""
Embedding providers for semantic search functionality.

This module provides a unified interface for various embedding providers,
including OCI GenAI, Ollama, and HuggingFace models.
"""

from .base import BaseEmbeddingProvider, EmbeddingResult
from .oci import OCIEmbeddingProvider

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingResult",
    "OCIEmbeddingProvider",
]