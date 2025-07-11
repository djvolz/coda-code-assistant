# Search Module

The Search module provides semantic code search capabilities using vector embeddings for intelligent code discovery.

## Features

- 🔍 **Semantic Search**: Find code by meaning, not just keywords
- 🧠 **Vector Embeddings**: Understand code context and relationships
- 📊 **Multi-Language Support**: Search across different programming languages
- ⚡ **Incremental Indexing**: Efficiently update changed files
- 🎯 **Similarity Search**: Find code similar to a given snippet

## Quick Start

```python
import asyncio
from coda.base.search import SearchManager

async def main():
    # Initialize search manager
    search = SearchManager({
        "search": {
            "index_path": "~/.coda/search_index"
        }
    })
    
    # Index a directory
    file_count = await search.index_directory("/path/to/project")
    print(f"Indexed {file_count} files")
    
    # Search semantically
    results = await search.search("function that handles user authentication")
    
    for result in results:
        print(f"{result.file}:{result.line} (score: {result.score:.2f})")
        print(result.content)

asyncio.run(main())
```

## Core Features

### Semantic Search

```python
# Search by meaning
results = await search.search("calculate fibonacci sequence")

# Search with options
results = await search.search(
    query="error handling in database connections",
    limit=20,              # Number of results
    threshold=0.8          # Minimum relevance score
)
```

### Code Similarity

```python
# Find similar code patterns
snippet = """
def process_items(items):
    return [transform(item) for item in items if item.valid]
"""

similar = await search.find_similar(snippet, limit=5)
```

### File-Specific Search

```python
# Search within a specific file
results = await search.search_in_file(
    "/path/to/module.py",
    "class initialization"
)
```

## Indexing

### Directory Indexing

```python
# Index entire directory
await search.index_directory("/path/to/project")

# Force re-index
await search.index_directory("/path/to/project", force=True)

# Update only changed files
updated = await search.update_index("/path/to/project")
```

### File Management

```python
# Index single file
await search.index_file("/path/to/new_file.py")

# Remove from index
await search.remove_from_index("/path/to/deleted_file.py")

# Clear entire index
search.clear_index()
```

## Configuration

```toml
[search]
# Index storage location
index_path = "~/.coda/search_index"

# File extensions to index
extensions = [".py", ".js", ".ts", ".java", ".go", ".rs", ".cpp", ".c"]

# Patterns to exclude
exclude_patterns = [
    "**/node_modules/**",
    "**/.git/**",
    "**/venv/**",
    "**/__pycache__/**"
]

# Chunk size for splitting files
chunk_size = 500

# Overlap between chunks
chunk_overlap = 50

# Maximum file size to index (MB)
max_file_size = 10

# Embedding model
embedding_model = "all-MiniLM-L6-v2"
```

## Advanced Usage

### Custom Embeddings

```python
# Use different embedding models
search = SearchManager({
    "search": {
        "embedding_model": "microsoft/codebert-base",
        "embedding_provider": "sentence_transformers"
    }
})
```

### Incremental Updates

```python
class AutoIndexer:
    """Automatically keep index up to date."""
    
    def __init__(self, search: SearchManager, watch_path: str):
        self.search = search
        self.watch_path = watch_path
    
    async def watch(self):
        """Watch for file changes and update index."""
        import watchdog.observers
        # Implementation for file watching
```

### Search Analytics

```python
# Get index statistics
stats = search.get_index_stats()
print(f"Files indexed: {stats.file_count}")
print(f"Total chunks: {stats.chunk_count}")
print(f"Index size: {stats.size_mb:.1f} MB")

# Optimize index for better performance
search.optimize_index()
```

## Architecture

### Components

1. **Embeddings**: Convert code to vector representations
   - Sentence Transformers (default)
   - OCI Embeddings
   - Ollama Embeddings

2. **Vector Stores**: Store and search embeddings
   - FAISS (default)
   - ChromaDB (planned)
   - Pinecone (planned)

3. **Code Chunking**: Split files intelligently
   - Syntax-aware chunking
   - Overlap for context preservation

### Submodules

- **vector_search/**: Core vector search implementation
- **map/**: Code structure analysis and mapping

## Performance Tips

1. **Batch Indexing**: Index multiple files concurrently
2. **Chunk Size**: Adjust based on your code structure
3. **Exclude Patterns**: Skip non-code files and dependencies
4. **Regular Optimization**: Run `optimize_index()` periodically

## API Documentation

For detailed API documentation, see [Search API Reference](../../../docs/api/search.md).

## Examples

- [Code Analyzer](../../../tests/examples/code_analyzer/) - Full search integration
- [Search Examples](./example.py) - Basic usage patterns
- [Vector Search Example](./vector_search/example.py) - Advanced vector search

## Troubleshooting

### Common Issues

1. **Out of Memory**: Reduce chunk_size or index in batches
2. **Slow Indexing**: Check exclude patterns, reduce max_file_size
3. **Poor Results**: Try different embedding models or adjust chunk_size
4. **Index Corruption**: Clear and rebuild index

### Debug Mode

```python
# Enable debug logging
import logging
logging.basicConfig(level=logging.DEBUG)

# Now search operations will show detailed logs
```