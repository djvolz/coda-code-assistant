"""
Tests for FAISS vector store.
"""

import tempfile
from pathlib import Path

import numpy as np
import pytest

from coda.vector_stores.base import SearchResult
from coda.vector_stores.faiss_store import FAISSVectorStore


class TestFAISSVectorStore:
    """Tests for FAISS vector store."""

    @pytest.fixture
    def vector_store(self):
        """Create a test vector store."""
        return FAISSVectorStore(dimension=128, index_type="flat", metric="cosine")

    @pytest.fixture
    def sample_data(self):
        """Create sample data for testing."""
        texts = [
            "Python is a great programming language",
            "Machine learning with neural networks",
            "Vector databases for similarity search",
            "Natural language processing techniques",
            "Software engineering best practices",
        ]

        # Create random embeddings
        np.random.seed(42)
        embeddings = [np.random.randn(128).astype("float32") for _ in texts]

        # Normalize for cosine similarity
        embeddings = [e / np.linalg.norm(e) for e in embeddings]

        ids = [f"doc_{i}" for i in range(len(texts))]

        metadata = [
            {"topic": "programming", "language": "en"},
            {"topic": "ml", "language": "en"},
            {"topic": "database", "language": "en"},
            {"topic": "nlp", "language": "en"},
            {"topic": "engineering", "language": "en"},
        ]

        return texts, embeddings, ids, metadata

    @pytest.mark.asyncio
    async def test_add_vectors(self, vector_store, sample_data):
        """Test adding vectors to the store."""
        texts, embeddings, ids, metadata = sample_data

        result_ids = await vector_store.add_vectors(
            texts=texts, embeddings=embeddings, ids=ids, metadata=metadata
        )

        assert result_ids == ids
        assert await vector_store.get_vector_count() == 5

    @pytest.mark.asyncio
    async def test_search(self, vector_store, sample_data):
        """Test searching for similar vectors."""
        texts, embeddings, ids, metadata = sample_data

        # Add vectors
        await vector_store.add_vectors(texts, embeddings, ids, metadata)

        # Search with first embedding (should find itself)
        results = await vector_store.search(embeddings[0], k=3)

        assert len(results) == 3
        assert isinstance(results[0], SearchResult)
        assert results[0].id == "doc_0"
        assert results[0].text == texts[0]
        assert results[0].score > 0.99  # Should be very similar to itself

    @pytest.mark.asyncio
    async def test_search_with_filter(self, vector_store, sample_data):
        """Test searching with metadata filter."""
        texts, embeddings, ids, metadata = sample_data

        # Add vectors
        await vector_store.add_vectors(texts, embeddings, ids, metadata)

        # Search for ML-related content
        ml_embedding = embeddings[1]  # ML document
        results = await vector_store.search(ml_embedding, k=5, filter={"topic": "ml"})

        # Should only find the ML document
        assert len(results) == 1
        assert results[0].id == "doc_1"
        assert results[0].metadata["topic"] == "ml"

    @pytest.mark.asyncio
    async def test_delete_vectors(self, vector_store, sample_data):
        """Test deleting vectors."""
        texts, embeddings, ids, metadata = sample_data

        # Add vectors
        await vector_store.add_vectors(texts, embeddings, ids, metadata)

        # Delete some vectors
        deleted = await vector_store.delete_vectors(["doc_0", "doc_2"])

        assert deleted == 2

    @pytest.mark.asyncio
    async def test_update_vectors(self, vector_store, sample_data):
        """Test updating vector metadata."""
        texts, embeddings, ids, metadata = sample_data

        # Add vectors
        await vector_store.add_vectors(texts, embeddings, ids, metadata)

        # Update metadata
        new_metadata = [{"topic": "updated", "version": 2}]
        updated = await vector_store.update_vectors(ids=["doc_0"], metadata=new_metadata)

        assert updated == 1
        assert vector_store.metadata["doc_0"]["topic"] == "updated"

    @pytest.mark.asyncio
    async def test_clear(self, vector_store, sample_data):
        """Test clearing all vectors."""
        texts, embeddings, ids, metadata = sample_data

        # Add vectors
        await vector_store.add_vectors(texts, embeddings, ids, metadata)

        # Clear
        count = await vector_store.clear()

        assert count == 5
        assert await vector_store.get_vector_count() == 0

    @pytest.mark.asyncio
    async def test_save_and_load_index(self, vector_store, sample_data):
        """Test saving and loading index."""
        texts, embeddings, ids, metadata = sample_data

        # Add vectors
        await vector_store.add_vectors(texts, embeddings, ids, metadata)

        # Save index
        with tempfile.TemporaryDirectory() as tmpdir:
            index_path = Path(tmpdir) / "test_index"
            await vector_store.save_index(str(index_path))

            # Create new store and load
            new_store = FAISSVectorStore(dimension=128)
            await new_store.load_index(str(index_path))

            # Verify loaded data
            assert await new_store.get_vector_count() == 5
            assert new_store.texts["doc_0"] == texts[0]

            # Test search on loaded index
            results = await new_store.search(embeddings[0], k=1)
            assert results[0].id == "doc_0"

    def test_different_metrics(self):
        """Test different distance metrics."""
        # L2 distance
        store_l2 = FAISSVectorStore(dimension=128, metric="l2")
        assert store_l2.metric == "l2"

        # Inner product
        store_ip = FAISSVectorStore(dimension=128, metric="inner_product")
        assert store_ip.metric == "inner_product"

    def test_different_index_types(self):
        """Test different index types."""
        # IVF index
        store_ivf = FAISSVectorStore(dimension=128, index_type="ivf", nlist=10)
        assert store_ivf.index_type == "ivf"

        # HNSW index
        store_hnsw = FAISSVectorStore(dimension=128, index_type="hnsw", M=16, ef_construction=100)
        assert store_hnsw.index_type == "hnsw"

    @pytest.mark.asyncio
    async def test_auto_generated_ids(self, vector_store):
        """Test automatic ID generation."""
        texts = ["Test document"]
        embeddings = [np.random.randn(128).astype("float32")]

        # Add without IDs
        ids = await vector_store.add_vectors(texts, embeddings)

        assert len(ids) == 1
        assert isinstance(ids[0], str)
        assert len(ids[0]) > 0  # Should be a UUID

    @pytest.mark.skip(reason="Test is complex due to module import caching")
    def test_import_error_handling(self):
        """Test handling when FAISS is not installed."""
        # This test is skipped because it's difficult to properly mock
        # module imports in a way that doesn't affect other tests
        pass
