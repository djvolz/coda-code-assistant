"""
Coda-specific semantic search functionality.

This module provides wrappers and utilities that integrate the self-contained
semantic search components with Coda's configuration system.
"""

from typing import Optional
from pathlib import Path

from .semantic_search import SemanticSearchManager
from .embeddings.oci_coda import create_oci_embedding_provider
from .configuration import CodaConfig, get_config
from .constants import get_cache_dir


def create_semantic_search_manager(
    config: Optional[CodaConfig] = None,
    model_id: str = "multilingual-e5"
) -> SemanticSearchManager:
    """Create a semantic search manager from Coda configuration.
    
    Args:
        config: Coda configuration object
        model_id: Embedding model to use
        
    Returns:
        Configured SemanticSearchManager instance
        
    Raises:
        ValueError: If no embedding provider is configured
    """
    config = config or get_config()
    
    # Try to create embedding provider
    embedding_provider = None
    error_messages = []
    
    # Try OCI first
    try:
        embedding_provider = create_oci_embedding_provider(model_id, config)
    except ValueError as e:
        error_messages.append(f"OCI: {str(e)}")
    
    # TODO: Try other providers (sentence-transformers, Ollama, etc.)
    
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