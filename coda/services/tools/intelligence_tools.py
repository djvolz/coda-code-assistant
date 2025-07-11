"""
Intelligence tools for codebase analysis using tree-sitter.
"""

from pathlib import Path
from typing import Any

from coda.base.search import DependencyGraph, RepoMap, TreeSitterAnalyzer
from coda.base.search.map.tree_sitter_query_analyzer import DefinitionKind

from .base import (
    BaseTool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolSchema,
    tool_registry,
)


class AnalyzeFileTool(BaseTool):
    """Analyze a source code file to extract semantic information."""

    def __init__(self):
        super().__init__()
        self.analyzer = TreeSitterAnalyzer()

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="analyze_code_file",
            description="Analyze a source code file to extract definitions, imports, and references using tree-sitter",
            category="intelligence",
            parameters={
                "file_path": ToolParameter(
                    type=ToolParameterType.STRING, description="Path to the file to analyze"
                ),
                "include_references": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Include references (function calls, etc.) in the analysis",
                    required=False,
                    default=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the file analysis."""
        file_path = arguments["file_path"]
        include_references = arguments.get("include_references", False)

        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False, error=f"File not found: {file_path}", tool="analyze_code_file"
                )

            analysis = self.analyzer.analyze_file(path)

            # Build result dictionary
            result = {
                "file_path": str(analysis.file_path),
                "language": analysis.language,
                "definitions": [
                    {
                        "name": d.name,
                        "kind": d.kind.value,
                        "line": d.line,
                        "column": d.column,
                        "docstring": d.docstring,
                    }
                    for d in analysis.definitions
                ],
                "imports": [{"name": i.name, "line": i.line} for i in analysis.imports],
                "errors": analysis.errors,
            }

            if include_references:
                result["references"] = [
                    {"name": r.name, "kind": r.kind.value, "line": r.line, "column": r.column}
                    for r in analysis.references
                ]

            # Create summary
            summary = f"Analyzed {path.name} ({analysis.language}): "
            summary += f"{len(analysis.definitions)} definitions, "
            summary += f"{len(analysis.imports)} imports"
            if include_references:
                summary += f", {len(analysis.references)} references"

            return ToolResult(
                success=True,
                result=result,
                tool="analyze_code_file",
                metadata={
                    "language": analysis.language,
                    "definition_count": len(analysis.definitions),
                    "import_count": len(analysis.imports),
                    "reference_count": len(analysis.references) if include_references else 0,
                    "summary": summary,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, error=f"Error analyzing file: {str(e)}", tool="analyze_code_file"
            )


class ScanDirectoryTool(BaseTool):
    """Scan a directory to analyze all source code files."""

    def __init__(self):
        super().__init__()
        self.analyzer = TreeSitterAnalyzer()

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="scan_code_directory",
            description="Scan a directory to analyze all source code files and get aggregate statistics",
            category="intelligence",
            parameters={
                "directory": ToolParameter(
                    type=ToolParameterType.STRING, description="Directory path to scan"
                ),
                "recursive": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Scan directory recursively",
                    required=False,
                    default=True,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the directory scan."""
        directory = arguments["directory"]
        recursive = arguments.get("recursive", True)

        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {directory}",
                    tool="scan_code_directory",
                )

            analyses = self.analyzer.analyze_directory(dir_path, recursive=recursive)

            if not analyses:
                return ToolResult(
                    success=True,
                    result={"message": "No supported files found in directory"},
                    tool="scan_code_directory",
                    metadata={"file_count": 0},
                )

            # Aggregate statistics by language
            language_stats = {}
            total_definitions = 0
            total_imports = 0

            for _file_path, analysis in analyses.items():
                lang = analysis.language
                if lang not in language_stats:
                    language_stats[lang] = {
                        "files": 0,
                        "definitions": 0,
                        "imports": 0,
                        "classes": 0,
                        "functions": 0,
                    }

                language_stats[lang]["files"] += 1
                language_stats[lang]["definitions"] += len(analysis.definitions)
                language_stats[lang]["imports"] += len(analysis.imports)

                # Count specific definition types
                for defn in analysis.definitions:
                    if defn.kind == DefinitionKind.CLASS:
                        language_stats[lang]["classes"] += 1
                    elif defn.kind in [DefinitionKind.FUNCTION, DefinitionKind.METHOD]:
                        language_stats[lang]["functions"] += 1

                total_definitions += len(analysis.definitions)
                total_imports += len(analysis.imports)

            result = {
                "directory": str(directory),
                "total_files": len(analyses),
                "total_definitions": total_definitions,
                "total_imports": total_imports,
                "languages": language_stats,
            }

            return ToolResult(
                success=True,
                result=result,
                tool="scan_code_directory",
                metadata={
                    "file_count": len(analyses),
                    "language_count": len(language_stats),
                    "summary": f"Scanned {len(analyses)} files: {total_definitions} definitions, {total_imports} imports",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error scanning directory: {str(e)}",
                tool="scan_code_directory",
            )


class FindDefinitionTool(BaseTool):
    """Find definitions by name in the codebase."""

    def __init__(self):
        super().__init__()
        self.analyzer = TreeSitterAnalyzer()

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="find_code_definition",
            description="Find all definitions matching a name in the codebase",
            category="intelligence",
            parameters={
                "name": ToolParameter(
                    type=ToolParameterType.STRING, description="Name to search for"
                ),
                "directory": ToolParameter(
                    type=ToolParameterType.STRING, description="Directory to search in"
                ),
                "kind": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Filter by definition kind",
                    required=False,
                    enum=[
                        "function",
                        "class",
                        "method",
                        "variable",
                        "constant",
                        "interface",
                        "type",
                        "enum",
                        "struct",
                        "trait",
                        "module",
                    ],
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the definition search."""
        name = arguments["name"]
        directory = arguments["directory"]
        kind = arguments.get("kind")

        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {directory}",
                    tool="find_code_definition",
                )

            # Convert string kind to DefinitionKind enum if provided
            definition_kind = None
            if kind:
                try:
                    definition_kind = DefinitionKind(kind)
                except ValueError:
                    return ToolResult(
                        success=False,
                        error=f"Invalid definition kind: {kind}",
                        tool="find_code_definition",
                    )

            # Find definitions
            definitions = self.analyzer.find_definition(name, str(dir_path), kind=definition_kind)

            if not definitions:
                return ToolResult(
                    success=True,
                    result={"message": f"No definitions found for '{name}'"},
                    tool="find_code_definition",
                    metadata={"found_count": 0},
                )

            # Format results
            results = []
            for defn in definitions:
                results.append(
                    {
                        "file": defn.file_path,
                        "line": defn.line,
                        "column": defn.column,
                        "kind": defn.kind.value,
                        "full_text": defn.full_text,
                    }
                )

            return ToolResult(
                success=True,
                result={"name": name, "definitions": results, "count": len(results)},
                tool="find_code_definition",
                metadata={
                    "found_count": len(results),
                    "summary": f"Found {len(results)} definition(s) for '{name}'",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error finding definitions: {str(e)}",
                tool="find_code_definition",
            )


class GetFileDependenciesTool(BaseTool):
    """Get dependencies (imports) for a source file."""

    def __init__(self):
        super().__init__()
        self.analyzer = TreeSitterAnalyzer()

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="get_file_dependencies",
            description="Get all dependencies (imports) for a source code file",
            category="intelligence",
            parameters={
                "file_path": ToolParameter(
                    type=ToolParameterType.STRING, description="Path to the file"
                )
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the dependency extraction."""
        file_path = arguments["file_path"]

        try:
            path = Path(file_path)
            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path}",
                    tool="get_file_dependencies",
                )

            analysis = self.analyzer.analyze_file(path)
            dependencies = self.analyzer.get_file_dependencies(analysis)

            result = {
                "file": str(file_path),
                "language": analysis.language,
                "dependencies": dependencies,
                "count": len(dependencies),
            }

            return ToolResult(
                success=True,
                result=result,
                tool="get_file_dependencies",
                metadata={
                    "dependency_count": len(dependencies),
                    "summary": f"Found {len(dependencies)} dependencies for {path.name}",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting dependencies: {str(e)}",
                tool="get_file_dependencies",
            )


class BuildDependencyGraphTool(BaseTool):
    """Build a dependency graph for a directory."""

    def __init__(self):
        super().__init__()
        self.analyzer = TreeSitterAnalyzer()
        self.dep_graph = DependencyGraph(self.analyzer)

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="build_dependency_graph",
            description="Build a dependency graph for all files in a directory",
            category="intelligence",
            parameters={
                "directory": ToolParameter(
                    type=ToolParameterType.STRING, description="Directory to analyze"
                ),
                "include_cycles": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Include circular dependency detection",
                    required=False,
                    default=True,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the dependency graph building."""
        directory = arguments["directory"]
        include_cycles = arguments.get("include_cycles", True)

        try:
            dir_path = Path(directory)
            if not dir_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {directory}",
                    tool="build_dependency_graph",
                )

            # Analyze all files
            analyses = self.analyzer.analyze_directory(dir_path)

            if not analyses:
                return ToolResult(
                    success=True,
                    result={"message": "No supported files found in directory"},
                    tool="build_dependency_graph",
                    metadata={"file_count": 0},
                )

            # Build dependency graph
            self.dep_graph.build_from_analyses(analyses)

            # Get statistics
            stats = self.dep_graph.get_statistics()

            result = {
                "directory": str(directory),
                "total_nodes": stats.total_nodes,
                "total_edges": stats.total_edges,
                "max_depth": stats.max_depth,
            }

            # Add most depended upon files
            if stats.most_depended_upon:
                result["most_depended_upon"] = [
                    {"file": Path(f).name, "dependents": c}
                    for f, c in stats.most_depended_upon[:10]
                ]

            # Add files with most dependencies
            if stats.most_dependencies:
                result["most_dependencies"] = [
                    {"file": Path(f).name, "dependencies": c}
                    for f, c in stats.most_dependencies[:10]
                ]

            # Add circular dependencies if requested
            if include_cycles and stats.circular_dependencies:
                result["circular_dependencies"] = [
                    [Path(f).name for f in cycle] for cycle in stats.circular_dependencies[:10]
                ]
                result["circular_dependency_count"] = len(stats.circular_dependencies)

            return ToolResult(
                success=True,
                result=result,
                tool="build_dependency_graph",
                metadata={
                    "node_count": stats.total_nodes,
                    "edge_count": stats.total_edges,
                    "has_cycles": len(stats.circular_dependencies) > 0,
                    "summary": f"Graph with {stats.total_nodes} files and {stats.total_edges} dependencies",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error building dependency graph: {str(e)}",
                tool="build_dependency_graph",
            )


class MapRepositoryTool(BaseTool):
    """Map repository structure and get aggregate information."""

    def __init__(self):
        super().__init__()
        self.repo_map = None

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="map_repository",
            description="Map repository structure to get file counts, sizes, and language distribution",
            category="intelligence",
            parameters={
                "repository_path": ToolParameter(
                    type=ToolParameterType.STRING, description="Path to the repository root"
                ),
                "include_git_info": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Include git repository information if available",
                    required=False,
                    default=True,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        """Execute the repository mapping."""
        repository_path = arguments["repository_path"]
        include_git_info = arguments.get("include_git_info", True)

        try:
            repo_path = Path(repository_path)
            if not repo_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Repository path not found: {repository_path}",
                    tool="map_repository",
                )

            self.repo_map = RepoMap(repo_path)
            self.repo_map.scan_repository()

            summary = self.repo_map.get_summary()
            language_stats = self.repo_map.get_language_stats()

            result = {
                "repository": str(repository_path),
                "total_files": summary["total_files"],
                "total_size": summary["total_size"],
                "total_lines": summary.get("total_lines", 0),
                "languages": {},
            }

            # Add language statistics
            for lang, stats in language_stats.items():
                result["languages"][lang] = {
                    "files": stats["file_count"],
                    "size": stats["total_size"],
                    "lines": stats.get("total_lines", 0),
                    "percentage": round(stats["percentage"], 1),
                }

            # Add git info if requested and available
            if include_git_info:
                git_info = self.repo_map.get_git_info()
                if git_info:
                    result["git"] = {
                        "branch": git_info.get("branch", "unknown"),
                        "remote": git_info.get("remote", "unknown"),
                        "commit": git_info.get("commit", "unknown")[:8],  # Short hash
                    }

            return ToolResult(
                success=True,
                result=result,
                tool="map_repository",
                metadata={
                    "file_count": summary["total_files"],
                    "language_count": len(language_stats),
                    "summary": f"Repository with {summary['total_files']} files across {len(language_stats)} languages",
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, error=f"Error mapping repository: {str(e)}", tool="map_repository"
            )


# Register all intelligence tools
tool_registry.register(AnalyzeFileTool())
tool_registry.register(ScanDirectoryTool())
tool_registry.register(FindDefinitionTool())
tool_registry.register(GetFileDependenciesTool())
tool_registry.register(BuildDependencyGraphTool())
tool_registry.register(MapRepositoryTool())
