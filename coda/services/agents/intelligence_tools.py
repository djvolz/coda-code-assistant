"""Native intelligence tools for quick code analysis using @tool decorator."""

from pathlib import Path

from coda.base.search import TreeSitterAnalyzer
from coda.services.agents.decorators import tool

# Initialize analyzer once for all tools
_analyzer = TreeSitterAnalyzer()


@tool(description="Find code definitions by name in current directory")
def find_definition(name: str, kind: str | None = None) -> str:
    """
    Quick search for code definitions by name.

    Args:
        name: Name to search for (e.g., 'MyClass', 'process_data')
        kind: Optional filter - function, class, method, variable, etc.

    Returns:
        Formatted string with results or "No definitions found"
    """
    try:
        from coda.base.search.tree_sitter_query_analyzer import DefinitionKind

        # Search in current directory
        directory = Path.cwd()

        # Convert kind string to enum if provided
        definition_kind = None
        if kind:
            try:
                definition_kind = DefinitionKind(kind)
            except ValueError:
                return f"Invalid kind '{kind}'. Valid options: function, class, method, variable, constant, interface, type, enum, struct, trait, module"

        # Find definitions
        definitions = _analyzer.find_definition(name, str(directory), kind=definition_kind)

        if not definitions:
            return f"No definitions found for '{name}'"

        # Format results
        results = [f"Found {len(definitions)} definition(s) for '{name}':"]
        for defn in definitions:
            file_path = Path(defn.file_path)
            relative_path = (
                file_path.relative_to(directory) if file_path.is_absolute() else file_path
            )
            results.append(f"  {relative_path}:{defn.line} - {defn.kind.value}")

        return "\n".join(results)

    except Exception as e:
        return f"Error searching for '{name}': {str(e)}"


