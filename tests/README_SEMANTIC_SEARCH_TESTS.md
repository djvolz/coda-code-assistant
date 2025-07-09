# Semantic Search Test Coverage

This document describes the comprehensive test suite for the semantic search functionality in Phase 8.

## Test Organization

### Unit Tests

#### 1. Chunking Module (`tests/test_chunking.py`)
- **Chunk dataclass**: Creation, metadata handling
- **TextChunker**: Default/custom parameters, small/large text handling, overlap calculation
- **CodeChunker**: Python and JavaScript code parsing, function/class detection, language fallback
- **Factory function**: File type detection, parameter passing
- **Edge cases**: Unicode, empty text, long lines, invalid configurations

#### 2. Embedding Providers

##### Mock Provider (`tests/embeddings/test_mock.py`)
- Basic functionality covered by existing tests

##### Sentence Transformers (`tests/embeddings/test_sentence_transformers.py`)
- Model initialization and configuration
- Single text and batch embedding
- Model info and listing
- Lazy loading and error handling
- Normalization settings
- Device selection

##### Ollama Provider (`tests/embeddings/test_ollama.py`)
- HTTP client management
- Model availability checking
- Dimension detection and caching
- Error handling (404, connection errors)
- Batch processing with semaphore
- Keep-alive settings

##### OCI Provider (`tests/embeddings/test_oci_embeddings.py`)
- Existing tests for OCI integration

##### Factory (`tests/embeddings/test_factory.py`)
- Provider creation for all types
- Alias resolution
- Default model selection
- Provider info retrieval
- Error handling

#### 3. Vector Stores

##### FAISS Store (`tests/vector_stores/test_faiss_store.py`)
- Existing tests for FAISS operations

#### 4. Search Display (`tests/cli/test_search_display.py`)
- **SearchHighlighter**: Query term highlighting
- **SearchResultDisplay**: Result formatting, score coloring, content preview
- **IndexingProgress**: Progress tracking with/without total
- **Stats display**: Formatting search statistics

### Integration Tests

#### 1. Semantic Search Integration (`tests/integration/test_semantic_search_integration.py`)
- End-to-end indexing and search workflows
- File indexing with chunking
- Metadata filtering
- Session message indexing
- Index persistence (save/load)
- Large batch processing
- Unicode content handling
- Provider switching
- Chunking context preservation

#### 2. CLI Integration (`tests/integration/test_semantic_search_cli.py`)
- Existing tests for CLI commands

## Running Tests

### Run All Semantic Search Tests
```bash
./scripts/run_semantic_search_tests.sh
```

### Run Specific Test Categories

#### Unit Tests Only
```bash
uv run python -m pytest tests/test_chunking.py tests/embeddings/ tests/cli/test_search_display.py -v
```

#### Integration Tests Only
```bash
uv run python -m pytest tests/integration/test_semantic_search*.py -v
```

#### With Coverage Report
```bash
uv run python -m pytest tests/ -v --cov=coda.chunking --cov=coda.embeddings --cov=coda.vector_stores --cov=coda.semantic_search --cov-report=html
```

### Test Markers

- `@pytest.mark.unit` - Fast unit tests with no external dependencies
- `@pytest.mark.integration` - Integration tests requiring setup
- `@pytest.mark.asyncio` - Async tests

## Coverage Goals

Target coverage: **85%+** for core modules:
- `coda.chunking` - Text chunking logic
- `coda.embeddings` - All embedding providers
- `coda.vector_stores` - Vector storage implementations
- `coda.semantic_search` - Core search functionality
- `coda.cli.search_display` - UI components

## CI Integration

Tests are automatically run on:
- Every push to main, develop, and feature branches
- All pull requests
- Python versions: 3.11, 3.12, 3.13

Integration tests run only on:
- Pushes to main
- Commits with `[integration]` tag

## Future Test Additions

1. **Performance Tests**
   - Large file indexing benchmarks
   - Search response time tests
   - Memory usage profiling

2. **Stress Tests**
   - Concurrent indexing operations
   - Very large corpus handling
   - Resource exhaustion scenarios

3. **Security Tests**
   - Input validation
   - Path traversal prevention
   - Injection attack prevention