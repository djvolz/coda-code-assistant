# Tree-Sitter Intelligence Design Document

## Overview

The Tree-Sitter Intelligence feature provides comprehensive code analysis capabilities for Coda, enabling users to understand code structure, dependencies, and relationships across their codebase. This document outlines the architecture, design decisions, and implementation details.

## Architecture

### Core Components

```
coda/intelligence/
├── __init__.py                    # Public API exports
├── tree_sitter_analyzer.py        # Main analyzer interface
├── tree_sitter_query_analyzer.py  # Query-based implementation
├── repo_map.py                    # Repository structure mapping
├── dependency_graph.py            # Dependency analysis
├── cli.py                         # CLI command interface
└── queries/                       # Language-specific query files
    ├── python-tags.scm
    ├── javascript-tags.scm
    ├── kotlin-tags.scm
    └── ... (30+ languages)
```

### Design Principles

1. **Language Agnostic**: Uses tree-sitter grammars to support 30+ languages uniformly
2. **Query-Based Extraction**: SCM query files define what to extract for each language
3. **Fallback Support**: Regex-based fallback for when tree-sitter isn't available
4. **Incremental Analysis**: Can analyze single files or entire directories
5. **Extensible**: Easy to add new languages by adding query files

## Key Features

### 1. Code Element Extraction

The system extracts various code elements:
- **Definitions**: Classes, functions, methods, variables, constants
- **References**: Function calls, class instantiations, property access
- **Imports**: Import statements and dependencies
- **Documentation**: Docstrings and comments

### 2. Repository Mapping

`RepoMap` provides repository-wide analysis:
- File discovery and categorization
- Language statistics
- Git integration for repository metadata
- Aggregate metrics (size, lines, file counts)

### 3. Dependency Analysis

`DependencyGraph` builds and analyzes dependency relationships:
- Import resolution
- Circular dependency detection
- Dependency depth calculation
- Most depended upon files

### 4. Tool Integration

#### Hybrid Tool Approach

We implement two types of tools:

**Native Tools** (`@tool` decorator):
- Simple, synchronous functions
- Instant execution
- String-based output
- Perfect for interactive use

**MCP Tools** (class-based):
- Comprehensive analysis
- Rich metadata
- Async execution
- Structured results

This hybrid approach provides both speed and depth as needed.

## Implementation Details

### Tree-Sitter Integration

```python
# Query-based extraction
query = language.query(query_scm)
captures = query.captures(tree.root_node)

# Process captures
for node, tag in captures:
    if tag.startswith("definition."):
        # Extract definition
    elif tag == "import":
        # Extract import
```

### Query File Structure

Example Python query:
```scheme
;; Class definitions
(class_definition
  name: (identifier) @name.definition.class) @definition.class

;; Function definitions  
(function_definition
  name: (identifier) @name.definition.function) @definition.function
```

### Error Handling

1. **Graceful Degradation**: Falls back to regex when tree-sitter fails
2. **Language Detection**: Multiple methods (extension, content-based)
3. **Parser Caching**: Reuses parsers for performance
4. **Query Validation**: Validates SCM queries on load

## Performance Considerations

1. **Parser Caching**: Each language parser initialized once
2. **Query Caching**: Compiled queries cached per language
3. **Lazy Loading**: Only loads necessary language support
4. **Progress Indicators**: For long-running operations

## Extensibility

### Adding New Languages

1. Create `queries/[language]-tags.scm` file
2. Add extension mappings in `_get_extension_map()`
3. Write test coverage
4. Document supported constructs

### Custom Analysis

The modular design allows:
- Custom query patterns
- Additional extraction rules
- Language-specific handling
- Plugin-based extensions

## Testing Strategy

1. **Unit Tests**: Each component tested independently
2. **Integration Tests**: Full pipeline testing
3. **Language Tests**: Per-language test coverage
4. **Query Validation**: Automated query syntax checking

## Future Enhancements

1. **Incremental Parsing**: Only reparse changed portions
2. **Cross-File Resolution**: Resolve symbols across files
3. **Type Information**: Extract and track type annotations
4. **Semantic Search**: Search by meaning not just text
5. **IDE Integration**: Language server protocol support

## Security Considerations

1. **File Access**: Respects file permissions
2. **Path Validation**: Prevents directory traversal
3. **Resource Limits**: Caps on file sizes and counts
4. **Safe Parsing**: Handles malformed code gracefully

## Conclusion

The Tree-Sitter Intelligence feature provides a robust foundation for code analysis in Coda. The hybrid tool approach, comprehensive language support, and extensible architecture make it suitable for both interactive use and automated analysis workflows.