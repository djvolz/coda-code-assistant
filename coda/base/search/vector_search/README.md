# Standalone Vector Search Module

This module provides comprehensive vector search and embedding capabilities that are completely independent of Coda-specific code. It can be copy-pasted to other projects and used standalone.

## Features

- **Text Chunking**: Intelligent splitting of documents into embeddings-optimized chunks
- **Multiple Embedding Providers**: Support for various vector embedding backends
- **Vector Storage**: Efficient similarity search with FAISS and other vector stores
- **Vector Search**: High-level semantic search coordination and management
- **Zero Dependencies**: No Coda-specific dependencies

## Module Structure

```
vector_search/
├── __init__.py              # Main module exports
├── constants.py             # Module constants  
├── example.py              # Usage examples
├── chunking.py             # Text chunking utilities
├── manager.py              # Core search management
├── embeddings/             # Embedding providers
│   ├── __init__.py
│   ├── base.py             # Base provider interface
│   ├── mock.py             # Mock provider for testing
│   ├── oci.py              # Oracle Cloud embeddings
│   ├── ollama.py           # Local Ollama embeddings
│   └── sentence_transformers.py  # Hugging Face embeddings
└── vector_stores/          # Vector storage backends
    ├── __init__.py
    ├── base.py             # Base store interface
    └── faiss_store.py      # FAISS implementation
```

## Quick Start

```python
import asyncio
from coda.search import SemanticSearchManager
from coda.search.embeddings.mock import MockEmbeddingProvider

async def main():
    # Create embedding provider
    provider = MockEmbeddingProvider(dimension=768)
    
    # Create search manager
    search = SemanticSearchManager(embedding_provider=provider)
    
    # Index content
    await search.index_content([
        "Python is a programming language",
        "Machine learning uses algorithms to find patterns"
    ])
    
    # Search
    results = await search.search("programming", k=5)
    for result in results:
        print(f"Score: {result.score:.3f} - {result.text}")

asyncio.run(main())
```

## Independence Verification

This module has **zero dependencies** on other Coda modules:

- ✅ No imports from `coda.config`
- ✅ No imports from `coda.cli` 
- ✅ No imports from `coda.session`
- ✅ No imports from `coda.providers`
- ✅ Uses only standard library and optional external packages

## Optional Dependencies

The module gracefully handles missing optional dependencies:

- `faiss-cpu` or `faiss-gpu` - for vector similarity search
- `sentence-transformers` - for Hugging Face embeddings
- `oci` - for Oracle Cloud embeddings
- `ollama` - for local Ollama embeddings

## Copy-Paste Independence

To use this module in another project:

1. Copy the entire `search/` directory
2. Install optional dependencies as needed
3. Import and use - no Coda dependencies required!

```python
# Works in any Python project
from search import SemanticSearchManager
from search.embeddings.mock import MockEmbeddingProvider
```

## Examples

See `example.py` for comprehensive usage examples including:

- Basic semantic search
- Text and code chunking
- File indexing
- Advanced search patterns