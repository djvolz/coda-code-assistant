"""Integration tests for semantic search functionality."""

import tempfile
from pathlib import Path

import pytest

from coda.embeddings.factory import create_embedding_provider
from coda.embeddings.mock import MockEmbeddingProvider
from coda.semantic_search import SemanticSearchManager


@pytest.mark.integration
class TestSemanticSearchIntegration:
    """Integration tests for the semantic search system."""

    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for test files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    async def search_manager(self):
        """Create a search manager with mock provider."""
        provider = MockEmbeddingProvider(dimension=384)
        manager = SemanticSearchManager(embedding_provider=provider)
        yield manager
        # Cleanup
        await manager.clear_index()

    @pytest.mark.asyncio
    async def test_basic_indexing_and_search(self, search_manager):
        """Test basic content indexing and search."""
        # Index some content
        contents = [
            "Python is a high-level programming language",
            "JavaScript runs in the browser",
            "Machine learning with Python and TensorFlow",
            "Web development using React and JavaScript",
        ]

        ids = await search_manager.index_content(contents)
        assert len(ids) == 4

        # Search for Python-related content
        results = await search_manager.search("Python programming", k=2)
        assert len(results) == 2
        assert any("Python" in result.text for result in results)

        # Search for JavaScript content
        results = await search_manager.search("JavaScript browser", k=2)
        assert len(results) == 2
        assert any("JavaScript" in result.text for result in results)

    @pytest.mark.asyncio
    async def test_file_indexing_with_chunking(self, search_manager, temp_dir):
        """Test indexing code files with chunking."""
        # Create a Python file
        python_file = temp_dir / "test.py"
        python_code = '''"""Test module for semantic search."""

def calculate_sum(a, b):
    """Calculate the sum of two numbers."""
    return a + b

def calculate_product(a, b):
    """Calculate the product of two numbers."""
    return a * b

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.result = 0

    def add(self, value):
        """Add a value to the result."""
        self.result += value
        return self.result

    def multiply(self, value):
        """Multiply the result by a value."""
        self.result *= value
        return self.result
'''
        python_file.write_text(python_code)

        # Index the file
        ids = await search_manager.index_code_files([python_file])
        assert len(ids) > 1  # Should create multiple chunks

        # Search for specific functions
        results = await search_manager.search("calculate sum of numbers", k=3)
        assert len(results) > 0
        assert any("calculate_sum" in result.text for result in results)

        # Search for class
        results = await search_manager.search("calculator class multiply", k=3)
        assert len(results) > 0
        assert any("Calculator" in result.text or "multiply" in result.text for result in results)

    @pytest.mark.asyncio
    async def test_metadata_filtering(self, search_manager, temp_dir):
        """Test search with metadata filtering."""
        # Create files of different types
        py_file = temp_dir / "script.py"
        py_file.write_text("def hello_python():\n    print('Hello from Python')")

        js_file = temp_dir / "script.js"
        js_file.write_text("function helloJavaScript() {\n    console.log('Hello from JS');\n}")

        # Index both files
        await search_manager.index_code_files([py_file, js_file])

        # Search all
        all_results = await search_manager.search("hello function", k=10)
        assert len(all_results) >= 2

        # Search with filter (Python files only)
        py_results = await search_manager.search(
            "hello function", k=10, filter={"file_type": ".py"}
        )
        assert all(r.metadata.get("file_type") == ".py" for r in py_results)
        assert not any(r.metadata.get("file_type") == ".js" for r in py_results)

    @pytest.mark.asyncio
    async def test_session_message_indexing(self, search_manager):
        """Test indexing conversation messages."""
        messages = [
            {"role": "user", "content": "How do I create a Python function?"},
            {"role": "assistant", "content": "To create a Python function, use the def keyword"},
            {"role": "user", "content": "Can you show an example?"},
            {"role": "assistant", "content": "def greet(name):\n    return f'Hello, {name}'"},
        ]

        ids = await search_manager.index_session_messages(messages, session_id="test-session")
        assert len(ids) == 4

        # Search for function-related messages
        results = await search_manager.search("Python function def", k=2)
        assert len(results) > 0
        assert any("def" in result.text for result in results)

    @pytest.mark.asyncio
    async def test_index_persistence(self, search_manager, temp_dir):
        """Test saving and loading indexes."""
        # Index some content
        contents = ["First document", "Second document", "Third document"]
        await search_manager.index_content(contents)

        # Get initial stats
        stats1 = await search_manager.get_stats()
        initial_count = stats1["vector_count"]

        # Save index
        index_name = "test_index"
        search_manager.index_dir = temp_dir  # Use temp dir for test
        await search_manager.save_index(index_name)

        # Clear and verify empty
        await search_manager.clear_index()
        stats2 = await search_manager.get_stats()
        assert stats2["vector_count"] == 0

        # Load index
        await search_manager.load_index(index_name)

        # Verify restored
        stats3 = await search_manager.get_stats()
        assert stats3["vector_count"] == initial_count

        # Verify search works
        results = await search_manager.search("document", k=2)
        assert len(results) == 2

    @pytest.mark.asyncio
    async def test_large_batch_indexing(self, search_manager):
        """Test indexing large batches of content."""
        # Create 100 documents
        contents = [f"Document {i}: This is test content about topic {i % 10}" for i in range(100)]

        # Index with small batch size
        ids = await search_manager.index_content(contents, batch_size=10)
        assert len(ids) == 100

        # Verify all indexed
        stats = await search_manager.get_stats()
        assert stats["vector_count"] == 100

        # Search should work
        results = await search_manager.search("topic 5", k=5)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_empty_and_edge_cases(self, search_manager):
        """Test edge cases like empty content."""
        # Empty content list
        ids = await search_manager.index_content([])
        assert ids == []

        # Empty search on empty index
        results = await search_manager.search("anything", k=5)
        assert results == []

        # Index single item
        ids = await search_manager.index_content(["Single item"])
        assert len(ids) == 1

        # Search with k larger than index
        results = await search_manager.search("item", k=10)
        assert len(results) == 1

    @pytest.mark.asyncio
    async def test_unicode_content(self, search_manager):
        """Test handling of Unicode content."""
        contents = [
            "Hello 世界",
            "Python 编程",
            "🌍 Global search",
            "Émojis and spëcial characters",
        ]

        ids = await search_manager.index_content(contents)
        assert len(ids) == 4

        # Search Unicode
        results = await search_manager.search("世界", k=2)
        assert len(results) > 0

        results = await search_manager.search("🌍", k=2)
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_custom_ids_and_metadata(self, search_manager):
        """Test indexing with custom IDs and metadata."""
        contents = ["Doc 1", "Doc 2", "Doc 3"]
        custom_ids = ["id-001", "id-002", "id-003"]
        metadata = [
            {"category": "A", "priority": 1},
            {"category": "B", "priority": 2},
            {"category": "A", "priority": 3},
        ]

        ids = await search_manager.index_content(
            contents=contents, ids=custom_ids, metadata=metadata
        )
        assert ids == custom_ids

        # Search and verify metadata
        results = await search_manager.search("Doc", k=3)
        assert len(results) == 3
        assert all(r.metadata is not None for r in results)
        assert any(r.metadata.get("category") == "A" for r in results)


