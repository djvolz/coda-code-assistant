"""
Semantic search functionality.

This module provides a self-contained interface for semantic search capabilities,
including content indexing, similarity search, and hybrid search. It can be used
independently by external projects without Coda dependencies.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from .embeddings.base import BaseEmbeddingProvider
from .vector_stores.base import BaseVectorStore, SearchResult
from .vector_stores.faiss_store import FAISSVectorStore

logger = logging.getLogger(__name__)


class SemanticSearchManager:
    """Manages semantic search functionality.

    Coordinates between embedding providers and vector stores to provide
    unified semantic search capabilities. This is designed to be self-contained
    and usable by external projects.
    """

    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store: BaseVectorStore | None = None,
        index_dir: str | Path | None = None,
    ):
        """Initialize semantic search manager.

        Args:
            embedding_provider: Provider for generating embeddings (required)
            vector_store: Store for vector similarity search (optional, defaults to FAISS)
            index_dir: Directory for storing indexes (optional)
        """
        self.embedding_provider = embedding_provider

        # Initialize vector store if not provided
        if vector_store is None:
            # Get dimension from embedding provider
            model_info = self.embedding_provider.get_model_info()
            dimension = model_info.get("dimensions", model_info.get("dimension", 768))

            # Default to FAISS with flat index for simplicity
            self.vector_store = FAISSVectorStore(
                dimension=dimension,
                index_type="flat",  # Use flat index for immediate use without training
                metric="cosine",
            )
        else:
            self.vector_store = vector_store

        # Set index directory
        if index_dir is None:
            # Default to user's cache directory
            self.index_dir = Path.home() / ".cache" / "embeddings" / "indexes"
        else:
            self.index_dir = Path(index_dir)

        self.index_dir.mkdir(parents=True, exist_ok=True)

    async def index_content(
        self,
        contents: list[str],
        ids: list[str] | None = None,
        metadata: list[dict[str, Any]] | None = None,
        batch_size: int = 32,
    ) -> list[str]:
        """Index content for semantic search.

        Args:
            contents: List of text content to index
            ids: Optional IDs for the content
            metadata: Optional metadata for each content
            batch_size: Batch size for embedding generation

        Returns:
            List of IDs for the indexed content
        """
        all_ids = []

        # Process in batches
        for i in range(0, len(contents), batch_size):
            batch_contents = contents[i : i + batch_size]
            batch_ids = ids[i : i + batch_size] if ids else None
            batch_metadata = metadata[i : i + batch_size] if metadata else None

            # Generate embeddings
            embedding_results = await self.embedding_provider.embed_batch(batch_contents)
            embeddings = [result.embedding for result in embedding_results]

            # Add to vector store
            batch_result_ids = await self.vector_store.add_vectors(
                texts=batch_contents, embeddings=embeddings, ids=batch_ids, metadata=batch_metadata
            )

            all_ids.extend(batch_result_ids)

        logger.info(f"Indexed {len(all_ids)} documents")
        return all_ids

    async def search(
        self, query: str, k: int = 10, filter: dict[str, Any] | None = None
    ) -> list[SearchResult]:
        """Search for similar content using semantic search.

        Args:
            query: Search query
            k: Number of results to return
            filter: Optional metadata filter

        Returns:
            List of search results
        """
        # Generate query embedding
        query_result = await self.embedding_provider.embed_text(query)

        # Search vector store
        results = await self.vector_store.search(
            query_embedding=query_result.embedding, k=k, filter=filter
        )

        return results

    async def index_code_files(
        self,
        file_paths: list[str | Path],
        batch_size: int = 32,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[str]:
        """Index code files for semantic search.

        Args:
            file_paths: List of file paths to index
            batch_size: Batch size for processing
            chunk_size: Target size for chunks in characters
            chunk_overlap: Overlap between chunks

        Returns:
            List of IDs for the indexed files
        """
        from .chunking import create_chunker

        contents = []
        metadata_list = []
        ids = []

        for file_path in file_paths:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"File not found: {path}")
                continue

            try:
                # Read file content
                content = path.read_text(encoding="utf-8")

                # Create appropriate chunker for the file type
                chunker = create_chunker(
                    file_path=path, chunk_size=chunk_size, chunk_overlap=chunk_overlap
                )

                # Get chunks
                chunks = chunker.chunk_text(content, metadata={"file_path": str(path)})

                # Process each chunk
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{path}#chunk_{i}"
                    contents.append(chunk.text)
                    ids.append(chunk_id)

                    # Create metadata for the chunk
                    chunk_metadata = {
                        "file_path": str(path),
                        "file_name": path.name,
                        "file_type": path.suffix,
                        "chunk_index": i,
                        "chunk_type": chunk.chunk_type,
                        "start_line": chunk.start_line,
                        "end_line": chunk.end_line,
                        "indexed_at": datetime.now().isoformat(),
                    }

                    # Add any additional metadata from the chunk
                    if chunk.metadata:
                        chunk_metadata.update(chunk.metadata)

                    metadata_list.append(chunk_metadata)

                logger.info(f"Created {len(chunks)} chunks from {path}")

            except Exception as e:
                logger.error(f"Error reading file {path}: {str(e)}")
                continue

        # Index all chunks
        return await self.index_content(
            contents=contents, ids=ids, metadata=metadata_list, batch_size=batch_size
        )

    async def index_session_messages(
        self, messages: list[dict[str, Any]], session_id: str, batch_size: int = 32
    ) -> list[str]:
        """Index session messages for semantic search.

        Args:
            messages: List of message dictionaries
            session_id: ID of the session
            batch_size: Batch size for processing

        Returns:
            List of IDs for the indexed messages
        """
        contents = []
        metadata_list = []
        ids = []

        for i, message in enumerate(messages):
            # Combine role and content for better context
            content = f"{message.get('role', 'user')}: {message.get('content', '')}"

            contents.append(content)
            ids.append(f"{session_id}_msg_{i}")
            metadata_list.append(
                {
                    "session_id": session_id,
                    "message_index": i,
                    "role": message.get("role"),
                    "timestamp": message.get("timestamp"),
                }
            )

        return await self.index_content(
            contents=contents, ids=ids, metadata=metadata_list, batch_size=batch_size
        )

    async def save_index(self, name: str = "default") -> None:
        """Save the current index to disk.

        Args:
            name: Name for the index
        """
        index_path = self.index_dir / name
        await self.vector_store.save_index(str(index_path))
        logger.info(f"Saved index to {index_path}")

    async def load_index(self, name: str = "default") -> None:
        """Load an index from disk.

        Args:
            name: Name of the index to load
        """
        index_path = self.index_dir / name
        if not index_path.with_suffix(".faiss").exists():
            raise FileNotFoundError(f"Index not found: {index_path}")

        await self.vector_store.load_index(str(index_path))
        logger.info(f"Loaded index from {index_path}")

    async def clear_index(self) -> int:
        """Clear all vectors from the current index.

        Returns:
            Number of vectors cleared
        """
        count = await self.vector_store.clear()
        logger.info(f"Cleared {count} vectors from index")
        return count

    async def get_stats(self) -> dict[str, Any]:
        """Get statistics about the semantic search index.

        Returns:
            Dictionary with index statistics
        """
        vector_count = await self.vector_store.get_vector_count()
        model_info = self.embedding_provider.get_model_info()

        return {
            "vector_count": vector_count,
            "embedding_model": model_info.get("id"),
            "embedding_dimension": model_info.get("dimensions", model_info.get("dimension")),
            "vector_store_type": self.vector_store.__class__.__name__,
            "index_type": getattr(self.vector_store, "index_type", "unknown"),
        }
