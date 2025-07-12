"""
CLI commands for codebase intelligence features.
"""

from pathlib import Path

from .map.dependency_graph import DependencyGraph
from .map.repo_map import RepoMap
from .map.tree_sitter_analyzer import TreeSitterAnalyzer


class IntelligenceCommands:
    """CLI commands for codebase intelligence."""

    def __init__(self):
        self.repo_map = None
        self.analyzer = TreeSitterAnalyzer()
        self.dependency_graph = DependencyGraph(self.analyzer)

    def handle_command(self, command: str, args: list[str]) -> str:
        """
        Handle intelligence commands.

        Args:
            command: Command name
            args: Command arguments

        Returns:
            Command output
        """
        if command == "analyze":
            return self._handle_analyze(args)
        elif command == "map":
            return self._handle_map(args)
        elif command == "scan":
            return self._handle_scan(args)
        elif command == "stats":
            return self._handle_stats(args)
        elif command == "find":
            return self._handle_find(args)
        elif command == "deps":
            return self._handle_deps(args)
        elif command == "graph":
            return self._handle_graph(args)
        else:
            return f"Unknown intelligence command: {command}"

    def _handle_analyze(self, args: list[str]) -> str:
        """Handle file analysis command."""
        if not args:
            return "Usage: /map analyze <file_path>"

        file_path = Path(args[0])
        if not file_path.exists():
            return f"File not found: {file_path}"

        try:
            analysis = self.analyzer.analyze_file(file_path)

            result = []
            result.append(f"File: {analysis.file_path}")
            result.append(f"Language: {analysis.language}")
            result.append(f"Definitions: {len(analysis.definitions)}")
            result.append(f"References: {len(analysis.references)}")
            result.append(f"Imports: {len(analysis.imports)}")

            if analysis.errors:
                result.append(f"Errors: {len(analysis.errors)}")
                for error in analysis.errors:
                    result.append(f"  - {error}")

            if analysis.definitions:
                result.append("\nDefinitions:")
                for definition in analysis.definitions:
                    result.append(
                        f"  {definition.kind.value}: {definition.name} (line {definition.line})"
                    )

            if analysis.imports:
                result.append("\nImports:")
                for import_item in analysis.imports:
                    result.append(f"  - {import_item.name}")

            return "\n".join(result)

        except Exception as e:
            return f"Error analyzing file: {e}"

    def _handle_map(self, args: list[str]) -> str:
        """Handle repository mapping command."""
        repo_path = Path(args[0]) if args else Path.cwd()

        if not repo_path.exists():
            return f"Path not found: {repo_path}"

        try:
            self.repo_map = RepoMap(repo_path)
            self.repo_map.scan_repository()

            summary = self.repo_map.get_summary()

            result = []
            result.append(f"Repository: {repo_path}")
            result.append(f"Total files: {summary['total_files']}")
            result.append(f"Total size: {summary['total_size']} bytes")

            if summary["top_languages"]:
                result.append("\nTop languages:")
                for lang, count in list(summary["top_languages"].items())[:5]:
                    result.append(f"  {lang}: {count} files")

            return "\n".join(result)

        except Exception as e:
            return f"Error mapping repository: {e}"

    def _handle_scan(self, args: list[str]) -> str:
        """Handle directory scanning command."""
        directory = Path(args[0]) if args else Path.cwd()

        if not directory.exists():
            return f"Directory not found: {directory}"

        try:
            import sys

            # Progress tracking
            last_progress = [0]  # Using list to modify in closure

            def show_progress(current, total, filename):
                # Update progress every 10% or on last file
                progress = int((current / total) * 100)
                if progress >= last_progress[0] + 10 or current == total:
                    sys.stdout.write(
                        f"\rScanning: {progress}% ({current}/{total} files) - {filename[:50]:<50}"
                    )
                    sys.stdout.flush()
                    last_progress[0] = progress

            # Clear the line before starting
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

            analyses = self.analyzer.analyze_directory(directory, progress_callback=show_progress)

            # Clear the progress line
            sys.stdout.write("\r" + " " * 80 + "\r")
            sys.stdout.flush()

            if not analyses:
                return "No supported files found in directory."

            result = []
            result.append(f"Scanned {len(analyses)} files in {directory}")

            # Get summary by language
            language_counts = {}
            for analysis in analyses.values():
                lang = analysis.language
                if lang not in language_counts:
                    language_counts[lang] = {"files": 0, "definitions": 0, "imports": 0}
                language_counts[lang]["files"] += 1
                language_counts[lang]["definitions"] += len(analysis.definitions)
                language_counts[lang]["imports"] += len(analysis.imports)

            result.append("\nBy language:")
            for lang, stats in language_counts.items():
                result.append(
                    f"  {lang}: {stats['files']} files, {stats['definitions']} definitions, {stats['imports']} imports"
                )

            return "\n".join(result)

        except Exception as e:
            return f"Error scanning directory: {e}"

    def _handle_stats(self, args: list[str]) -> str:
        """Handle statistics command."""
        if not self.repo_map:
            return "No repository mapped. Use '/map' first."

        try:
            language_stats = self.repo_map.get_language_stats()

            result = []
            result.append("Language statistics:")

            for lang, stats in language_stats.items():
                result.append(f"\n{lang}:")
                result.append(f"  Files: {stats['file_count']}")
                result.append(f"  Size: {stats['total_size']} bytes")
                result.append(f"  Percentage: {stats['percentage']:.1f}%")
                result.append(f"  Avg size: {stats['average_size']:.0f} bytes")

            return "\n".join(result)

        except Exception as e:
            return f"Error getting statistics: {e}"

    def _handle_find(self, args: list[str]) -> str:
        """Handle find definition command."""
        if not args:
            return "Usage: /map find <name>"

        name = args[0]

        # First try to find in current repository map
        if self.repo_map:
            try:
                # Scan all files in the repository
                analyses = {}
                for file_path in self.repo_map.files.keys():
                    full_path = self.repo_map.root_path / file_path
                    if full_path.exists():
                        analysis = self.analyzer.analyze_file(full_path)
                        analyses[file_path] = analysis

                definitions = self.analyzer.find_definition(name, analyses)

                if definitions:
                    result = [f"Found {len(definitions)} definition(s) for '{name}':"]
                    for definition in definitions:
                        result.append(
                            f"  {definition.file_path}:{definition.line} - {definition.kind.value}"
                        )
                    return "\n".join(result)
                else:
                    return f"No definitions found for '{name}'"

            except Exception as e:
                return f"Error finding definition: {e}"
        else:
            return "No repository mapped. Use '/map' first."

    def _handle_deps(self, args: list[str]) -> str:
        """Handle dependencies command."""
        if not args:
            return "Usage: /map deps <file_path>"

        file_path = Path(args[0])
        if not file_path.exists():
            return f"File not found: {file_path}"

        try:
            analysis = self.analyzer.analyze_file(file_path)
            deps = self.analyzer.get_file_dependencies(analysis)

            if deps:
                result = [f"Dependencies for {file_path}:"]
                for dep in deps:
                    result.append(f"  - {dep}")
                return "\n".join(result)
            else:
                return f"No dependencies found for {file_path}"

        except Exception as e:
            return f"Error getting dependencies: {e}"

    def _handle_graph(self, args: list[str]) -> str:
        """Handle dependency graph command."""
        if not args:
            return "Usage: /map graph <directory> [--format=json|dot] [--output=filename]"

        directory = Path(args[0])
        if not directory.exists():
            return f"Directory not found: {directory}"

        # Parse additional arguments
        output_format = "json"
        output_file = None

        for arg in args[1:]:
            if arg.startswith("--format="):
                output_format = arg.split("=")[1]
            elif arg.startswith("--output="):
                output_file = arg.split("=")[1]

        try:
            # Analyze all files in the directory
            analyses = self.analyzer.analyze_directory(directory)

            if not analyses:
                return "No supported files found in directory."

            # Build dependency graph
            self.dependency_graph.build_from_analyses(analyses)

            # Get statistics
            stats = self.dependency_graph.get_statistics()

            result = []
            result.append(f"Dependency Graph for {directory}")
            result.append(f"Nodes: {stats.total_nodes}")
            result.append(f"Edges: {stats.total_edges}")
            result.append(f"Max depth: {stats.max_depth}")

            if stats.circular_dependencies:
                result.append(f"\nCircular dependencies found: {len(stats.circular_dependencies)}")
                for i, cycle in enumerate(stats.circular_dependencies[:3]):  # Show first 3
                    result.append(f"  Cycle {i + 1}: {' -> '.join(Path(p).name for p in cycle)}")
                if len(stats.circular_dependencies) > 3:
                    result.append(f"  ... and {len(stats.circular_dependencies) - 3} more")

            if stats.most_depended_upon:
                result.append("\nMost depended upon files:")
                for file_path, count in stats.most_depended_upon[:5]:
                    result.append(f"  {Path(file_path).name}: {count} dependents")

            if stats.most_dependencies:
                result.append("\nFiles with most dependencies:")
                for file_path, count in stats.most_dependencies[:5]:
                    result.append(f"  {Path(file_path).name}: {count} dependencies")

            # Export if requested
            if output_file:
                if output_format == "json":
                    self.dependency_graph.to_json(output_file)
                    result.append(f"\nGraph exported to {output_file} (JSON)")
                elif output_format == "dot":
                    self.dependency_graph.to_dot(output_file)
                    result.append(f"\nGraph exported to {output_file} (DOT)")
                    result.append("Use 'dot -Tpng output.dot -o output.png' to generate image")
                else:
                    result.append(f"\nUnsupported format: {output_format}")

            return "\n".join(result)

        except Exception as e:
            return f"Error generating dependency graph: {e}"

    def get_help(self) -> str:
        """Get help text for intelligence commands."""
        help_text = """
Map Commands:
  /map analyze <file>     - Analyze a single file
  /map [path]             - Map repository structure
  /map scan [dir]         - Scan directory for code files
  /map stats              - Show language statistics
  /map find <name>        - Find definitions by name
  /map deps <file>        - Show file dependencies
  /map graph <dir>        - Generate dependency graph
  /map help               - Show this help

Graph Options:
  --format=json|dot         - Output format (default: json)
  --output=filename         - Export to file
"""
        return help_text.strip()
