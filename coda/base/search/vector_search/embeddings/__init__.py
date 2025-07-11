"""
Embedding providers for semantic search functionality.

This module provides a unified interface for various embedding providers,
including OCI GenAI, Ollama, and HuggingFace models.
"""

from .base import BaseEmbeddingProvider, EmbeddingResult
from .factory import EmbeddingProviderFactory, create_embedding_provider
from .mock import MockEmbeddingProvider

# Optional providers (conditionally imported)
try:
    from .oci import (
        OCIEmbeddingProvider,
        create_oci_provider_from_coda_config,
        create_standalone_oci_provider,
    )
except ImportError:
    OCIEmbeddingProvider = None
    create_oci_provider_from_coda_config = None
    create_standalone_oci_provider = None

try:
    from .ollama import OllamaEmbeddingProvider
except ImportError:
    OllamaEmbeddingProvider = None

try:
    from .sentence_transformers import SentenceTransformersProvider
except ImportError:
    SentenceTransformersProvider = None

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingResult",
    "MockEmbeddingProvider",
    "EmbeddingProviderFactory",
    "create_embedding_provider",
]

# Add optional exports if available
if OCIEmbeddingProvider is not None:
    __all__.extend(
        [
            "OCIEmbeddingProvider",
            "create_oci_provider_from_coda_config",
            "create_standalone_oci_provider",
        ]
    )

if SentenceTransformersProvider is not None:
    __all__.append("SentenceTransformersProvider")

if OllamaEmbeddingProvider is not None:
    __all__.append("OllamaEmbeddingProvider")
