"""
Example of a self-contained semantic search manager.
"""

from typing import List, Dict, Any, Optional, Union
from pathlib import Path
import asyncio
import logging
from datetime import datetime

from .embeddings import BaseEmbeddingProvider
from .vector_stores import BaseVectorStore, FAISSVectorStore, SearchResult

logger = logging.getLogger(__name__)


class StandaloneSemanticSearchManager:
    """Self-contained semantic search manager that can be used as a library.
    
    Example usage:
        # Initialize with your own providers
        from coda.embeddings import StandaloneOCIEmbeddingProvider
        from coda.vector_stores import FAISSVectorStore
        
        embedding_provider = StandaloneOCIEmbeddingProvider(
            compartment_id="your-compartment-id",
            model_id="multilingual-e5"
        )
        
        vector_store = FAISSVectorStore(
            dimension=768,
            index_type="flat"
        )
        
        manager = StandaloneSemanticSearchManager(
            embedding_provider=embedding_provider,
            vector_store=vector_store,
            index_dir="/path/to/your/index/storage"  # Optional
        )
        
        # Index content
        await manager.index_content(["doc1", "doc2", "doc3"])
        
        # Search
        results = await manager.search("query text")
    """
    
    def __init__(
        self,
        embedding_provider: BaseEmbeddingProvider,
        vector_store: Optional[BaseVectorStore] = None,
        index_dir: Optional[Union[str, Path]] = None
    ):
        """Initialize semantic search manager.
        
        Args:
            embedding_provider: Provider for generating embeddings (required)
            vector_store: Store for vector similarity search (optional, creates FAISS if not provided)
            index_dir: Directory for storing indexes (optional, uses temp if not provided)
        """
        self.embedding_provider = embedding_provider
        
        # Initialize vector store if not provided
        if vector_store is None:
            # Get dimension from embedding provider
            model_info = self.embedding_provider.get_model_info()
            dimension = model_info.get("dimension", 768)
            self.vector_store = FAISSVectorStore(dimension=dimension)
        else:
            self.vector_store = vector_store
            
        # Set index directory
        if index_dir is None:
            # Use temp directory if not specified
            import tempfile
            self.index_dir = Path(tempfile.gettempdir()) / "semantic_search_indexes"
        else:
            self.index_dir = Path(index_dir)
            
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