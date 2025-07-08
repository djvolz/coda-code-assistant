# Tree-Sitter Intelligence Usage Guide

This guide explains how to use the tree-sitter intelligence features in Coda for code analysis, navigation, and understanding your codebase.

## Quick Start

### In Chat

The AI assistant automatically uses intelligence tools when you ask about code:

```
> "Find the definition of MyClass"
> "What's in the utils.py file?"
> "Show me all the functions in this directory"
> "What does this file import?"
```

### Direct Commands

Use the `/intel` command for direct access:

```bash
# Find definitions
coda /intel find MyFunction

# Analyze a file
coda /intel analyze src/main.py

# Show dependencies
coda /intel deps src/utils.py

# Scan directory
coda /intel scan src/

# Generate dependency graph
coda /intel graph src/ --output=deps.json
```

## Available Tools

### Native Tools (Quick & Simple)

These tools provide instant results for common queries:

#### 1. **find_definition**
Find code definitions by name.

**Example prompts:**
- "Find the TreeSitterAnalyzer class"
- "Where is the process_data function defined?"
- "Find all methods named 'save'"

**Direct usage:**
```python
from coda.agents.intelligence_tools import find_definition
result = find_definition("MyClass", kind="class")
```

#### 2. **analyze_code**
Quick analysis of file structure.

**Example prompts:**
- "Analyze the main.py file"
- "What's in this file?"
- "Show me the structure of utils.js"

**Direct usage:**
```python
from coda.agents.intelligence_tools import analyze_code
result = analyze_code("src/main.py")
```

#### 3. **get_dependencies**
List file imports and dependencies.

**Example prompts:**
- "What does this file import?"
- "Show dependencies for main.py"
- "What external libraries does this use?"

**Direct usage:**
```python
from coda.agents.intelligence_tools import get_dependencies
result = get_dependencies("src/utils.py")
```

#### 4. **code_stats**
Directory-level statistics.

**Example prompts:**
- "Show code statistics for this project"
- "How many Python files are in src/?"
- "Give me a breakdown of code by language"

**Direct usage:**
```python
from coda.agents.intelligence_tools import code_stats
result = code_stats("src/")
```

#### 5. **find_pattern**
Search for code patterns.

**Example prompts:**
- "Find all classes in the codebase"
- "Show me all functions in Python files"
- "Find imports from numpy"

**Direct usage:**
```python
from coda.agents.intelligence_tools import find_pattern
result = find_pattern("classes", file_type="py")
```

### MCP Tools (Comprehensive Analysis)

These tools provide detailed analysis with rich metadata:

#### 1. **analyze_code_file**
Full file analysis with structured output.

```python
# Async usage
import asyncio
from coda.tools.intelligence_tools import AnalyzeFileTool

tool = AnalyzeFileTool()
result = await tool.execute({
    "file_path": "src/main.py",
    "include_references": True
})
```

#### 2. **scan_code_directory**
Comprehensive directory scanning.

```python
tool = ScanDirectoryTool()
result = await tool.execute({
    "directory": "src/",
    "recursive": True
})
```

#### 3. **build_dependency_graph**
Create dependency graphs with cycle detection.

```python
tool = BuildDependencyGraphTool()
result = await tool.execute({
    "directory": "src/",
    "include_cycles": True
})
```

## Supported Languages

Currently supports 30+ languages including:
- Python, JavaScript, TypeScript
- Java, Kotlin, Swift
- C, C++, Rust, Go
- Ruby, PHP, C#
- And many more...

## Common Use Cases

### 1. Code Navigation
```
"Where is the UserService class defined?"
"Find all references to the save method"
"Show me all API endpoints in this project"
```

### 2. Dependency Analysis
```
"What files import the utils module?"
"Show me the dependency graph for src/"
"Find circular dependencies in my code"
```

### 3. Code Understanding
```
"What does the auth.py file do?"
"Summarize the main components in this directory"
"How many classes vs functions are in this project?"
```

### 4. Refactoring Support
```
"Find all occurrences of the old_function"
"What files would be affected if I change this class?"
"Show me all TODO comments in the codebase"
```

## Advanced Features

### Filtering by Kind

Many tools support filtering by definition kind:
- `function`, `method`
- `class`, `interface`
- `variable`, `constant`
- `type`, `enum`, `struct`

Example:
```python
find_definition("process", kind="function")
```

### Language-Specific Analysis

The tools automatically detect language and apply appropriate parsing:
```python
analyze_code("app.js")   # Uses JavaScript parser
analyze_code("main.py")  # Uses Python parser
analyze_code("App.java") # Uses Java parser
```

### Output Formats

MCP tools support multiple output formats:
```bash
# JSON output
coda /intel graph src/ --format=json --output=deps.json

# DOT format for visualization
coda /intel graph src/ --format=dot --output=deps.dot
dot -Tpng deps.dot -o deps.png
```

## Tips and Best Practices

1. **Start with Native Tools**: For quick lookups and simple queries
2. **Use MCP Tools for Deep Analysis**: When you need comprehensive data
3. **Combine with Other Commands**: Intelligence tools work great with file operations
4. **Cache Results**: MCP tools cache parser results for performance
5. **Use Filters**: Narrow down results with kind and file type filters

## Troubleshooting

### Common Issues

1. **"No definitions found"**
   - Check file path is correct
   - Ensure file has supported extension
   - Try without kind filter

2. **"Language not supported"**
   - Check supported languages list
   - File may need proper extension
   - Fallback to regex may be active

3. **Performance Issues**
   - Use non-recursive scan for large directories
   - Filter by file patterns
   - Consider using native tools for quick queries

### Debug Mode

Enable debug logging:
```python
import logging
logging.getLogger("coda.intelligence").setLevel(logging.DEBUG)
```

## Integration Examples

### With File Operations
```
"Find the Config class and show me its implementation"
"Update all imports of old_module to new_module"
```

### With Git Operations
```
"What functions were added in the last commit?"
"Show me all class definitions in changed files"
```

### With Documentation
```
"Generate a summary of all public APIs in this module"
"Find all functions missing docstrings"
```

## Conclusion

The tree-sitter intelligence features provide powerful code analysis capabilities that integrate seamlessly with Coda's AI assistant. Whether you need quick lookups or comprehensive analysis, these tools help you understand and navigate your codebase effectively.