@tool(description="Analyze current file or specified file for code structure")
def analyze_code(file_path: str | None = None) -> str:
    """
    Quick analysis of a code file's structure.

    Args:
        file_path: Path to analyze (default: currently discussed file)

    Returns:
        Summary of definitions and imports found
    """
    try:
        if not file_path:
            return "Please specify a file path to analyze"

        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"

        analysis = _analyzer.analyze_file(path)

        # Build summary
        lines = [f"=== Analysis of {path.name} ({analysis.language}) ==="]

        # Group definitions by kind
        definitions_by_kind = {}
        for defn in analysis.definitions:
            kind = defn.kind.value
            if kind not in definitions_by_kind:
                definitions_by_kind[kind] = []
            definitions_by_kind[kind].append(defn.name)

        if definitions_by_kind:
            lines.append("\nDefinitions:")
            for kind, names in sorted(definitions_by_kind.items()):
                lines.append(f"  {kind}s: {', '.join(names)}")
        else:
            lines.append("\nNo definitions found")

        # List imports
        if analysis.imports:
            lines.append(f"\nImports ({len(analysis.imports)}):")
            # Deduplicate import names
            import_names = list(set(imp.name for imp in analysis.imports))
            for name in sorted(import_names)[:10]:  # Show first 10
                lines.append(f"  - {name}")
            if len(import_names) > 10:
                lines.append(f"  ... and {len(import_names) - 10} more")

        # Show errors if any
        if analysis.errors:
            lines.append(f"\nWarnings: {', '.join(analysis.errors)}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error analyzing file: {str(e)}"


@tool(description="Get file dependencies (imports)")
def get_dependencies(file_path: str) -> str:
    """
    List all dependencies (imports) for a file.

    Args:
        file_path: Path to the file

    Returns:
        List of dependencies or error message
    """
    try:
        path = Path(file_path)
        if not path.exists():
            return f"File not found: {file_path}"

        analysis = _analyzer.analyze_file(path)
        dependencies = _analyzer.get_file_dependencies(analysis)

        if not dependencies:
            return f"No dependencies found in {path.name}"

        # Format results
        lines = [f"Dependencies for {path.name} ({analysis.language}):"]
        for dep in sorted(set(dependencies)):  # Deduplicate and sort
            lines.append(f"  - {dep}")

        return "\n".join(lines)

    except Exception as e:
        return f"Error getting dependencies: {str(e)}"


@tool(description="Quick code statistics for current directory")
def code_stats(directory: str | None = None) -> str:
    """
    Get quick code statistics for a directory.

    Args:
        directory: Directory to analyze (default: current directory)

    Returns:
        Summary statistics by language
    """
    try:
        dir_path = Path(directory) if directory else Path.cwd()
        if not dir_path.exists():
            return f"Directory not found: {directory}"

        # Analyze directory (non-recursive for speed)
        analyses = _analyzer.analyze_directory(dir_path, recursive=False)

        if not analyses:
            return "No code files found in directory"

        # Aggregate stats
        stats = {}
        total_definitions = 0

        for analysis in analyses.values():
            lang = analysis.language
            if lang not in stats:
                stats[lang] = {"files": 0, "definitions": 0, "classes": 0, "functions": 0}

            stats[lang]["files"] += 1
            stats[lang]["definitions"] += len(analysis.definitions)
            total_definitions += len(analysis.definitions)

            # Count specific types
            for defn in analysis.definitions:
                if defn.kind.value == "class":
                    stats[lang]["classes"] += 1
                elif defn.kind.value in ["function", "method"]:
                    stats[lang]["functions"] += 1

        # Format results
        lines = [f"Code statistics for {dir_path.name}:"]
        lines.append(f"Total files: {len(analyses)}")
        lines.append(f"Total definitions: {total_definitions}")
        lines.append("\nBy language:")

        for lang, data in sorted(stats.items()):
            lines.append(
                f"  {lang}: {data['files']} files, {data['definitions']} definitions ({data['classes']} classes, {data['functions']} functions)"
            )

        return "\n".join(lines)

    except Exception as e:
        return f"Error getting code statistics: {str(e)}"


@tool(description="Find specific patterns in code (classes, functions, imports)")
def find_pattern(pattern: str, file_type: str | None = None) -> str:
    """
    Search for specific code patterns in current directory.

    Args:
        pattern: What to search for - 'classes', 'functions', 'imports', or a specific name
        file_type: Optional file extension filter (e.g., 'py', 'js')

    Returns:
        List of matches with file locations
    """
    try:
        directory = Path.cwd()

        # Build file pattern
        file_patterns = [f"*.{file_type}"] if file_type else None

        # Analyze directory
        analyses = _analyzer.analyze_directory(
            directory, recursive=True, file_patterns=file_patterns
        )

        if not analyses:
            return "No matching files found"

        results = []
        pattern_lower = pattern.lower()

        for file_path, analysis in analyses.items():
            matches = []

            # Search based on pattern
            if pattern_lower in ["classes", "class"]:
                matches = [
                    (d.name, d.line, "class")
                    for d in analysis.definitions
                    if d.kind.value == "class"
                ]
            elif pattern_lower in ["functions", "function", "methods", "method"]:
                matches = [
                    (d.name, d.line, d.kind.value)
                    for d in analysis.definitions
                    if d.kind.value in ["function", "method"]
                ]
            elif pattern_lower in ["imports", "import"]:
                matches = [(i.name, i.line, "import") for i in analysis.imports]
            else:
                # Search for specific name
                matches = [
                    (d.name, d.line, d.kind.value)
                    for d in analysis.definitions
                    if pattern.lower() in d.name.lower()
                ]

            if matches:
                rel_path = Path(file_path).relative_to(directory)
                for name, line, kind in matches:
                    results.append(f"{rel_path}:{line} - {kind}: {name}")

        if not results:
            return f"No matches found for pattern '{pattern}'"

        # Format results
        lines = [f"Found {len(results)} match(es) for '{pattern}':"]
        for result in results[:20]:  # Show first 20
            lines.append(f"  {result}")
        if len(results) > 20:
            lines.append(f"  ... and {len(results) - 20} more")

        return "\n".join(lines)

    except Exception as e:
        return f"Error searching for pattern: {str(e)}"
