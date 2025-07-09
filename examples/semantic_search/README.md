# Semantic Search Examples

This directory contains examples demonstrating the semantic search functionality in Coda.

## Examples

### 1. Basic Search (`basic_search.py`)
Demonstrates fundamental semantic search operations:
- Initializing a semantic search manager with OCI embeddings
- Indexing text documents
- Performing semantic searches
- Retrieving index statistics

**Requirements**: OCI configuration and Coda setup

### 2. Code Indexing (`code_indexing.py`)
Shows how to index and search source code:
- Indexing Python source files
- Searching for code patterns semantically
- Finding relevant code snippets

**Requirements**: OCI configuration and Coda setup

### 3. Mock Provider Demo (`mock_provider_demo.py`)
Demonstrates testing without external dependencies:
- Using the mock embedding provider
- Testing search functionality locally
- Index persistence and loading

**Requirements**: None (uses mock provider)

## Running the Examples

1. Install dependencies:
   ```bash
   uv sync --extra embeddings
   ```

2. For OCI-based examples, ensure you have:
   - Coda configuration: `~/.config/coda/config.toml`
   - OCI credentials: `~/.oci/config`

3. Run an example:
   ```bash
   python examples/semantic_search/basic_search.py
   ```

## Configuration

For examples using OCI, you need a Coda configuration file with OCI settings:

```toml
[oci]
compartment_id = "your-compartment-id"
embedding_model_id = "cohere.embed-english-v3.0"
config_file_path = "~/.oci/config"
profile = "DEFAULT"
```

## Using as a Library

These examples demonstrate how to use Coda's semantic search as a library in your own projects:

```python
from coda.semantic_search import SemanticSearchManager
from coda.embeddings import create_standalone_oci_provider

# Create embedding provider
provider = create_standalone_oci_provider(
    compartment_id="your-compartment-id",
    model_id="cohere.embed-english-v3.0"
)

# Create search manager
manager = SemanticSearchManager(embedding_provider=provider)

# Index and search
await manager.index_content(["document 1", "document 2"])
results = await manager.search("query", k=5)
```