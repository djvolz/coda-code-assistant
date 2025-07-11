# Search Module API Reference

## Overview

The Search module provides semantic code search capabilities using vector embeddings. It enables intelligent code discovery by understanding the meaning and context of code, not just keyword matching.

## Installation

The Search module requires additional dependencies:

```bash
pip install coda-assistant[search]
```

## Quick Start

```python
from coda.base.search import SearchManager

# Initialize search manager
search = SearchManager({"search": {"index_path": "~/.coda/search_index"}})

# Index a directory
await search.index_directory("/path/to/project")

# Search semantically
results = await search.search("function that handles user authentication")

# Display results
for result in results:
    print(f"{result['file']}:{result['line']} - {result['score']:.2f}")
    print(result['content'])
```

## API Reference

### SearchManager Class

```python
class SearchManager:
    """Manages code search indexing and querying."""
    
    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize search manager.
        
        Args:
            config: Configuration with search settings
        """
```

#### Indexing Methods

##### async index_directory(path: str, force: bool = False) -> int

Index all supported files in a directory.

```python
# Index a project
file_count = await search.index_directory("/path/to/project")
print(f"Indexed {file_count} files")

# Force re-indexing
await search.index_directory("/path/to/project", force=True)
```

##### async index_file(file_path: str) -> bool

Index a single file.

```python
success = await search.index_file("/path/to/file.py")
```

##### async update_index(path: str) -> int

Update index for modified files only.

```python
updated = await search.update_index("/path/to/project")
print(f"Updated {updated} files")
```

##### async remove_from_index(path: str) -> int

Remove files from the index.

```python
removed = await search.remove_from_index("/path/to/old_file.py")
```

#### Search Methods

##### async search(query: str, limit: int = 10, threshold: float = 0.7) -> list[SearchResult]

Search for code semantically.

```python
# Basic search
results = await search.search("calculate fibonacci sequence")

# With options
results = await search.search(
    query="error handling in database connections",
    limit=20,
    threshold=0.8  # Higher threshold = more relevant results
)
```

##### async search_in_file(file_path: str, query: str) -> list[SearchResult]

Search within a specific file.

```python
results = await search.search_in_file(
    "/path/to/module.py",
    "class initialization"
)
```

##### async find_similar(code_snippet: str, limit: int = 5) -> list[SearchResult]

Find code similar to a given snippet.

```python
snippet = """
def process_data(items):
    return [transform(item) for item in items if item.valid]
"""

similar = await search.find_similar(snippet)
```

#### Index Management

##### get_index_stats() -> IndexStats

Get statistics about the search index.

```python
stats = search.get_index_stats()
print(f"Total files: {stats.file_count}")
print(f"Total chunks: {stats.chunk_count}")
print(f"Index size: {stats.size_mb:.1f} MB")
```

##### clear_index() -> None

Clear the entire search index.

```python
search.clear_index()
```

##### optimize_index() -> None

Optimize index for better performance.

```python
search.optimize_index()
```

### SearchResult Type

```python
@dataclass
class SearchResult:
    """A search result."""
    file: str              # File path
    content: str           # Matching content
    line: int             # Line number
    score: float          # Relevance score (0-1)
    language: str         # Programming language
    context: str | None   # Surrounding context
```

### Configuration

```python
config = {
    "search": {
        # Index storage location
        "index_path": "~/.coda/search_index",
        
        # File extensions to index
        "extensions": [".py", ".js", ".ts", ".java", ".go", ".rs"],
        
        # Patterns to exclude
        "exclude_patterns": ["**/node_modules/**", "**/.git/**"],
        
        # Chunk size for indexing
        "chunk_size": 500,
        
        # Overlap between chunks
        "chunk_overlap": 50,
        
        # Embedding model
        "embedding_model": "all-MiniLM-L6-v2",
        
        # Maximum file size to index (MB)
        "max_file_size": 10
    }
}
```

## Examples

### Basic Code Search

```python
import asyncio
from coda.base.search import SearchManager

async def search_codebase():
    search = SearchManager()
    
    # Index the current directory
    print("Indexing codebase...")
    file_count = await search.index_directory(".")
    print(f"Indexed {file_count} files")
    
    # Search for specific functionality
    queries = [
        "user authentication",
        "database connection pooling",
        "rate limiting implementation",
        "error handling middleware"
    ]
    
    for query in queries:
        print(f"\nSearching for: {query}")
        results = await search.search(query, limit=3)
        
        for result in results:
            print(f"  {result.file}:{result.line} (score: {result.score:.2f})")
            print(f"    {result.content[:100]}...")

# Run the search
asyncio.run(search_codebase())
```

