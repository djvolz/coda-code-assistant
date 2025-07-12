"""
Factory for creating embedding providers.

This module provides a unified interface for creating different
embedding providers based on configuration.
"""

import logging
from typing import Any

from .base import BaseEmbeddingProvider
from .mock import MockEmbeddingProvider

# Optional providers (conditionally imported)
try:
    from .oci import OCIEmbeddingProvider
except ImportError:
    OCIEmbeddingProvider = None

try:
    from .ollama import OllamaEmbeddingProvider
except ImportError:
    OllamaEmbeddingProvider = None

try:
    from .sentence_transformers import SentenceTransformersProvider
except ImportError:
    SentenceTransformersProvider = None

logger = logging.getLogger(__name__)


class EmbeddingProviderFactory:
    """Factory for creating embedding providers."""

    # Registry of available providers
    PROVIDERS = {}

    # Add providers that are available
    if OCIEmbeddingProvider is not None:
        PROVIDERS["oci"] = OCIEmbeddingProvider
    PROVIDERS["mock"] = MockEmbeddingProvider  # Always available
    if SentenceTransformersProvider is not None:
        PROVIDERS["sentence-transformers"] = SentenceTransformersProvider
    if OllamaEmbeddingProvider is not None:
        PROVIDERS["ollama"] = OllamaEmbeddingProvider

    # Aliases for convenience
    ALIASES = {
        "st": "sentence-transformers",
        "sbert": "sentence-transformers",
        "local": "sentence-transformers",  # Default local provider
    }

    @classmethod
    def create_provider(
        cls, provider_type: str, model_id: str | None = None, **kwargs
    ) -> BaseEmbeddingProvider:
        """Create an embedding provider.

        Args:
            provider_type: Type of provider (oci, mock, sentence-transformers, ollama)
            model_id: Model ID to use (provider-specific)
            **kwargs: Additional provider-specific arguments

        Returns:
            Initialized embedding provider

        Raises:
            ValueError: If provider type is unknown
        """
        # Resolve aliases
        provider_type = provider_type.lower()
        provider_type = cls.ALIASES.get(provider_type, provider_type)

        # Get provider class
        provider_class = cls.PROVIDERS.get(provider_type)
        if not provider_class:
            available = list(cls.PROVIDERS.keys()) + list(cls.ALIASES.keys())
            raise ValueError(
                f"Unknown provider type: {provider_type}. Available: {', '.join(available)}"
            )

        # Set default model IDs if not provided
        if model_id is None:
            if provider_type == "oci":
                model_id = "cohere.embed-multilingual-v3.0"
            elif provider_type == "sentence-transformers":
                model_id = "all-MiniLM-L6-v2"
            elif provider_type == "ollama":
                model_id = "mxbai-embed-large"
            elif provider_type == "mock":
                model_id = "mock-768d"

        # Create provider instance
        try:
            if provider_type == "oci":
                # OCI requires special initialization
                if OCIEmbeddingProvider is None:
                    raise ImportError("OCI provider not available. Install oci package.")
                from .oci import create_standalone_oci_provider

                return create_standalone_oci_provider(
                    model_id=model_id,
                    compartment_id=kwargs.get("compartment_id"),
                    config_file=kwargs.get("config_file"),
                    profile=kwargs.get("profile"),
                )
            else:
                # Standard initialization
                return provider_class(model_id=model_id, **kwargs)

        except Exception as e:
            logger.error(f"Failed to create {provider_type} provider: {e}")
            raise

    @classmethod
    def list_providers(cls) -> dict[str, str]:
        """List available providers with descriptions.

        Returns:
            Dictionary of provider names to descriptions
        """
        return {
            "oci": "Oracle Cloud Infrastructure GenAI embeddings",
            "mock": "Mock provider for testing (no external dependencies)",
            "sentence-transformers": "Local embeddings using sentence-transformers",
            "ollama": "Local embeddings using Ollama",
        }

    @classmethod
    def get_provider_info(cls, provider_type: str) -> dict[str, Any]:
        """Get information about a specific provider.

        Args:
            provider_type: Type of provider

        Returns:
            Dictionary with provider information
        """
        # Resolve aliases
        provider_type = provider_type.lower()
        provider_type = cls.ALIASES.get(provider_type, provider_type)

        info = {
            "oci": {
                "description": "Oracle Cloud Infrastructure GenAI embeddings",
                "requires_auth": True,
                "requires_internet": True,
                "default_model": "cohere.embed-multilingual-v3.0",
                "example_models": [
                    "cohere.embed-multilingual-v3.0",
                    "cohere.embed-english-v3.0",
                    "multilingual-e5-base",
                ],
            },
            "mock": {
                "description": "Mock provider for testing",
                "requires_auth": False,
                "requires_internet": False,
                "default_model": "mock-768d",
                "example_models": ["mock-384d", "mock-768d", "mock-1024d"],
            },
            "sentence-transformers": {
                "description": "Local embeddings using sentence-transformers library",
                "requires_auth": False,
                "requires_internet": False,  # After initial download
                "default_model": "all-MiniLM-L6-v2",
                "example_models": [
                    "all-MiniLM-L6-v2",
                    "all-mpnet-base-v2",
                    "paraphrase-multilingual-mpnet-base-v2",
                ],
            },
            "ollama": {
                "description": "Local embeddings using Ollama server",
                "requires_auth": False,
                "requires_internet": False,  # After model pull
                "default_model": "mxbai-embed-large",
                "example_models": [
                    "mxbai-embed-large",
                    "nomic-embed-text",
                    "all-minilm",
                    "bge-base",
                ],
            },
        }

        return info.get(
            provider_type,
            {
                "description": "Unknown provider",
                "requires_auth": "unknown",
                "requires_internet": "unknown",
                "default_model": "unknown",
                "example_models": [],
            },
        )


def create_embedding_provider(
    provider_type: str = "mock", model_id: str | None = None, **kwargs
) -> BaseEmbeddingProvider:
    """Convenience function to create an embedding provider.

    Args:
        provider_type: Type of provider (oci, mock, sentence-transformers, ollama)
        model_id: Model ID to use (provider-specific)
        **kwargs: Additional provider-specific arguments

    Returns:
        Initialized embedding provider
    """
    return EmbeddingProviderFactory.create_provider(
        provider_type=provider_type, model_id=model_id, **kwargs
    )
