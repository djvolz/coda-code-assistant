"""
Tests for semantic search functionality.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import numpy as np
import pytest

from coda.embeddings.base import EmbeddingResult
from coda.semantic_search import SemanticSearchManager
from coda.vector_stores.base import SearchResult


class TestSemanticSearchManager:
    """Tests for semantic search manager."""

    @pytest.fixture
    def mock_embedding_provider(self):
        """Create mock embedding provider."""
        provider = Mock()

        # Mock model info
        provider.get_model_info.return_value = {
            "id": "test-model",
            "dimension": 128,
            "provider": "mock",
        }

        # Mock embed_text
        async def mock_embed_text(text):
            embedding = np.random.randn(128).astype("float32")
            return EmbeddingResult(text=text, embedding=embedding, model="test-model")

        provider.embed_text = mock_embed_text

        # Mock embed_batch
        async def mock_embed_batch(texts):
            results = []
            for text in texts:
                embedding = np.random.randn(128).astype("float32")
                results.append(EmbeddingResult(text=text, embedding=embedding, model="test-model"))
            return results

        provider.embed_batch = mock_embed_batch

        return provider

    @pytest.fixture
    def mock_vector_store(self):
        """Create mock vector store."""
        store = Mock()

        # Storage for testing
        store._vectors = {}
        store._counter = 0

        # Mock add_vectors
        async def mock_add_vectors(texts, embeddings, ids=None, metadata=None):
            if ids is None:
                ids = [f"id_{store._counter + i}" for i in range(len(texts))]

            for i, (text, embedding, id_) in enumerate(zip(texts, embeddings, ids, strict=False)):
                store._vectors[id_] = {
                    "text": text,
                    "embedding": embedding,
                    "metadata": metadata[i] if metadata else {},
                }

            store._counter += len(texts)
            return ids

        store.add_vectors = mock_add_vectors

        # Mock search
        async def mock_search(query_embedding, k=10, filter=None):
            results = []
            for id_, data in store._vectors.items():
                if filter:
                    meta = data.get("metadata", {})
                    if not all(meta.get(k) == v for k, v in filter.items()):
                        continue

                # Simple similarity: random score
                score = np.random.random()
                results.append(
                    SearchResult(
                        id=id_, text=data["text"], score=score, metadata=data.get("metadata")
                    )
                )

            # Sort by score and limit
            results.sort(key=lambda x: x.score, reverse=True)
            return results[:k]

        store.search = mock_search

        # Mock other methods
        async def mock_get_vector_count():
            return len(store._vectors)

        store.get_vector_count = mock_get_vector_count

        async def mock_clear():
            count = len(store._vectors)
            store._vectors.clear()
            return count

        store.clear = mock_clear

        store.save_index = AsyncMock()
        store.load_index = AsyncMock()

        return store

    @pytest.fixture
    def search_manager(self, mock_embedding_provider, mock_vector_store):
        """Create search manager with mocks."""
        return SemanticSearchManager(
            embedding_provider=mock_embedding_provider, vector_store=mock_vector_store
        )

    @pytest.mark.asyncio
    async def test_index_content(self, search_manager):
        """Test indexing content."""
        contents = [
            "Python programming guide",
            "Machine learning tutorial",
            "Database optimization tips",
        ]

        ids = await search_manager.index_content(contents)

        assert len(ids) == 3
        assert all(isinstance(id_, str) for id_ in ids)

    @pytest.mark.asyncio
    async def test_index_content_with_metadata(self, search_manager):
        """Test indexing content with metadata."""
        contents = ["Test document"]
        metadata = [{"category": "test", "version": 1}]

        ids = await search_manager.index_content(contents=contents, metadata=metadata)

        assert len(ids) == 1
        # Verify metadata was stored
        vector_data = search_manager.vector_store._vectors[ids[0]]
        assert vector_data["metadata"]["category"] == "test"

    @pytest.mark.asyncio
    async def test_search(self, search_manager):
        """Test searching for content."""
        # Index some content first
        contents = [
            "Python programming guide",
            "Machine learning with Python",
            "Web development tutorial",
        ]
        await search_manager.index_content(contents)

        # Search
        results = await search_manager.search("Python tutorial", k=2)

        assert len(results) <= 2
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_search_with_filter(self, search_manager):
        """Test searching with metadata filter."""
        # Index content with metadata
        contents = ["Doc 1", "Doc 2", "Doc 3"]
        metadata = [{"type": "guide"}, {"type": "tutorial"}, {"type": "guide"}]
        await search_manager.index_content(contents, metadata=metadata)

        # Search with filter
        results = await search_manager.search("document", k=10, filter={"type": "guide"})

        # Should only return guides
        for result in results:
            assert result.metadata["type"] == "guide"

    @pytest.mark.asyncio
    async def test_index_code_files(self, search_manager):
        """Test indexing code files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files with enough content to create chunks
            file1 = Path(tmpdir) / "test1.py"
            file1.write_text(
                """def hello():
    \"\"\"Say hello to the world.\"\"\"
    print("Hello, world!")
    return 'world'

def goodbye():
    \"\"\"Say goodbye.\"\"\"
    print("Goodbye!")
    return 'bye'
"""
            )

            file2 = Path(tmpdir) / "test2.py"
            file2.write_text(
                """class MyClass:
    \"\"\"A sample class for testing.\"\"\"

    def __init__(self):
        self.value = 42

    def get_value(self):
        return self.value
"""
            )

            # Index files
            ids = await search_manager.index_code_files([file1, file2])

            # With chunking, we might get more than 2 IDs
            assert len(ids) >= 2

            # Verify metadata
            for id_ in ids:
                data = search_manager.vector_store._vectors[id_]
                assert "file_path" in data["metadata"]
                assert data["metadata"]["file_type"] == ".py"

    @pytest.mark.asyncio
    async def test_index_session_messages(self, search_manager):
        """Test indexing session messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
        ]
        session_id = "test-session"

        ids = await search_manager.index_session_messages(messages, session_id)

        assert len(ids) == 3

        # Verify IDs and metadata
        for i, id_ in enumerate(ids):
            assert id_ == f"{session_id}_msg_{i}"
            data = search_manager.vector_store._vectors[id_]
            assert data["metadata"]["session_id"] == session_id
            assert data["metadata"]["message_index"] == i

    @pytest.mark.asyncio
    async def test_save_and_load_index(self, search_manager):
        """Test saving and loading index."""
        # Index some content
        contents = ["Test content"]
        await search_manager.index_content(contents)

        # Save
        await search_manager.save_index("test_index")

        # Verify save was called
        search_manager.vector_store.save_index.assert_called_once()

        # Mock the file exists check for load
        with patch("pathlib.Path.exists", return_value=True):
            # Load
            await search_manager.load_index("test_index")

        # Verify load was called
        search_manager.vector_store.load_index.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_index(self, search_manager):
        """Test clearing the index."""
        # Index some content
        contents = ["Test 1", "Test 2"]
        await search_manager.index_content(contents)

        # Clear
        count = await search_manager.clear_index()

        # Should have cleared 2 items
        assert count == 2

    @pytest.mark.asyncio
    async def test_get_stats(self, search_manager):
        """Test getting index statistics."""
        # Index some content
        contents = ["Test 1", "Test 2", "Test 3"]
        await search_manager.index_content(contents)

        stats = await search_manager.get_stats()

        assert stats["vector_count"] == 3
        assert stats["embedding_model"] == "test-model"
        assert stats["embedding_dimension"] == 128
        assert "vector_store_type" in stats

    @pytest.mark.asyncio
    async def test_batch_processing(self, search_manager):
        """Test batch processing of large content."""
        # Create 100 documents
        contents = [f"Document {i}" for i in range(100)]

        # Index with small batch size
        ids = await search_manager.index_content(contents, batch_size=10)

        assert len(ids) == 100

        # Verify all were indexed
        vector_count = await search_manager.vector_store.get_vector_count()
        assert vector_count == 100

    def test_init_requires_provider(self):
        """Test that initialization requires an embedding provider."""
        # Cannot create without a provider
        with pytest.raises(TypeError):
            SemanticSearchManager()

    def test_init_with_provider(self):
        """Test initialization with embedding provider."""
        # Mock provider
        mock_provider = Mock()
        mock_provider.get_model_info.return_value = {"dimension": 768}

        # Create manager with provider
        manager = SemanticSearchManager(embedding_provider=mock_provider)

        assert manager.embedding_provider == mock_provider
        assert manager.vector_store is not None
        assert manager.index_dir.exists()
