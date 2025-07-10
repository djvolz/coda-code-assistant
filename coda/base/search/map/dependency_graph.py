"""
Dependency graph generation for codebase analysis.

This module provides functionality to generate and visualize
dependency relationships between files and modules in a codebase.
"""

import json
from collections import defaultdict, deque
from dataclasses import asdict, dataclass
from pathlib import Path

from .tree_sitter_analyzer import FileAnalysis, TreeSitterAnalyzer


@dataclass
class DependencyNode:
    """Represents a node in the dependency graph."""

    file_path: str
    language: str
    dependencies: list[str]
    dependents: list[str]

    def __post_init__(self):
        if self.dependencies is None:
            self.dependencies = []
        if self.dependents is None:
            self.dependents = []


@dataclass
class DependencyEdge:
    """Represents an edge in the dependency graph."""

    source: str
    target: str
    edge_type: str  # 'import', 'include', 'require', etc.
    line_number: int | None = None


@dataclass
class DependencyGraphStats:
    """Statistics about the dependency graph."""

    total_nodes: int
    total_edges: int
    max_depth: int
    circular_dependencies: list[list[str]]
    most_depended_upon: list[tuple[str, int]]
    most_dependencies: list[tuple[str, int]]


class DependencyGraph:
    """
    Dependency graph generator and analyzer.

    Analyzes code dependencies and provides graph-based insights.
    """

    def __init__(self, analyzer: TreeSitterAnalyzer | None = None):
        """
        Initialize the dependency graph.

        Args:
            analyzer: Tree-sitter analyzer instance
        """
        self.analyzer = analyzer or TreeSitterAnalyzer()
        self.nodes: dict[str, DependencyNode] = {}
        self.edges: list[DependencyEdge] = []
        self.graph: dict[str, set[str]] = defaultdict(set)
        self.reverse_graph: dict[str, set[str]] = defaultdict(set)

    def build_from_analyses(self, analyses: dict[str, FileAnalysis]) -> None:
        """
        Build dependency graph from file analyses.

        Args:
            analyses: Dictionary of file analyses
        """
        self.nodes.clear()
        self.edges.clear()
        self.graph.clear()
        self.reverse_graph.clear()

        # First pass: create nodes
        for file_path, analysis in analyses.items():
            self.nodes[file_path] = DependencyNode(
                file_path=file_path, language=analysis.language, dependencies=[], dependents=[]
            )

        # Second pass: create edges from imports/dependencies
        for file_path, analysis in analyses.items():
            dependencies = self.analyzer.get_file_dependencies(analysis)

            for dep in dependencies:
                # Try to resolve the dependency to an actual file
                resolved_dep = self._resolve_dependency(dep, file_path, analysis.language)

                if resolved_dep and resolved_dep in self.nodes:
                    # Add edge
                    edge = DependencyEdge(source=file_path, target=resolved_dep, edge_type="import")
                    self.edges.append(edge)

                    # Update graph structures
                    self.graph[file_path].add(resolved_dep)
                    self.reverse_graph[resolved_dep].add(file_path)

                    # Update node dependencies
                    self.nodes[file_path].dependencies.append(resolved_dep)
                    self.nodes[resolved_dep].dependents.append(file_path)

    def _resolve_dependency(self, dep: str, source_file: str, language: str) -> str | None:
        """
        Resolve a dependency string to an actual file path.

        Args:
            dep: Dependency string (e.g., "mymodule", "./utils", "../config")
            source_file: Path to the source file
            language: Programming language

        Returns:
            Resolved file path or None if not found
        """
        source_path = Path(source_file)
        source_dir = source_path.parent

        # Language-specific resolution
        if language == "python":
            return self._resolve_python_import(dep, source_dir)
        elif language in ["javascript", "typescript"]:
            return self._resolve_js_import(dep, source_dir)
        elif language in ["c", "cpp"]:
            return self._resolve_c_include(dep, source_dir)
        elif language == "java":
            return self._resolve_java_import(dep, source_dir)
        elif language == "go":
            return self._resolve_go_import(dep, source_dir)
        else:
            # Generic resolution - look for files with matching names
            return self._resolve_generic(dep, source_dir)

    def _resolve_python_import(self, dep: str, source_dir: Path) -> str | None:
        """Resolve Python import to file path."""
        # Handle relative imports
        if dep.startswith("."):
            # Relative import - convert to file path
            parts = dep.lstrip(".").split(".")
            path = source_dir
            for part in parts:
                if part:
                    path = path / part

            # Try .py file
            py_file = path.with_suffix(".py")
            if py_file.exists():
                return str(py_file)

            # Try package __init__.py
            init_file = path / "__init__.py"
            if init_file.exists():
                return str(init_file)

        # Absolute import - look in current directory tree
        parts = dep.split(".")
        current = source_dir

        # Go up until we find the module or reach root
        while current.parent != current:
            path = current
            for part in parts:
                path = path / part

            py_file = path.with_suffix(".py")
            if py_file.exists():
                return str(py_file)

            init_file = path / "__init__.py"
            if init_file.exists():
                return str(init_file)

            current = current.parent

        return None

    def _resolve_js_import(self, dep: str, source_dir: Path) -> str | None:
        """Resolve JavaScript/TypeScript import to file path."""
        if dep.startswith("./") or dep.startswith("../"):
            # Relative import
            path = (source_dir / dep).resolve()

            # Try various extensions
            for ext in [".js", ".ts", ".jsx", ".tsx"]:
                file_path = path.with_suffix(ext)
                if file_path.exists():
                    return str(file_path)

            # Try index files
            for ext in [".js", ".ts", ".jsx", ".tsx"]:
                index_file = path / f"index{ext}"
                if index_file.exists():
                    return str(index_file)

        return None

    def _resolve_c_include(self, dep: str, source_dir: Path) -> str | None:
        """Resolve C/C++ include to file path."""
        # Remove quotes if present
        dep = dep.strip('"<>')

        if not dep.startswith("/"):
            # Relative include
            path = source_dir / dep
            if path.exists():
                return str(path)

        return None

    def _resolve_java_import(self, dep: str, source_dir: Path) -> str | None:
        """Resolve Java import to file path."""
        # Convert package.ClassName to path/ClassName.java
        parts = dep.split(".")
        if parts:
            class_name = parts[-1]
            path = source_dir

            # Go up to find src/main/java or similar structure
            while path.parent != path:
                java_path = path
                for part in parts[:-1]:
                    java_path = java_path / part
                java_file = java_path / f"{class_name}.java"

                if java_file.exists():
                    return str(java_file)

                path = path.parent

        return None

    def _resolve_go_import(self, dep: str, source_dir: Path) -> str | None:
        """Resolve Go import to file path."""
        # Go imports are typically package paths
        # This is a simplified resolution
        parts = dep.strip('"').split("/")
        if parts:
            package_name = parts[-1]

            # Look for .go files in directories
            current = source_dir
            while current.parent != current:
                for go_file in current.glob(f"**/{package_name}/*.go"):
                    return str(go_file)
                current = current.parent

        return None

    def _resolve_generic(self, dep: str, source_dir: Path) -> str | None:
        """Generic dependency resolution."""
        # Simple pattern matching
        current = source_dir
        while current.parent != current:
            try:
                for file_path in current.rglob("*"):
                    try:
                        if file_path.is_file() and dep in file_path.name:
                            return str(file_path)
                    except (OSError, PermissionError):
                        # Skip files we can't access
                        continue
            except (OSError, PermissionError):
                # Skip directories we can't access
                break
            current = current.parent

        return None

    def find_circular_dependencies(self) -> list[list[str]]:
        """
        Find circular dependencies in the graph.

        Returns:
            List of cycles (each cycle is a list of file paths)
        """
        cycles = []
        visited = set()
        rec_stack = set()

        def dfs(node: str, path: list[str]) -> None:
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycle = path[cycle_start:] + [node]
                cycles.append(cycle)
                return

            if node in visited:
                return

            visited.add(node)
            rec_stack.add(node)
            path.append(node)

            for neighbor in self.graph[node]:
                dfs(neighbor, path.copy())

            rec_stack.remove(node)

        for node in self.nodes:
            if node not in visited:
                dfs(node, [])

        return cycles

    def calculate_depth(self, start_node: str) -> int:
        """
        Calculate the maximum depth from a starting node.

        Args:
            start_node: Starting node path

        Returns:
            Maximum depth
        """
        if start_node not in self.nodes:
            return 0

        visited = set()
        queue = deque([(start_node, 0)])
        max_depth = 0

        while queue:
            node, depth = queue.popleft()

            if node in visited:
                continue

            visited.add(node)
            max_depth = max(max_depth, depth)

            for neighbor in self.graph[node]:
                if neighbor not in visited:
                    queue.append((neighbor, depth + 1))

        return max_depth

    def get_most_depended_upon(self, limit: int = 10) -> list[tuple[str, int]]:
        """
        Get files that are most depended upon (most incoming edges).

        Args:
            limit: Maximum number of results

        Returns:
            List of (file_path, dependent_count) tuples
        """
        dependents_count = [(node, len(data.dependents)) for node, data in self.nodes.items()]
        return sorted(dependents_count, key=lambda x: x[1], reverse=True)[:limit]

    def get_most_dependencies(self, limit: int = 10) -> list[tuple[str, int]]:
        """
        Get files with most dependencies (most outgoing edges).

        Args:
            limit: Maximum number of results

        Returns:
            List of (file_path, dependency_count) tuples
        """
        dependencies_count = [(node, len(data.dependencies)) for node, data in self.nodes.items()]
        return sorted(dependencies_count, key=lambda x: x[1], reverse=True)[:limit]

    def get_statistics(self) -> DependencyGraphStats:
        """
        Get comprehensive statistics about the dependency graph.

        Returns:
            DependencyGraphStats object
        """
        circular_deps = self.find_circular_dependencies()

        # Calculate maximum depth across all nodes
        max_depth = 0
        for node in self.nodes:
            depth = self.calculate_depth(node)
            max_depth = max(max_depth, depth)

        return DependencyGraphStats(
            total_nodes=len(self.nodes),
            total_edges=len(self.edges),
            max_depth=max_depth,
            circular_dependencies=circular_deps,
            most_depended_upon=self.get_most_depended_upon(),
            most_dependencies=self.get_most_dependencies(),
        )

    def to_dict(self) -> dict:
        """
        Export graph to dictionary format.

        Returns:
            Dictionary representation of the graph
        """
        return {
            "nodes": {path: asdict(node) for path, node in self.nodes.items()},
            "edges": [asdict(edge) for edge in self.edges],
            "statistics": asdict(self.get_statistics()),
        }

    def to_json(self, file_path: str | Path) -> None:
        """
        Export graph to JSON file.

        Args:
            file_path: Output file path
        """
        with open(file_path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dot(self, file_path: str | Path, max_nodes: int = 50) -> None:
        """
        Export graph to DOT format for visualization with Graphviz.

        Args:
            file_path: Output file path
            max_nodes: Maximum number of nodes to include
        """
        # Limit nodes to most important ones
        important_nodes = self.get_most_depended_upon(max_nodes // 2)
        important_nodes.extend(self.get_most_dependencies(max_nodes // 2))
        node_set = set(node for node, _ in important_nodes)

        # Ensure we have at least some nodes
        if len(node_set) < max_nodes:
            remaining = max_nodes - len(node_set)
            for node in list(self.nodes.keys())[:remaining]:
                node_set.add(node)

        with open(file_path, "w") as f:
            f.write("digraph dependencies {\n")
            f.write("  rankdir=TB;\n")
            f.write("  node [shape=box, style=filled, fillcolor=lightblue];\n")

            # Write nodes
            for i, node in enumerate(node_set):
                node_data = self.nodes[node]
                label = Path(node).name  # Use just filename for readability
                f.write(f'  n{i} [label="{label}\\n({node_data.language})"];\n')

            # Create node index mapping
            node_to_index = {node: i for i, node in enumerate(node_set)}

            # Write edges
            for edge in self.edges:
                if edge.source in node_to_index and edge.target in node_to_index:
                    src_idx = node_to_index[edge.source]
                    tgt_idx = node_to_index[edge.target]
                    f.write(f"  n{src_idx} -> n{tgt_idx};\n")

            f.write("}\n")
