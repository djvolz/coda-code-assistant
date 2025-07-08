"""
Vector storage backends for semantic search.

This module provides various vector storage implementations including
Oracle Vector Database, FAISS, and other vector stores.
"""

from .base import BaseVectorStore, SearchResult
from .faiss_store import FAISSVectorStore

__all__ = [
    "BaseVectorStore",
    "SearchResult",
    "FAISSVectorStore",
]
