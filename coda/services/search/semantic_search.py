"""
Coda integration layer for search module.

This module provides wrappers and utilities that integrate the self-contained
vector search components with Coda's configuration system. This acts as the
bridge between the standalone search module and Coda-specific features.
"""

import logging
from typing import Any

from coda.base.search.vector_search.constants import (
    DEFAULT_MODELS,
    OLLAMA_HEALTH_TIMEOUT,
)
from coda.base.search.vector_search.embeddings import create_oci_provider_from_coda_config
from coda.base.search.vector_search.embeddings.factory import create_embedding_provider
from coda.base.search.vector_search.manager import SemanticSearchManager
from coda.services.config import get_config_service


# Minimal compatibility type for transition
class CodaConfig:
    """Compatibility type for semantic search integration."""

    def __init__(self, config_dict: dict[str, Any]):
        self._dict = config_dict
        for key, value in config_dict.items():
            setattr(self, key, value)

    def to_dict(self) -> dict[str, Any]:
        return self._dict

    def get(self, key: str, default: Any = None) -> Any:
        return self._dict.get(key, default)


def get_config() -> CodaConfig:
    """Get config in compatibility format."""
    config_service = get_config_service()
    return CodaConfig(config_service.to_dict())


logger = logging.getLogger(__name__)


def _try_oci_provider(
    config_dict: dict[str, Any], model_id: str | None
) -> tuple[Any | None, str | None]:
    """Try to create OCI embedding provider.

    Returns:
        Tuple of (provider, error_message). Provider is None if failed.
    """
    if not config_dict.get("oci_genai", {}).get("compartment_id"):
        return None, "OCI not configured"

    try:
        provider = create_oci_provider_from_coda_config(
            config_dict, model_id or DEFAULT_MODELS["oci"]
        )
        logger.info("Using OCI embedding provider")
        return provider, None
    except Exception as e:
        return None, f"OCI: {str(e)}"


def _try_sentence_transformers_provider(model_id: str | None) -> tuple[Any | None, str | None]:
    """Try to create sentence-transformers provider.

    Returns:
        Tuple of (provider, error_message). Provider is None if failed.
    """
    try:
        provider = create_embedding_provider(
            provider_type="sentence-transformers",
            model_id=model_id or DEFAULT_MODELS["sentence_transformers"],
        )
        logger.info("Using sentence-transformers embedding provider")
        return provider, None
    except Exception as e:
        return None, f"Sentence-transformers: {str(e)}"


def _try_ollama_provider(model_id: str | None) -> tuple[Any | None, str | None]:
    """Try to create Ollama provider if service is available.

    Returns:
        Tuple of (provider, error_message). Provider is None if failed.
    """
    try:
        # Quick check if Ollama is available
        import httpx

        try:
            with httpx.Client(timeout=OLLAMA_HEALTH_TIMEOUT) as client:
                response = client.get("http://localhost:11434/api/version")
                response.raise_for_status()

            # Ollama is running, try to create provider
            provider = create_embedding_provider(
                provider_type="ollama", model_id=model_id or DEFAULT_MODELS["ollama"]
            )
            logger.info("Using Ollama embedding provider")
            return provider, None
        except (httpx.ConnectError, httpx.TimeoutException):
            # Ollama not running, skip silently
            return None, "Ollama service not available"
    except Exception as e:
        return None, f"Ollama: {str(e)}"


def _try_mock_provider(model_id: str | None) -> tuple[Any | None, str | None]:
    """Try to create mock provider (should always succeed).

    Returns:
        Tuple of (provider, error_message). Provider is None if failed.
    """
    try:
        provider = create_embedding_provider(
            provider_type="mock", model_id=model_id or DEFAULT_MODELS["mock"]
        )
        logger.warning("Using mock embedding provider (for testing only)")
        return provider, None
    except Exception as e:
        return None, f"Mock: {str(e)}"


def create_semantic_search_manager(
    config: CodaConfig | None = None,
    provider_type: str | None = None,
    model_id: str | None = None,
    **provider_kwargs,
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
    if hasattr(config, "config_dict"):
        config_dict = config.config_dict
    elif hasattr(config, "__dict__"):
        config_dict = config.__dict__
    else:
        config_dict = config

    # Try to create embedding provider
    embedding_provider = None
    error_messages = []

    # If provider type is specified, use it directly
    if provider_type:
        if provider_type == "oci":
            embedding_provider, error = _try_oci_provider(config_dict, model_id)
        elif provider_type == "sentence-transformers":
            embedding_provider, error = _try_sentence_transformers_provider(model_id)
        elif provider_type == "ollama":
            embedding_provider, error = _try_ollama_provider(model_id)
        elif provider_type == "mock":
            embedding_provider, error = _try_mock_provider(model_id)
        else:
            # Use factory for other providers
            try:
                embedding_provider = create_embedding_provider(
                    provider_type=provider_type, model_id=model_id, **provider_kwargs
                )
            except Exception as e:
                error = f"{provider_type}: {str(e)}"

        if error:
            error_messages.append(error)
    else:
        # Try providers in order of preference based on config

        # 1. Try OCI if configured
        embedding_provider, error = _try_oci_provider(config_dict, model_id)
        if error:
            error_messages.append(error)

        # 2. Try sentence-transformers (no external dependencies after install)
        if embedding_provider is None:
            embedding_provider, error = _try_sentence_transformers_provider(model_id)
            if error:
                error_messages.append(error)

        # 3. Try Ollama if running
        if embedding_provider is None:
            embedding_provider, error = _try_ollama_provider(model_id)
            if error:
                error_messages.append(error)

        # 4. Use mock as last resort
        if embedding_provider is None:
            embedding_provider, error = _try_mock_provider(model_id)
            if error:
                error_messages.append(error)

    if embedding_provider is None:
        raise ValueError(f"No embedding provider available. Errors: {'; '.join(error_messages)}")

    # Use Coda's cache directory for indexes
    config_service = get_config_service()
    index_dir = config_service.get_cache_dir() / "semantic_search"

    return SemanticSearchManager(embedding_provider=embedding_provider, index_dir=index_dir)
