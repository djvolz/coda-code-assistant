#!/usr/bin/env python3
"""
Demo script to showcase tree-sitter intelligence features in Coda.

Run this after starting Coda with: uv run coda
"""

print("""
=== Coda Tree-Sitter Intelligence Demo ===

Start Coda with: uv run coda

Then try these commands to explore the new tree-sitter intelligence features:

1. Map the current repository structure:
   /intel map .

2. View repository statistics:
   /intel stats

3. Analyze a specific file (shows definitions, imports, etc.):
   /intel analyze coda/intelligence/tree_sitter_query_analyzer.py

4. Find a specific class/function definition:
   /intel find TreeSitterQueryAnalyzer
   /intel find analyze_file

5. Scan a directory with progress indicator:
   /intel scan coda/intelligence/
   
   Note: The scan now shows a progress bar with percentage, file count, 
   and current filename being analyzed!

6. Check file dependencies:
   /intel deps coda/intelligence/cli.py

7. Generate a dependency graph:
   /intel graph coda/intelligence/ --format=json --output=deps.json
   /intel graph coda/intelligence/ --format=dot --output=deps.dot

8. Get help on all intelligence commands:
   /intel help

The tree-sitter integration provides accurate code parsing for:
- Python, JavaScript, TypeScript, Rust, Go, Java, and many more languages
- Extracts classes, functions, methods, variables, imports
- Works with the actual AST instead of regex patterns
- Provides better accuracy for code understanding

Try it out on your own projects!
""")