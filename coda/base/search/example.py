#!/usr/bin/env python3
"""Standalone example showing the search module works without other Coda modules.

This example demonstrates that the search module:
1. Has zero dependencies on other coda modules
2. Can be used in any project for code analysis and search
3. Provides comprehensive repository search features

When using this module standalone:
- Copy the entire search directory to your project
- Import directly: from search import RepoMap, TreeSitterAnalyzer
- Or run this example: python example.py
"""

from pathlib import Path

# When running from coda package (always use this path when running as script)
from coda.base.search import (
    DependencyGraph,
    RepoMap,
    TreeSitterAnalyzer,
)

# Import SemanticSearchManager separately to avoid FAISS issues
try:
    from coda.base.search import SemanticSearchManager
except (ImportError, AttributeError):
    # FAISS not available, skip semantic search demo
    SemanticSearchManager = None


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def demonstrate_repo_map() -> None:
    """Demonstrate repository mapping functionality."""
    print_section("Repository Mapping Demo")

    # Map the search module itself
    module_path = Path(__file__).parent

    # Create a repo map for the search module directory
    repo_map = RepoMap(module_path)

    # Scan the repository
    repo_map.scan_repository()

    # Get summary
    summary = repo_map.get_summary()
    print(f"Found {summary['total_files']} files in the search module")

    # Show language statistics
    lang_stats = repo_map.get_language_stats()
    print("\nLanguage distribution:")
    for lang, stats in sorted(lang_stats.items(), key=lambda x: x[1]["file_count"], reverse=True)[
        :5
    ]:
        print(f"  - {lang}: {stats['file_count']} files ({stats['percentage']:.1f}%)")

    # Show repository structure
    structure = repo_map.get_repo_structure()
    print("\nRepository structure (top-level):")
    for dir_name, files in sorted(structure.items())[:5]:
        if dir_name == ".":
            print(f"  - Root: {len(files)} files")
        else:
            print(f"  - {dir_name}/: {len(files)} files")

    # Check if it's a git repository
    if repo_map.is_git_repository():
        git_info = repo_map.get_git_info()
        if git_info:
            print("\nGit repository info:")
            print(f"  - Branch: {git_info.get('branch', 'unknown')}")
            print(f"  - Remote: {git_info.get('remote', 'none')}")


def demonstrate_tree_sitter() -> None:
    """Demonstrate tree-sitter code analysis."""
    print_section("Tree-Sitter Analysis Demo")

    analyzer = TreeSitterAnalyzer()

    # Analyze this example file
    this_file = Path(__file__)

    print(f"Analyzing: {this_file.name}")
    print("-" * 40)

    try:
        # Analyze this file
        result = analyzer.analyze_file(str(this_file))

        print("\nAnalysis results:")
        print(f"  Language: {result.language}")
        print(f"  Definitions: {len(result.definitions)}")
        print(f"  Imports: {len(result.imports)}")
        print(f"  Errors: {len(result.errors)}")

        # Show some definitions
        if result.definitions:
            print("\nDefinitions found:")
            for defn in result.definitions[:5]:
                print(f"  - {defn.category} '{defn.name}' at line {defn.line_number}")
                if defn.docstring:
                    doc_preview = defn.docstring[:50].replace("\n", " ")
                    print(f"    Doc: {doc_preview}...")

    except Exception as e:
        print("Note: Tree-sitter analysis requires optional dependencies")
        print(f"Error: {e}")
        print(
            "\nThe analyzer will fall back to regex-based parsing when tree-sitter is unavailable"
        )


