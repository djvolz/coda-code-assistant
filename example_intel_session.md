# Example Coda Intelligence Session

Start Coda:
```bash
uv run coda
```

Then try these commands:

```
# Map the current repository
/intel map .

# See what was found
/intel stats

# Analyze a specific file
/intel analyze coda/intelligence/tree_sitter_query_analyzer.py

# Find a class
/intel find TreeSitterQueryAnalyzer

# Scan for Python files
/intel scan coda/intelligence/

# Check dependencies
/intel deps coda/intelligence/cli.py

# Generate a dependency graph (exports to JSON)
/intel graph coda/intelligence/ --export graph.json
```

The intelligence features use tree-sitter for accurate parsing across many languages, providing better code understanding than regex-based approaches.