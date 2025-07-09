# Using Coda Embeddings as a Library

## Current State: Not Fully Self-Contained

The current implementation has dependencies on Coda's internal configuration and constants, making it difficult to use as a standalone library.

### Issues:
1. `OCIEmbeddingProvider` requires `CodaConfig` object
2. Imports Coda-specific constants (`MODEL_CACHE_DURATION`, `get_cache_dir`)
3. Configuration is tightly coupled to Coda's structure

## Recommended Refactoring

To make the embedding modules truly self-contained:

### 1. Decouple Configuration

Replace Coda-specific config with standard parameters:

```python
# Current (coupled)
provider = OCIEmbeddingProvider(config=CodaConfig())

# Recommended (decoupled)
provider = OCIEmbeddingProvider(
    compartment_id="ocid1.compartment...",
    oci_config_file="~/.oci/config",
    cache_duration_hours=24
)
```

### 2. Make Constants Configurable

```python
# Current (hardcoded)
from ..constants import MODEL_CACHE_DURATION

# Recommended (configurable)
def __init__(self, cache_duration_hours: int = 24):
    self.cache_duration = timedelta(hours=cache_duration_hours)
```

### 3. Configurable Storage Paths

```python
# Current (Coda-specific)
self.index_dir = get_cache_dir() / "semantic_search"

# Recommended (configurable)
def __init__(self, index_dir: Optional[Path] = None):
    self.index_dir = index_dir or Path.home() / ".cache" / "embeddings"
```

## Example: Self-Contained Usage

Here's how external projects SHOULD be able to use the embedding library:

```python
# my_project.py
from coda.embeddings import OCIEmbeddingProvider
from coda.vector_stores import FAISSVectorStore
from coda.semantic_search import SemanticSearchManager

# Direct initialization without Coda config
embedding_provider = OCIEmbeddingProvider(
    compartment_id="ocid1.compartment.oc1...",
    model_id="multilingual-e5",
    oci_config_file="~/.oci/config"
)

# Create vector store
vector_store = FAISSVectorStore(
    dimension=768,
    index_type="hnsw",
    metric="cosine"
)

# Create search manager with custom paths
manager = SemanticSearchManager(
    embedding_provider=embedding_provider,
    vector_store=vector_store,
    index_dir="/my/project/indexes"
)

# Use it
async def main():
    # Index documents
    docs = ["Document 1", "Document 2", "Document 3"]
    await manager.index_content(docs)
    
    # Search
    results = await manager.search("find similar documents")
    for result in results:
        print(f"{result.text} (score: {result.score})")
```

## Minimal Dependencies

A self-contained embedding library should only require:
- `numpy` - for vector operations
- `oci` - only if using OCI provider
- `faiss-cpu` - only if using FAISS store
- No Coda-specific imports

## Proposed Module Structure

```
coda/
├── embeddings/
│   ├── __init__.py
│   ├── base.py          # ✓ Already self-contained
│   ├── oci.py           # ✗ Needs refactoring
│   ├── ollama.py        # Future: self-contained
│   └── sentence_transformers.py  # Future: self-contained
├── vector_stores/
│   ├── __init__.py
│   ├── base.py          # ✓ Already self-contained
│   ├── faiss_store.py   # ✓ Already self-contained
│   └── oracle_vector.py # Future: self-contained
└── semantic_search.py    # ✗ Needs refactoring
```

## Benefits of Refactoring

1. **Reusability**: Other projects can use Coda's embedding infrastructure
2. **Testing**: Easier to test in isolation
3. **Maintenance**: Clear separation of concerns
4. **Documentation**: Simpler API to document
5. **Community**: Can be published as a separate package if desired

## Migration Path

1. Create new "standalone" versions alongside existing code
2. Update Coda to use the standalone versions with Coda-specific wrappers
3. Deprecate the tightly-coupled versions
4. Eventually move to a separate `coda-embeddings` package