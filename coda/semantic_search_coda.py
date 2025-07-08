"""
Coda-specific semantic search functionality.

This module provides wrappers and utilities that integrate the self-contained
semantic search components with Coda's configuration system.
"""

import logging

from .configuration import CodaConfig, get_config
from .constants import get_cache_dir
from .embeddings import create_oci_provider_from_coda_config
from .embeddings.factory import create_embedding_provider
from .semantic_search import SemanticSearchManager

logger = logging.getLogger(__name__)


def create_semantic_search_manager(
    config: CodaConfig | None = None,
    provider_type: str | None = None,
    model_id: str | None = None,
    **provider_kwargs
) -> SemanticSearchManager:
    """Create a semantic search manager from Coda configuration.

    Args:
        config: Coda configuration object
        provider_type: Type of embedding provider (oci, mock, sentence-transformers, ollama)
        model_id: Embedding model to use (provider-specific)
        **provider_kwargs: Additional provider-specific arguments

    Returns:
        Configured SemanticSearchManager instance

    Raises:
        ValueError: If no embedding provider can be created
    """
    config = config or get_config()
    # Handle both CodaConfig objects and plain dicts
    if hasattr(config, 'config_dict'):
        config_dict = config.config_dict
    elif hasattr(config, '__dict__'):
        config_dict = config.__dict__
    else:
        config_dict = config

    # Try to create embedding provider
    embedding_provider = None
    error_messages = []

    # If provider type is specified, use it directly
    if provider_type:
        try:
            if provider_type == "oci":
                # Use Coda-specific OCI config
                embedding_provider = create_oci_provider_from_coda_config(
                    config_dict,
                    model_id or "multilingual-e5"
                )
            else:
                # Use factory for other providers
                embedding_provider = create_embedding_provider(
                    provider_type=provider_type,
                    model_id=model_id,
                    **provider_kwargs
                )
        except Exception as e:
            error_messages.append(f"{provider_type}: {str(e)}")
    else:
        # Try providers in order of preference based on config

        # 1. Try OCI if configured
        if config_dict.get("oci_genai", {}).get("compartment_id"):
            try:
                embedding_provider = create_oci_provider_from_coda_config(
                    config_dict,
                    model_id or "multilingual-e5"
                )
                logger.info("Using OCI embedding provider")
            except Exception as e:
                error_messages.append(f"OCI: {str(e)}")

        # 2. Try sentence-transformers (no external dependencies after install)
        if embedding_provider is None:
            try:
                embedding_provider = create_embedding_provider(
                    provider_type="sentence-transformers",
                    model_id=model_id or "all-MiniLM-L6-v2"
                )
                logger.info("Using sentence-transformers embedding provider")
            except Exception as e:
                error_messages.append(f"Sentence-transformers: {str(e)}")

        # 3. Try Ollama if running
        if embedding_provider is None:
            try:
                # Quick check if Ollama is available
                import httpx
                try:
                    with httpx.Client(timeout=1.0) as client:
                        response = client.get("http://localhost:11434/api/version")
                        response.raise_for_status()
                    
                    # Ollama is running, try to create provider
                    embedding_provider = create_embedding_provider(
                        provider_type="ollama",
                        model_id=model_id or "mxbai-embed-large"
                    )
                    logger.info("Using Ollama embedding provider")
                except (httpx.ConnectError, httpx.TimeoutException):
                    # Ollama not running, skip silently
                    pass
            except Exception as e:
                error_messages.append(f"Ollama: {str(e)}")

        # 4. Use mock as last resort
        if embedding_provider is None:
            try:
                embedding_provider = create_embedding_provider(
                    provider_type="mock",
                    model_id=model_id or "mock-768d"
                )
                logger.warning("Using mock embedding provider (for testing only)")
            except Exception as e:
                error_messages.append(f"Mock: {str(e)}")

    if embedding_provider is None:
        raise ValueError(
            "No embedding provider available. "
            f"Errors: {'; '.join(error_messages)}"
        )

    # Use Coda's cache directory for indexes
    index_dir = get_cache_dir() / "semantic_search"

    return SemanticSearchManager(
        embedding_provider=embedding_provider,
        index_dir=index_dir
    )
