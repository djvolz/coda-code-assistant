"""
Embedding providers for semantic search functionality.

This module provides a unified interface for various embedding providers,
including OCI GenAI, Ollama, and HuggingFace models.
"""

from .base import BaseEmbeddingProvider, EmbeddingResult
from .oci import (
    OCIEmbeddingProvider,
    create_oci_provider_from_coda_config,
    create_standalone_oci_provider,
)
from .mock import MockEmbeddingProvider

__all__ = [
    "BaseEmbeddingProvider",
    "EmbeddingResult",
    "OCIEmbeddingProvider",
    "MockEmbeddingProvider",
    "create_oci_provider_from_coda_config",
    "create_standalone_oci_provider",
]