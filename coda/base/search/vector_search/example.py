"""Example usage of the standalone search module.

This demonstrates how the search module can be used independently
without any Coda-specific dependencies.
"""

import asyncio

from coda.base.search.vector_search.chunking import CodeChunker, TextChunker
from coda.base.search.vector_search.embeddings.mock import MockEmbeddingProvider
from coda.base.search.vector_search.manager import SemanticSearchManager


async def basic_search_example():
    """Basic semantic search example."""
    print("=== Basic Semantic Search Example ===")

    # Create a mock embedding provider
    embedding_provider = MockEmbeddingProvider(dimension=768)

    # Create semantic search manager
    search_manager = SemanticSearchManager(
        embedding_provider=embedding_provider, index_dir="./search_index"
    )

    # Sample documents to index
    documents = [
        "Python is a high-level programming language with dynamic semantics.",
        "JavaScript is the programming language of the web.",
        "Machine learning algorithms can identify patterns in data.",
        "Vector databases store and query high-dimensional vectors efficiently.",
        "Semantic search finds relevant content based on meaning, not just keywords.",
    ]

    # Index the documents
    print(f"Indexing {len(documents)} documents...")
    doc_ids = await search_manager.index_content(documents)
    print(f"Indexed documents with IDs: {doc_ids}")

    # Search for relevant content
    query = "programming languages"
    print(f"\nSearching for: '{query}'")
    results = await search_manager.search(query, k=3)

    print(f"Found {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"{i}. Score: {result.score:.3f}")
        print(f"   Text: {result.text}")
        print(f"   Metadata: {result.metadata}")
        print()


async def chunking_example():
    """Text chunking example."""
    print("=== Text Chunking Example ===")

    # Sample text content
    text_content = """
    This is a sample document that demonstrates text chunking.

    The text chunker can split long documents into smaller, manageable pieces
    while preserving semantic boundaries where possible.

    This is useful for search applications where you want to index smaller
    chunks rather than entire documents.

    Each chunk maintains metadata about its position in the original document.
    """

    # Create text chunker
    chunker = TextChunker(chunk_size=150, chunk_overlap=50, min_chunk_size=50)

    # Chunk the text
    chunks = chunker.chunk_text(text_content.strip())

    print(f"Split text into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  Lines {chunk.start_line}-{chunk.end_line}")
        print(f"  Type: {chunk.chunk_type}")
        print(f"  Text: {repr(chunk.text[:100])}")
        if len(chunk.text) > 100:
            print("  (truncated...)")


async def code_chunking_example():
    """Code chunking example."""
    print("=== Code Chunking Example ===")

    # Sample Python code
    python_code = '''
def fibonacci(n):
    """Calculate the nth Fibonacci number."""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

class Calculator:
    """A simple calculator class."""

    def __init__(self):
        self.history = []

    def add(self, a, b):
        """Add two numbers."""
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result

    def multiply(self, a, b):
        """Multiply two numbers."""
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result

# Example usage
calc = Calculator()
print(calc.add(5, 3))
print(calc.multiply(4, 7))
'''

    # Create code chunker
    chunker = CodeChunker(chunk_size=200, chunk_overlap=50)

    # Chunk the code
    chunks = chunker.chunk_text(python_code.strip(), metadata={"language": "python"})

    print(f"Split code into {len(chunks)} chunks:")
    for i, chunk in enumerate(chunks, 1):
        print(f"\nChunk {i}:")
        print(f"  Lines {chunk.start_line}-{chunk.end_line}")
        print(f"  Type: {chunk.chunk_type}")
        print(f"  Metadata: {chunk.metadata}")
        print("  Code preview:")
        for line in chunk.text.split("\n")[:3]:
            print(f"    {line}")
        if len(chunk.text.split("\n")) > 3:
            print("    ...")


async def file_indexing_example():
    """Example of indexing files from a directory."""
    print("=== File Indexing Example ===")

    # Create embedding provider and search manager
    embedding_provider = MockEmbeddingProvider(dimension=768)
    search_manager = SemanticSearchManager(embedding_provider=embedding_provider)

    # Simulate indexing files (in a real scenario, you'd read actual files)
    file_contents = {
        "README.md": "# My Project\n\nThis is a sample project that demonstrates...",
        "main.py": "#!/usr/bin/env python3\n\ndef main():\n    print('Hello, world!')",
        "config.json": '{"database": {"host": "localhost", "port": 5432}}',
    }

    print("Indexing files...")
    for filename, content in file_contents.items():
        # Add file metadata
        await search_manager.index_content(
            [content], metadata=[{"filename": filename, "type": "file"}]
        )
        print(f"  Indexed: {filename}")

    # Search across all indexed files
    query = "database configuration"
    results = await search_manager.search(query, k=5)

    print(f"\nSearch results for '{query}':")
    for result in results:
        filename = result.metadata.get("filename", "unknown")
        print(f"  {filename}: score={result.score:.3f}")


async def main():
    """Run all examples."""
    print("🔍 Standalone Search Module Examples\n")

    await basic_search_example()
    print("\n" + "=" * 50 + "\n")

    await chunking_example()
    print("\n" + "=" * 50 + "\n")

    await code_chunking_example()
    print("\n" + "=" * 50 + "\n")

    await file_indexing_example()

    print("\n✅ All examples completed!")


if __name__ == "__main__":
    asyncio.run(main())
