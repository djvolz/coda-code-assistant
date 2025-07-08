"""
Embedding providers for semantic search functionality.

This module provides a unified interface for various embedding providers,
including OCI GenAI, Ollama, and HuggingFace models.
"""

from .base import BaseEmbeddingProvider, EmbeddingResult
from .factory import EmbeddingProviderFactory, create_embedding_provider
from .mock import MockEmbeddingProvider
from .oci import (
    OCIEmbeddingProvider,
    create_oci_provider_from_coda_config,
    create_standalone_oci_provider,
)
from .ollama import OllamaEmbeddingProvider
from .sentence_transformers import SentenceTransformersProvider

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingResult",
    "OCIEmbeddingProvider",
    "MockEmbeddingProvider",
    "SentenceTransformersProvider",
    "OllamaEmbeddingProvider",
    "EmbeddingProviderFactory",
    "create_embedding_provider",
    "create_oci_provider_from_coda_config",
    "create_standalone_oci_provider",
]
