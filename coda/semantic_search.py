"""
Semantic search functionality for Coda.

This module provides the main interface for semantic search capabilities,
including content indexing, similarity search, and hybrid search.
"""

from typing import List, Dict, Any, Optional, Union, Tuple
from pathlib import Path
import asyncio
import logging
from datetime import datetime

from .embeddings import BaseEmbeddingProvider, OCIEmbeddingProvider
from .vector_stores import BaseVectorStore, FAISSVectorStore, SearchResult
from .configuration import CodaConfig
from .constants import get_cache_dir

logger = logging.getLogger(__name__)


class SemanticSearchManager:
    """Manages semantic search functionality for Coda.
    
    Coordinates between embedding providers and vector stores to provide
    unified semantic search capabilities.
    """
    
    def __init__(
        self,
        embedding_provider: Optional[BaseEmbeddingProvider] = None,
        vector_store: Optional[BaseVectorStore] = None,
        config: Optional[CodaConfig] = None
    ):
        """Initialize semantic search manager.
        
        Args:
            embedding_provider: Provider for generating embeddings
            vector_store: Store for vector similarity search
            config: Configuration object
        """
        self.config = config or CodaConfig()
        
        # Initialize embedding provider
        if embedding_provider is None:
            # Default to OCI embeddings if available
            oci_config = self.config.providers.get("oci_genai", {})
            if oci_config.get("compartment_id"):
                self.embedding_provider = OCIEmbeddingProvider(config=self.config)
            else:
                # TODO: Add fallback to sentence-transformers
                raise ValueError(
                    "No embedding provider available. "
                    "Configure OCI or install sentence-transformers."
                )
        else:
            self.embedding_provider = embedding_provider
            
        # Initialize vector store
        if vector_store is None:
            # Get dimension from embedding provider
            model_info = self.embedding_provider.get_model_info()
            dimension = model_info.get("dimension", 768)
            
            # Default to FAISS
            self.vector_store = FAISSVectorStore(dimension=dimension)
        else:
            self.vector_store = vector_store
            
        # Index paths
        self.index_dir = get_cache_dir() / "semantic_search"
        self.index_dir.mkdir(parents=True, exist_ok=True)
        
    async def index_content(
        self,
        contents: List[str],
        ids: Optional[List[str]] = None,
        metadata: Optional[List[Dict[str, Any]]] = None,
        batch_size: int = 32
    ) -> List[str]:
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
            batch_contents = contents[i:i + batch_size]
            batch_ids = ids[i:i + batch_size] if ids else None
            batch_metadata = metadata[i:i + batch_size] if metadata else None
            
            # Generate embeddings
            embedding_results = await self.embedding_provider.embed_batch(batch_contents)
            embeddings = [result.embedding for result in embedding_results]
            
            # Add to vector store
            batch_result_ids = await self.vector_store.add_vectors(
                texts=batch_contents,
                embeddings=embeddings,
                ids=batch_ids,
                metadata=batch_metadata
            )
            
            all_ids.extend(batch_result_ids)
            
        logger.info(f"Indexed {len(all_ids)} documents")
        return all_ids
        
    async def search(
        self,
        query: str,
        k: int = 10,
        filter: Optional[Dict[str, Any]] = None
    ) -> List[SearchResult]:
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
            query_embedding=query_result.embedding,
            k=k,
            filter=filter
        )
        
        return results
        
    async def index_code_files(
        self,
        file_paths: List[Union[str, Path]],
        batch_size: int = 32
    ) -> List[str]:
        """Index code files for semantic search.
        
        Args:
            file_paths: List of file paths to index
            batch_size: Batch size for processing
            
        Returns:
            List of IDs for the indexed files
        """
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
                content = path.read_text(encoding='utf-8')
                
                # Extract meaningful chunks (functions, classes, etc.)
                # For now, use the full file content
                # TODO: Implement intelligent chunking with tree-sitter
                
                contents.append(content)
                ids.append(str(path))
                metadata_list.append({
                    "file_path": str(path),
                    "file_name": path.name,
                    "file_type": path.suffix,
                    "indexed_at": datetime.now().isoformat(),
                })
                
            except Exception as e:
                logger.error(f"Error reading file {path}: {str(e)}")
                continue
                
        # Index the content
        return await self.index_content(
            contents=contents,
            ids=ids,
            metadata=metadata_list,
            batch_size=batch_size
        )
        
    async def index_session_messages(
        self,
        messages: List[Dict[str, Any]],
        session_id: str,
        batch_size: int = 32
    ) -> List[str]:
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
            metadata_list.append({
                "session_id": session_id,
                "message_index": i,
                "role": message.get('role'),
                "timestamp": message.get('timestamp'),
            })
            
        return await self.index_content(
            contents=contents,
            ids=ids,
            metadata=metadata_list,
            batch_size=batch_size
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
        if not index_path.with_suffix('.faiss').exists():
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
        
    async def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the semantic search index.
        
        Returns:
            Dictionary with index statistics
        """
        vector_count = await self.vector_store.get_vector_count()
        model_info = self.embedding_provider.get_model_info()
        
        return {
            "vector_count": vector_count,
            "embedding_model": model_info.get("id"),
            "embedding_dimension": model_info.get("dimension"),
            "vector_store_type": self.vector_store.__class__.__name__,
            "index_type": getattr(self.vector_store, "index_type", "unknown"),
        }