### Incremental Indexing

```python
class IncrementalIndexer:
    """Maintain an up-to-date search index."""
    
    def __init__(self, search: SearchManager, watch_path: str):
        self.search = search
        self.watch_path = watch_path
        self.last_update = {}
    
    async def update(self):
        """Update index for changed files."""
        import os
        from pathlib import Path
        
        updated = 0
        for root, _, files in os.walk(self.watch_path):
            for file in files:
                file_path = Path(root) / file
                
                # Skip if not a code file
                if file_path.suffix not in self.search.config.get("extensions", []):
                    continue
                
                # Check modification time
                mtime = file_path.stat().st_mtime
                if file_path in self.last_update:
                    if mtime <= self.last_update[file_path]:
                        continue
                
                # Re-index modified file
                await self.search.index_file(str(file_path))
                self.last_update[file_path] = mtime
                updated += 1
        
        return updated

# Usage
indexer = IncrementalIndexer(search, "/path/to/project")
updated = await indexer.update()
print(f"Updated {updated} files")
```

### Code Similarity Analysis

```python
async def find_duplicate_code(search: SearchManager, threshold: float = 0.9):
    """Find potentially duplicate code blocks."""
    
    # Get all indexed code chunks
    stats = search.get_index_stats()
    
    duplicates = []
    checked = set()
    
    # Sample some code blocks
    sample_results = await search.search("def", limit=100)
    
    for result in sample_results:
        if result.content in checked:
            continue
        
        checked.add(result.content)
        
        # Find similar code
        similar = await search.find_similar(
            result.content,
            limit=10
        )
        
        # Filter by threshold
        matches = [
            s for s in similar 
            if s.score > threshold and s.file != result.file
        ]
        
        if matches:
            duplicates.append({
                "original": result,
                "duplicates": matches
            })
    
    return duplicates

# Find duplicates
dupes = await find_duplicate_code(search)
for dup in dupes:
    print(f"\nPotential duplicate in {dup['original'].file}:")
    for match in dup['duplicates']:
        print(f"  - {match.file} (similarity: {match.score:.2%})")
```

### Contextual Code Search

```python
class ContextualSearch:
    """Search with additional context."""
    
    def __init__(self, search: SearchManager):
        self.search = search
    
    async def search_with_context(
        self,
        query: str,
        context_lines: int = 5
    ) -> list[dict]:
        """Search and include surrounding context."""
        
        results = await self.search.search(query)
        enhanced_results = []
        
        for result in results:
            # Read the full file
            with open(result.file, 'r') as f:
                lines = f.readlines()
            
            # Extract context
            start = max(0, result.line - context_lines - 1)
            end = min(len(lines), result.line + context_lines)
            
            context = {
                "file": result.file,
                "line": result.line,
                "score": result.score,
                "match": result.content,
                "before": lines[start:result.line-1],
                "after": lines[result.line:end]
            }
            
            enhanced_results.append(context)
        
        return enhanced_results

# Search with context
ctx_search = ContextualSearch(search)
results = await ctx_search.search_with_context("TODO", context_lines=3)
```

### Search Analytics

```python
class SearchAnalytics:
    """Track and analyze search patterns."""
    
    def __init__(self):
        self.query_history = []
        self.result_clicks = {}
    
    def log_search(self, query: str, result_count: int):
        """Log a search query."""
        self.query_history.append({
            "query": query,
            "timestamp": datetime.now(),
            "result_count": result_count
        })
    
    def log_click(self, query: str, result_file: str):
        """Log when a result is selected."""
        key = (query, result_file)
        self.result_clicks[key] = self.result_clicks.get(key, 0) + 1
    
    def get_popular_queries(self, limit: int = 10) -> list[tuple[str, int]]:
        """Get most popular search queries."""
        from collections import Counter
        
        queries = [h["query"] for h in self.query_history]
        return Counter(queries).most_common(limit)
    
    def get_effective_queries(self) -> list[str]:
        """Get queries that led to clicked results."""
        clicked_queries = {query for query, _ in self.result_clicks.keys()}
        return list(clicked_queries)

# Track search usage
analytics = SearchAnalytics()

# During search
results = await search.search(query)
analytics.log_search(query, len(results))

# When user selects a result
analytics.log_click(query, selected_result.file)
```

