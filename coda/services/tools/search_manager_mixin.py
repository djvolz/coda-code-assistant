"""Shared functionality for tools that use semantic search."""

from coda.base.search.vector_search.constants import DEFAULT_EMBEDDING_DIMENSION
from coda.base.search.vector_search.embeddings.mock import MockEmbeddingProvider
from coda.base.search.vector_search.manager import SemanticSearchManager
from coda.semantic_search_coda import create_semantic_search_manager


class SearchManagerMixin:
    """Mixin providing shared search manager initialization."""

    def __init__(self):
        self._search_manager = None

    def _initialize_manager(self):
        """Initialize the search manager once."""
        if self._search_manager is None:
            try:
                # Try to use configured provider first
                self._search_manager = create_semantic_search_manager()
            except Exception:
                # Fall back to mock provider for demo
                provider = MockEmbeddingProvider(dimension=DEFAULT_EMBEDDING_DIMENSION)
                self._search_manager = SemanticSearchManager(embedding_provider=provider)