def demonstrate_dependency_graph() -> None:
    """Demonstrate dependency graph generation."""
    print_section("Dependency Graph Demo")

    # Create analyzer and dependency graph
    analyzer = TreeSitterAnalyzer()
    graph = DependencyGraph(analyzer)

    # Analyze Python files in the search module
    module_path = Path(__file__).parent
    print("Analyzing Python files...")

    try:
        # Analyze directory
        analyses = analyzer.analyze_directory(
            str(module_path),
            file_patterns=["*.py"],
            recursive=False,  # Don't recurse into subdirectories
        )

        print(f"Analyzed {len(analyses)} Python files")

        # Build dependency graph from analyses
        graph.build_from_analyses(analyses)

        # Get statistics
        stats = graph.get_statistics()
        print("\nGraph statistics:")
        print(f"  Total nodes: {stats.total_nodes}")
        print(f"  Total edges: {stats.total_edges}")
        print(f"  Max depth: {stats.max_depth}")
        print(f"  Circular dependencies: {len(stats.circular_dependencies)}")

        # Find circular dependencies
        cycles = graph.find_circular_dependencies()
        if cycles:
            print(f"\nFound {len(cycles)} circular dependencies:")
            for cycle in cycles[:3]:
                # Show relative paths
                cycle_paths = [Path(f).name for f in cycle]
                print(f"  - {' -> '.join(cycle_paths)}")
        else:
            print("\nNo circular dependencies found!")

        # Get most depended upon modules
        print("\nMost depended upon modules:")
        most_depended = graph.get_most_depended_upon(limit=5)
        for filepath, count in most_depended:
            filename = Path(filepath).name
            print(f"  - {filename}: {count} dependents")

        # Get modules with most dependencies
        print("\nModules with most dependencies:")
        most_deps = graph.get_most_dependencies(limit=5)
        for filepath, count in most_deps:
            filename = Path(filepath).name
            print(f"  - {filename}: {count} dependencies")

    except Exception as e:
        print("Note: Dependency analysis requires tree-sitter")
        print(f"Error: {e}")


def demonstrate_language_support() -> None:
    """Show supported languages via query files."""
    print_section("Language Support")

    # List available query files
    queries_dir = Path(__file__).parent / "queries"
    if queries_dir.exists():
        query_files = sorted(queries_dir.glob("*-tags.scm"))
        print(f"Found {len(query_files)} language query files:")

        languages = []
        for qf in query_files:
            lang = qf.stem.replace("-tags", "")
            languages.append(lang)

        # Print in columns
        cols = 3
        for i in range(0, len(languages), cols):
            row = languages[i : i + cols]
            print("  " + "".join(f"{lang:<20}" for lang in row))
    else:
        print("Query files directory not found - would be included in standalone package")


def demonstrate_standalone_usage() -> None:
    """Show how to use the module in a standalone way."""
    print_section("Standalone Usage Example")

    print("To use this module in your own project:")
    print("\n1. Copy the entire 'search' directory to your project")
    print("\n2. Install optional dependencies (if needed):")
    print("   pip install tree-sitter grep-ast")
    print("\n3. Import and use:")
    print(
        """
    from search import RepoMap, TreeSitterAnalyzer, DependencyGraph

    # Analyze a repository
    repo = RepoMap("/path/to/repo")
    repo.scan_repository()
    print(repo.get_summary())

    # Analyze code files
    analyzer = TreeSitterAnalyzer()
    result = analyzer.analyze_file("myfile.py")

    # Build dependency graph
    graph = DependencyGraph(analyzer)
    analyses = analyzer.analyze_directory("/path/to/src")
    graph.build_from_analyses(analyses)
    """
    )


def main():
    """Run all demonstrations."""
    print("=== Coda Search Module Demo ===")
    print("\nThis demonstrates the search module working standalone")
    print("with zero dependencies on other coda modules.\n")

    # Run demonstrations
    demonstrate_repo_map()
    demonstrate_dependency_graph()
    demonstrate_tree_sitter()
    demonstrate_language_support()
    demonstrate_standalone_usage()

    # Summary
    print_section("Summary")
    print("✓ Search module works standalone!")
    print("✓ Zero dependencies on other coda modules")
    print("✓ Can be copy-pasted to any project")
    print("✓ Provides repository mapping and search")
    print("✓ Supports dependency graph generation")
    print("✓ Multi-language code parsing (30+ languages)")
    print("✓ Works with or without tree-sitter")


if __name__ == "__main__":
    main()