## Advanced Usage

### Custom Embedding Models

```python
from sentence_transformers import SentenceTransformer

class CustomEmbeddingSearch(SearchManager):
    """Search with custom embedding model."""
    
    def __init__(self, model_name: str, **kwargs):
        super().__init__(**kwargs)
        self.model = SentenceTransformer(model_name)
    
    def _encode(self, text: str) -> np.ndarray:
        """Encode text to embeddings."""
        return self.model.encode(text)

# Use specialized code model
search = CustomEmbeddingSearch("microsoft/codebert-base")
```

### Multi-Language Support

```python
class MultiLanguageSearch:
    """Language-aware code search."""
    
    def __init__(self, search: SearchManager):
        self.search = search
        self.language_keywords = {
            "python": ["def", "class", "import", "self"],
            "javascript": ["function", "const", "let", "var"],
            "java": ["public", "private", "class", "interface"]
        }
    
    async def search_language(
        self,
        query: str,
        language: str
    ) -> list[SearchResult]:
        """Search within specific language files."""
        
        # Add language hints to query
        enhanced_query = query
        if language in self.language_keywords:
            hints = " ".join(self.language_keywords[language][:2])
            enhanced_query = f"{query} {hints}"
        
        # Search and filter by language
        results = await self.search.search(enhanced_query)
        return [r for r in results if r.language == language]
```

### Search Query Enhancement

```python
class QueryEnhancer:
    """Enhance search queries for better results."""
    
    def __init__(self):
        self.synonyms = {
            "auth": ["authentication", "authorization", "login"],
            "db": ["database", "sql", "query"],
            "api": ["endpoint", "route", "REST"]
        }
    
    def enhance_query(self, query: str) -> str:
        """Add synonyms and related terms."""
        words = query.lower().split()
        enhanced = []
        
        for word in words:
            enhanced.append(word)
            if word in self.synonyms:
                enhanced.extend(self.synonyms[word][:1])
        
        return " ".join(enhanced)

# Use enhanced queries
enhancer = QueryEnhancer()
enhanced = enhancer.enhance_query("auth middleware")
results = await search.search(enhanced)
```

## Performance Optimization

### Batch Indexing

```python
async def batch_index(search: SearchManager, files: list[str], batch_size: int = 50):
    """Index files in batches for better performance."""
    
    for i in range(0, len(files), batch_size):
        batch = files[i:i + batch_size]
        
        # Index batch concurrently
        tasks = [search.index_file(f) for f in batch]
        await asyncio.gather(*tasks)
        
        print(f"Indexed batch {i//batch_size + 1}/{len(files)//batch_size + 1}")
```

### Caching

```python
from functools import lru_cache
import hashlib

class CachedSearch:
    """Search with result caching."""
    
    def __init__(self, search: SearchManager):
        self.search = search
        self._cache = {}
    
    async def search(self, query: str, **kwargs) -> list[SearchResult]:
        """Search with caching."""
        # Create cache key
        cache_key = hashlib.md5(
            f"{query}{kwargs}".encode()
        ).hexdigest()
        
        # Check cache
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # Perform search
        results = await self.search.search(query, **kwargs)
        
        # Cache results
        self._cache[cache_key] = results
        
        return results
    
    def clear_cache(self):
        """Clear the cache."""
        self._cache.clear()
```

## Troubleshooting

### Common Issues

1. **Index not updating**
   ```python
   # Force re-index
   await search.index_directory(path, force=True)
   ```

2. **Out of memory during indexing**
   ```python
   # Reduce chunk size
   search = SearchManager({
       "search": {"chunk_size": 200}
   })
   ```

3. **Slow search performance**
   ```python
   # Optimize index
   search.optimize_index()
   ```

## See Also

- [Integration Guide](../integration-guide.md) - Using search with other modules
- [Example: Code Analyzer](../../tests/examples/code_analyzer/) - Search in practice
- [Search Configuration](../reference/search-config.md) - Detailed configuration options