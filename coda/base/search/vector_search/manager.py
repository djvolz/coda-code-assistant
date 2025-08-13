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

        # Flag to track if we've tried loading the default index
        self._default_index_loaded = False

    async def _ensure_default_index_loaded(self) -> None:
        """Try to load the default index if it exists and hasn't been loaded yet."""
        if self._default_index_loaded:
            return

        self._default_index_loaded = True
        default_index_path = self.index_dir / "default"

        if (default_index_path.with_suffix(".faiss")).exists():
            try:
                await self.load_index("default")
                logger.info("Loaded existing default index")
            except Exception as e:
                logger.debug(f"Failed to load default index: {e}")

    async def _check_and_warn_stale_cache(self) -> None:
        """Check if cache is stale and log appropriate warnings."""
        try:
            cache_status = await self.check_cache_dirty()
            if cache_status["is_dirty"]:
                # Log warning about stale cache
                total_issues = len(cache_status["dirty_files"]) + len(cache_status["missing_files"])
                if total_issues > 0:
                    logger.warning(
                        f"Search index may be stale: {total_issues} files have changed. "
                        f"Consider running '/search index .' to update."
                    )
        except Exception as e:
            logger.debug(f"Failed to check cache status: {e}")

    async def check_cache_dirty(self, file_paths: list[str | Path] | None = None) -> dict[str, Any]:
        """Check if the cache needs to be updated based on file modifications.

        Args:
            file_paths: Optional list of specific files to check. If None, checks all indexed files.

        Returns:
            Dictionary with cache status information:
            - is_dirty: bool - whether cache needs updating
            - dirty_files: list - files that have been modified
            - missing_files: list - files that no longer exist
            - new_files: list - files not in cache (if file_paths provided)
        """
        if not hasattr(self.vector_store, "indexed_files"):
            return {
                "is_dirty": False,
                "dirty_files": [],
                "missing_files": [],
                "new_files": [],
                "reason": "No cache metadata available",
            }

        indexed_files = self.vector_store.indexed_files
        dirty_files = []
        missing_files = []
        new_files = []

        # Check specific files if provided, otherwise check all indexed files
        files_to_check = []
        if file_paths:
            files_to_check = [str(Path(p)) for p in file_paths]
            # Only find new files not in cache if we're doing an explicit check
            # For automatic cache validation, don't consider unindexed files as "new"
            for file_path in files_to_check:
                if file_path not in indexed_files:
                    new_files.append(file_path)
        else:
            # When no specific files provided, only check files that are already indexed
            files_to_check = list(indexed_files.keys())

        # Check each file for modifications
        for file_path in files_to_check:
            if file_path in indexed_files:
                path = Path(file_path)
                if not path.exists():
                    missing_files.append(file_path)
                    continue

                try:
                    current_stat = path.stat()
                    cached_mtime = indexed_files[file_path].get("mtime")
                    cached_size = indexed_files[file_path].get("size")

                    if (
                        cached_mtime is None
                        or abs(current_stat.st_mtime - cached_mtime)
                        > 5  # Allow 5 second tolerance for filesystem precision
                        or current_stat.st_size != cached_size
                    ):
                        dirty_files.append(file_path)

                except OSError:
                    missing_files.append(file_path)

        is_dirty = bool(dirty_files or missing_files or new_files)

        return {
            "is_dirty": is_dirty,
            "dirty_files": dirty_files,
            "missing_files": missing_files,
            "new_files": new_files,
            "total_indexed_files": len(indexed_files),
            "reason": f"Found {len(dirty_files)} modified, {len(missing_files)} missing, {len(new_files)} new files",
        }

    async def remove_files_from_index(self, file_paths: list[str]) -> int:
        """Remove indexed content for specific files.

        Args:
            file_paths: List of file paths to remove from index

        Returns:
            Number of chunks removed
        """
        removed_count = 0
        ids_to_remove = []

        # Find all chunk IDs for the specified files
        for chunk_id, metadata in self.vector_store.metadata.items():
            if isinstance(metadata, dict) and metadata.get("file_path") in file_paths:
                ids_to_remove.append(chunk_id)

        # Remove the chunks
        for chunk_id in ids_to_remove:
            try:
                await self.vector_store.remove_vector(chunk_id)
                removed_count += 1
            except Exception as e:
                logger.warning(f"Failed to remove chunk {chunk_id}: {e}")

        logger.info(f"Removed {removed_count} chunks for {len(file_paths)} files")
        return removed_count

    async def update_dirty_files(
        self, file_paths: list[str | Path] | None = None
    ) -> dict[str, Any]:
        """Update the index for files that have been modified.

        Args:
            file_paths: Optional list of specific files to update. If None, updates all dirty files.

        Returns:
            Dictionary with update results
        """
        # Check cache status
        cache_status = await self.check_cache_dirty(file_paths)

        if not cache_status["is_dirty"]:
            return {"updated": False, "reason": "Cache is up to date", "files_processed": 0}

        # Remove dirty and missing files from index
        files_to_remove = cache_status["dirty_files"] + cache_status["missing_files"]
        removed_count = 0
        if files_to_remove:
            removed_count = await self.remove_files_from_index(files_to_remove)

        # Re-index dirty files and new files (skip missing files)
        files_to_reindex = []
        for file_path in cache_status["dirty_files"] + cache_status["new_files"]:
            if Path(file_path).exists():
                files_to_reindex.append(file_path)

        indexed_count = 0
        if files_to_reindex:
            indexed_ids = await self.index_code_files(files_to_reindex)
            indexed_count = len(indexed_ids)

        return {
            "updated": True,
            "removed_chunks": removed_count,
            "indexed_files": len(files_to_reindex),
            "indexed_chunks": indexed_count,
            "dirty_files": cache_status["dirty_files"],
            "missing_files": cache_status["missing_files"],
            "new_files": cache_status["new_files"],
        }

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
        # Ensure default index is loaded before adding new content
        await self._ensure_default_index_loaded()

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

        # Auto-save the default index after adding content
        try:
            await self.save_index("default")
            logger.debug("Auto-saved default index")
        except Exception as e:
            logger.warning(f"Failed to auto-save default index: {e}")

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
        # Ensure default index is loaded before searching
        await self._ensure_default_index_loaded()

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

                # Always track the file, even if it produces 0 chunks
                file_stat = path.stat()

                # Ensure we have indexed_files dict
                if not hasattr(self.vector_store, "indexed_files"):
                    self.vector_store.indexed_files = {}

                # Track this file with current metadata
                self.vector_store.indexed_files[str(path)] = {
                    "mtime": file_stat.st_mtime,
                    "size": file_stat.st_size,
                    "indexed_at": datetime.now().isoformat(),
                }

                # Process each chunk (if any)
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
                        "file_mtime": file_stat.st_mtime,
                        "file_size": file_stat.st_size,
                    }

                    # Add any additional metadata from the chunk
                    if chunk.metadata:
                        chunk_metadata.update(chunk.metadata)

                    metadata_list.append(chunk_metadata)

                logger.info(f"Created {len(chunks)} chunks from {path}")

            except Exception as e:
                logger.error(f"Error reading file {path}: {str(e)}")
                continue

        # Index all chunks (if any were created)
        indexed_ids = []
        if contents:
            indexed_ids = await self.index_content(
                contents=contents, ids=ids, metadata=metadata_list, batch_size=batch_size
            )
        else:
            # If no chunks to index but we processed files, still save the index to persist file tracking
            try:
                await self.save_index("default")
                logger.debug("Saved index with file tracking metadata (no new chunks)")
            except Exception as e:
                logger.warning(f"Failed to save index after file tracking: {e}")

        return indexed_ids

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
