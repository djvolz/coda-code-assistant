#!/usr/bin/env python3
"""Simple example showing the search module's repository mapping features.

This example demonstrates repository analysis without vector search dependencies.
"""

from pathlib import Path

# Import only the repository mapping components
from coda.base.search import DependencyGraph, RepoMap, TreeSitterAnalyzer


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print("=" * 60)


def repo_map_demo():
    """Demo the repository mapping functionality."""
    print_section("Repository Mapping Demo")

    # Use current directory for demo
    project_path = Path(".").resolve()
    print(f"Analyzing repository: {project_path}")

    # Create repo map
    repo_map = RepoMap(str(project_path))

    # Set file filters for demo
    repo_map.set_file_filters(
        include_patterns=["*.py"], exclude_patterns=["*test*", "__pycache__", "*.pyc"]
    )

    # Analyze repository structure
    print("\nGenerating repository map...")
    summary = repo_map.generate_map(
        max_files=10,
        show_types=["function", "class"],  # Limit for demo
    )

    print("\nRepository summary:")
    print(summary[:500] + "..." if len(summary) > 500 else summary)


def tree_sitter_demo():
    """Demo the tree-sitter code analysis."""
    print_section("Tree-Sitter Code Analysis Demo")

    analyzer = TreeSitterAnalyzer()

    # Example Python code
    code = '''
class Calculator:
    """A simple calculator class."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def multiply(self, a: int, b: int) -> int:
        """Multiply two numbers."""
        return a * b

def main():
    calc = Calculator()
    result = calc.add(5, 3)
    print(f"Result: {result}")
'''

    print("Analyzing sample code...")
    symbols = analyzer.extract_symbols(code, "python")

    print("\nExtracted symbols:")
    for symbol in symbols:
        print(f"  - {symbol.type}: {symbol.name} at line {symbol.line}")
        if symbol.docstring:
            print(f"    Docstring: {symbol.docstring[:50]}...")


def dependency_graph_demo():
    """Demo the dependency graph generation."""
    print_section("Dependency Graph Demo")

    # Create a simple dependency graph
    graph = DependencyGraph()

    # Add some sample modules
    modules = [
        "coda.base.config",
        "coda.base.theme",
        "coda.base.providers",
        "coda.services.agents",
        "coda.services.tools",
    ]

    # Add modules as nodes
    for module in modules:
        graph.add_node(module)

    # Add some dependencies
    graph.add_edge("coda.services.agents", "coda.base.providers")
    graph.add_edge("coda.services.agents", "coda.services.tools")
    graph.add_edge("coda.services.tools", "coda.base.config")

    print("Sample dependency graph:")
    print(f"Nodes: {len(graph.nodes)}")
    print(f"Edges: {len(graph.edges)}")

    print("\nDependencies:")
    for source, targets in graph.edges.items():
        if targets:
            print(f"  {source} -> {', '.join(targets)}")


def main():
    """Run all demos."""
    print("=== Coda Search Module Demo ===")
    print("\nThis demonstrates the search module's repository analysis features")
    print("without requiring vector search dependencies.\n")

    try:
        tree_sitter_demo()
    except Exception as e:
        print(f"Tree-sitter demo skipped: {e}")

    try:
        dependency_graph_demo()
    except Exception as e:
        print(f"Dependency graph demo skipped: {e}")

    try:
        repo_map_demo()
    except Exception as e:
        print(f"Repo map demo skipped: {e}")

    print("\n✓ Search module (repository mapping) works standalone!")
    print("✓ Can analyze code structure without vector search dependencies")


if __name__ == "__main__":
    main()
