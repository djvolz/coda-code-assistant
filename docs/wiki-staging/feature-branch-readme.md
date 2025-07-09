# Tree-Sitter Intelligence Feature Branch

## Overview

This feature branch (`feature/tree-sitter`) adds comprehensive code intelligence capabilities to Coda using tree-sitter for parsing and analysis. It enables AI-powered code understanding, navigation, and analysis across 30+ programming languages.

## What's New

### 🎯 Core Features

1. **Code Analysis**: Extract definitions, imports, and references from source files
2. **Multi-Language Support**: 30+ languages including Python, JavaScript, Java, Kotlin, PHP, and more
3. **Dependency Graphs**: Visualize and analyze code dependencies with cycle detection
4. **Hybrid Tools**: Both native (fast) and MCP (comprehensive) tool implementations
5. **Smart Navigation**: Find definitions, analyze files, and understand code structure

### 🛠 New Commands

```bash
# Intelligence commands
coda /intel analyze <file>     # Analyze a file's structure
coda /intel find <name>        # Find definitions by name
coda /intel deps <file>        # Show file dependencies
coda /intel scan <dir>         # Scan directory for code
coda /intel graph <dir>        # Build dependency graph
coda /intel map [path]         # Map repository structure
coda /intel stats              # Show language statistics
```

### 🤖 AI Integration

The AI assistant now understands code-related queries:
- "Find the definition of MyClass"
- "What does this file import?"
- "Show me all functions in this directory"
- "Analyze the structure of main.py"

## Installation

1. **Checkout the branch**:
   ```bash
   git checkout feature/tree-sitter
   ```

2. **Install dependencies** (if not already installed):
   ```bash
   pip install -r requirements.txt
   ```

3. **Verify installation**:
   ```bash
   coda /intel help
   ```

## Quick Start

### In Chat
```bash
coda chat

# Then ask:
> "Find the UserService class"
> "What's in the utils.py file?"
> "Show me code statistics for src/"
```

### Direct Commands
```bash
# Find a definition
coda /intel find TreeSitterAnalyzer

# Analyze a file
coda /intel analyze coda/intelligence/tree_sitter_analyzer.py

# Scan a directory
coda /intel scan coda/intelligence/

# Build dependency graph
coda /intel graph src/ --output=dependencies.json
```

### In Code
```python
# Native tools (simple & fast)
from coda.agents.intelligence_tools import find_definition
print(find_definition("MyClass"))

# MCP tools (comprehensive)
from coda.tools.intelligence_tools import AnalyzeFileTool
tool = AnalyzeFileTool()
result = await tool.execute({"file_path": "main.py"})
```

## Architecture

```
coda/
├── intelligence/              # Core intelligence module
│   ├── tree_sitter_analyzer.py
│   ├── repo_map.py
│   ├── dependency_graph.py
│   └── queries/              # Language query files
│       ├── python-tags.scm
│       ├── javascript-tags.scm
│       └── ... (30+ languages)
├── tools/
│   └── intelligence_tools.py  # MCP tool implementations
└── agents/
    └── intelligence_tools.py  # Native tool implementations
```

## Testing

Run the test suite:
```bash
# All intelligence tests
pytest tests/intelligence/

# Specific test files
pytest tests/intelligence/test_tree_sitter_analyzer.py
pytest tests/tools/test_intelligence_tools.py
pytest tests/agents/test_intelligence_tools.py
```

## Documentation

- [Design Document](./tree-sitter-intelligence-design.md) - Architecture and implementation details
- [Usage Guide](./tree-sitter-intelligence-usage.md) - Comprehensive usage examples
- [API Reference](../intelligence/README.md) - Module API documentation

## Contributing

### Adding a New Language

1. Create a query file: `coda/intelligence/queries/[language]-tags.scm`
2. Add extension mapping in `tree_sitter_query_analyzer.py`
3. Write tests in `tests/intelligence/test_[language]_support.py`
4. Update documentation

### Query File Format

```scheme
;; Class definitions
(class_declaration
  name: (identifier) @name.definition.class) @definition.class

;; Function definitions
(function_declaration
  name: (identifier) @name.definition.function) @definition.function
```

## Known Limitations

1. **PL/SQL**: Limited support due to tree-sitter grammar constraints
2. **Large Files**: Performance may degrade on very large files (>10k lines)
3. **Cross-File Resolution**: Currently analyzes files independently

## Troubleshooting

### "Language not supported"
- Check if file extension is mapped in `_get_extension_map()`
- Ensure corresponding query file exists
- May fall back to regex-based parsing

### Performance Issues
- Use native tools for quick queries
- Limit directory scanning depth with `recursive=False`
- Filter by file patterns when scanning

### Import Detection Issues
- Verify query file captures import patterns correctly
- Check for language-specific import syntax
- Some languages may have limited import detection

## Future Enhancements

- [ ] Incremental parsing for better performance
- [ ] Cross-file symbol resolution
- [ ] Type information extraction
- [ ] Semantic code search
- [ ] IDE integration via Language Server Protocol

## Feedback

Please report issues or suggestions:
- Create an issue with `[tree-sitter]` prefix
- Include language and code sample for parsing issues
- Suggest new languages or features

## License

Same as Coda project - see main LICENSE file.