@pytest.mark.integration
class TestProviderIntegration:
    """Test integration with different embedding providers."""

    @pytest.mark.asyncio
    async def test_with_sentence_transformers(self):
        """Test with sentence-transformers provider if available."""
        try:
            provider = create_embedding_provider("sentence-transformers")
            manager = SemanticSearchManager(embedding_provider=provider)

            # Basic test
            contents = ["Test with sentence transformers"]
            ids = await manager.index_content(contents)
            assert len(ids) == 1

            results = await manager.search("transformers", k=1)
            assert len(results) == 1

        except ImportError:
            pytest.skip("sentence-transformers not installed")

    @pytest.mark.asyncio
    async def test_provider_switching(self):
        """Test switching between providers."""
        # Start with mock
        mock_provider = MockEmbeddingProvider(dimension=384)
        manager1 = SemanticSearchManager(embedding_provider=mock_provider)

        await manager1.index_content(["Content for mock provider"])
        stats1 = await manager1.get_stats()
        assert stats1["embedding_model"] == "mock-384d"
        assert stats1["embedding_dimension"] == 384

        # Create new manager with different dimension
        mock_provider2 = MockEmbeddingProvider(dimension=768)
        manager2 = SemanticSearchManager(embedding_provider=mock_provider2)

        await manager2.index_content(["Content for second provider"])
        stats2 = await manager2.get_stats()
        assert stats2["embedding_model"] == "mock-768d"
        assert stats2["embedding_dimension"] == 768


@pytest.mark.integration
class TestChunkingIntegration:
    """Test integration of chunking with semantic search."""

    @pytest.mark.asyncio
    async def test_chunking_preserves_context(self, temp_dir):
        """Test that chunking preserves code context."""
        provider = MockEmbeddingProvider(dimension=384)
        manager = SemanticSearchManager(embedding_provider=provider)

        # Create a file with multiple functions
        py_file = temp_dir / "functions.py"
        code = '''def first_function():
    """This is the first function."""
    # Some implementation
    return 1

def second_function():
    """This is the second function."""
    # Different implementation
    return 2

def third_function():
    """This is the third function."""
    # Another implementation
    return 3
'''
        py_file.write_text(code)

        # Index with small chunk size to force splitting
        ids = await manager.index_code_files([py_file], chunk_size=150)
        assert len(ids) >= 2  # Should create multiple chunks

        # Search for specific function
        results = await manager.search("second function implementation", k=1)
        assert len(results) == 1
        assert "second_function" in results[0].text

        # Verify chunk metadata
        assert results[0].metadata["chunk_type"] in ["function", "module"]
        assert "start_line" in results[0].metadata
        assert "end_line" in results[0].metadata
