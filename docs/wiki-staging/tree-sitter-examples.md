# Tree-Sitter Intelligence Examples

This document showcases real-world examples of using the tree-sitter intelligence features in Coda.

## Example Sessions

### 1. Finding a Class Definition

```bash
$ coda chat

> Where is the TreeSitterAnalyzer class defined?

Found 1 definition(s) for 'TreeSitterAnalyzer':
  coda/intelligence/tree_sitter_analyzer.py:7 - class

> Show me what's in that file

=== Analysis of tree_sitter_analyzer.py (python) ===

Definitions:
  classes: TreeSitterAnalyzer
  
Imports (6):
  - .tree_sitter_query_analyzer
  - CodeElement
  - DefinitionKind
  - FileAnalysis
  - TREE_SITTER_AVAILABLE
  - TreeSitterQueryAnalyzer

Note: TreeSitterAnalyzer is an alias for TreeSitterQueryAnalyzer
```

### 2. Analyzing Dependencies

```bash
> What does the intelligence module depend on?

$ coda /intel deps coda/intelligence/__init__.py

Dependencies for __init__.py (python):
  - .dependency_graph
  - .repo_map
  - .tree_sitter_analyzer
  - DependencyGraph
  - RepoMap
  - TreeSitterAnalyzer
```

### 3. Code Statistics

```bash
> Show me statistics for the intelligence module

$ coda /intel stats coda/intelligence/

Code statistics for intelligence:
Total files: 5
Total definitions: 47

By language:
  python: 5 files, 47 definitions (8 classes, 35 functions)
```

### 4. Finding Patterns

```bash
> Find all classes that handle tree-sitter operations

$ coda chat
> Find classes with "tree" in their name

Found 3 match(es) for 'tree':
  coda/intelligence/tree_sitter_analyzer.py:7 - class: TreeSitterAnalyzer
  coda/intelligence/tree_sitter_query_analyzer.py:105 - class: TreeSitterQueryAnalyzer
  tests/intelligence/test_tree_sitter.py:15 - class: TestTreeSitter
```

### 5. Building a Dependency Graph

```bash
$ coda /intel graph coda/intelligence/ --output=intel-deps.json

Dependency Graph for coda/intelligence/
Nodes: 7
Edges: 12
Max depth: 3

Most depended upon files:
  tree_sitter_query_analyzer.py: 4 dependents
  __init__.py: 2 dependents

Files with most dependencies:
  cli.py: 3 dependencies
  dependency_graph.py: 2 dependencies

Graph exported to intel-deps.json (JSON)
```

### 6. Multi-Language Analysis

```bash
> Analyze files in different languages

$ coda chat
> Analyze the javascript query file

=== Analysis of javascript-tags.scm (scheme) ===

Definitions:
  No standard definitions (query file)

This is a tree-sitter query file that defines patterns for:
- Class declarations
- Function declarations  
- Import statements
- Method definitions
- JSDoc comments
```

### 7. Hybrid Tool Usage

```python
# In a Python script

# Quick lookup with native tool
from coda.agents.intelligence_tools import find_definition
print(find_definition("DependencyGraph"))
# Output: Found 1 definition(s) for 'DependencyGraph':
#   coda/intelligence/dependency_graph.py:15 - class

# Comprehensive analysis with MCP tool
import asyncio
from coda.tools.intelligence_tools import AnalyzeFileTool

async def analyze():
    tool = AnalyzeFileTool()
    result = await tool.execute({
        "file_path": "coda/intelligence/repo_map.py",
        "include_references": True
    })
    return result

result = asyncio.run(analyze())
# Returns structured data with all definitions, imports, and references
```

### 8. Refactoring Support

```bash
> I want to rename TreeSitterAnalyzer to CodeAnalyzer, what files would be affected?

$ coda chat
> Find all references to TreeSitterAnalyzer

Searching for 'TreeSitterAnalyzer'...

Found in:
  coda/intelligence/__init__.py:3 - import
  coda/intelligence/tree_sitter_analyzer.py:7 - definition
  coda/intelligence/cli.py:10 - import
  coda/intelligence/dependency_graph.py:5 - import
  coda/tools/intelligence_tools.py:9 - import
  tests/intelligence/test_tree_sitter_analyzer.py:5 - import
  ... and 12 more locations

Total: 18 files would need updates
```

### 9. Understanding New Codebases

```bash
> I just cloned a new project. Help me understand its structure.

$ coda /intel map .

Repository: /Users/dev/new-project
Total files: 156
Total size: 2.1 MB

Top languages:
  python: 89 files (57.1%)
  javascript: 34 files (21.8%)
  yaml: 12 files (7.7%)
  json: 8 files (5.1%)
  markdown: 13 files (8.3%)

$ coda /intel find main

Found 3 definition(s) for 'main':
  src/main.py:45 - function
  src/cli.py:120 - function  
  tests/test_main.py:8 - function
```

### 10. Language-Specific Queries

```bash
> Show me all React components in this project

$ coda chat
> Find all classes that extend Component or use hooks

Searching JavaScript files for React patterns...

Found components:
  src/components/UserList.js:5 - class: UserList
  src/components/Header.js:3 - function: Header (with useState)
  src/components/Dashboard.js:8 - class: Dashboard
  src/hooks/useAuth.js:3 - function: useAuth
  src/pages/Home.js:4 - function: Home (with useEffect)
```

## Advanced Patterns

### Combining with Git

```bash
# Analyze only changed files
$ git diff --name-only | xargs -I {} coda /intel analyze {}
```

### Batch Analysis

```python
# Analyze all Python files in a directory
from pathlib import Path
from coda.agents.intelligence_tools import analyze_code

for py_file in Path("src").rglob("*.py"):
    print(f"\n{py_file}:")
    print(analyze_code(str(py_file)))
```

### Custom Reports

```python
# Generate a module summary
from coda.intelligence import TreeSitterAnalyzer

analyzer = TreeSitterAnalyzer()
stats = {"total_classes": 0, "total_functions": 0}

for analysis in analyzer.analyze_directory("src").values():
    for defn in analysis.definitions:
        if defn.kind.value == "class":
            stats["total_classes"] += 1
        elif defn.kind.value in ["function", "method"]:
            stats["total_functions"] += 1

print(f"Module has {stats['total_classes']} classes and {stats['total_functions']} functions")
```

## Tips for Effective Use

1. **Start Broad, Then Narrow**: Use `code_stats` first, then drill down with specific tools
2. **Combine Tools**: Use `find_definition` + `analyze_code` for complete understanding
3. **Filter by Language**: Use file type filters when searching large codebases
4. **Watch for Patterns**: The AI learns your codebase patterns over time
5. **Export for Visualization**: Use graph exports with tools like Graphviz

## Common Workflows

### Code Review Preparation
```bash
# Get overview of changes
coda /intel map .

# Find modified functions
coda /intel find modified_function

# Check dependencies
coda /intel deps src/changed_file.py
```

### Documentation Generation
```bash
# Find all public APIs
coda chat
> Find all public functions and classes

# Analyze module structure  
coda /intel analyze src/api/__init__.py
```

### Debugging Support
```bash
# Trace function calls
coda chat
> Show me all places where process_data is called

# Understand data flow
coda /intel graph src/ --output=dataflow.dot
```

These examples demonstrate the power and flexibility of the tree-sitter intelligence features. Experiment with different commands and combinations to find what works best for your workflow!