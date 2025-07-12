"""
Tree-sitter query-based analyzer for code structure analysis.

This module provides tree-sitter based code parsing using query files (.scm),
following aider's approach with tree-sitter-language-pack.
"""

import logging
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import tree-sitter components
try:
    import tree_sitter
    from grep_ast import filename_to_lang
    from grep_ast.tsl import get_language, get_parser

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    filename_to_lang = None
    get_language = None
    get_parser = None
    tree_sitter = None

logger = logging.getLogger(__name__)


class DefinitionKind(Enum):
    """Types of code definitions."""

    FUNCTION = "function"
    CLASS = "class"
    METHOD = "method"
    VARIABLE = "variable"
    CONSTANT = "constant"
    INTERFACE = "interface"
    MODULE = "module"
    STRUCT = "struct"
    ENUM = "enum"
    TRAIT = "trait"
    MACRO = "macro"
    IMPORT = "import"
    TYPE = "type"
    CONSTRUCTOR = "constructor"
    UNKNOWN = "unknown"


@dataclass
class CodeElement:
    """Represents a code element (definition or reference)."""

    name: str
    kind: DefinitionKind
    line: int
    column: int
    file_path: str
    language: str
    is_definition: bool = True
    parent_scope: str | None = None
    docstring: str | None = None
    full_text: str | None = None
    modifiers: list[str] | None = None
    parameters: list[str] | None = None
    return_type: str | None = None

    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []
        if self.parameters is None:
            self.parameters = []

    def __str__(self) -> str:
        return f"{self.name} ({self.kind.value})"

    def __repr__(self) -> str:
        return (
            f"CodeElement(name='{self.name}', kind={self.kind}, "
            f"line={self.line}, file='{self.file_path}', "
            f"is_definition={self.is_definition})"
        )


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""

    file_path: str
    language: str
    definitions: list[CodeElement]
    references: list[CodeElement]
    imports: list[CodeElement]
    errors: list[str]

    def __post_init__(self):
        if self.definitions is None:
            self.definitions = []
        if self.references is None:
            self.references = []
        if self.imports is None:
            self.imports = []
        if self.errors is None:
            self.errors = []


class TreeSitterQueryAnalyzer:
    """
    Tree-sitter analyzer using query files for pattern matching.

    This analyzer uses tree-sitter-language-pack to parse code files
    and extract semantic information using .scm query files.
    """

    def __init__(self, query_dir: Path | None = None):
        """
        Initialize the query-based analyzer.

        Args:
            query_dir: Directory containing .scm query files
        """
        if not TREE_SITTER_AVAILABLE:
            logger.warning("tree-sitter-language-pack not available, falling back to regex mode")

        if query_dir is None:
            query_dir = Path(__file__).parent / "queries"

        self.query_dir = Path(query_dir)
        if not self.query_dir.exists():
            logger.warning(f"Query directory {self.query_dir} does not exist")

        self._parser_cache = {}
        self._query_cache = {}

    def analyze_file(self, file_path: str | Path) -> FileAnalysis:
        """
        Analyze a single file using tree-sitter queries.

        Args:
            file_path: Path to the file to analyze

        Returns:
            FileAnalysis object with extracted information
        """
        file_path = Path(file_path)

        # Detect language first (from extension)
        language = self.detect_language(file_path)

        if not file_path.exists():
            return FileAnalysis(
                file_path=str(file_path),
                language=language,
                definitions=[],
                references=[],
                imports=[],
                errors=[f"Error reading file: File not found: {file_path}"],
            )

        if language == "unknown":
            return FileAnalysis(
                file_path=str(file_path),
                language=language,
                definitions=[],
                references=[],
                imports=[],
                errors=[f"Unsupported language for file: {file_path}"],
            )

        # Read file content
        try:
            content = file_path.read_text(encoding="utf-8")
        except Exception as e:
            return FileAnalysis(
                file_path=str(file_path),
                language=language,
                definitions=[],
                references=[],
                imports=[],
                errors=[f"Error reading file: {e}"],
            )

        # Analyze with tree-sitter or fallback to regex
        if TREE_SITTER_AVAILABLE:
            return self._analyze_with_tree_sitter(file_path, content, language)
        else:
            return self._analyze_with_regex(file_path, content, language)

    def _analyze_with_tree_sitter(
        self, file_path: Path, content: str, language: str
    ) -> FileAnalysis:
        """Analyze using tree-sitter queries."""
        definitions = []
        references = []
        imports = []
        errors = []

        try:
            # Get parser for language
            parser = self._get_parser(language)
            if not parser:
                return self._analyze_with_regex(file_path, content, language)

            # Parse the code
            tree = parser.parse(bytes(content, "utf-8"))

            # Load and run queries
            query_scm = self._load_query(language)
            if not query_scm:
                return self._analyze_with_regex(file_path, content, language)

            # Get language object and create query
            lang_obj = get_language(language)
            query = lang_obj.query(query_scm)

            # Get all captures
            captures = query.captures(tree.root_node)

            # Normalize captures format (TSL pack returns dict, standard returns list)
            if isinstance(captures, dict):
                # TSL pack format: {tag: [nodes]}
                all_nodes = []
                for tag, nodes in captures.items():
                    all_nodes += [(node, tag) for node in nodes]
            else:
                # Standard format: [(node, tag), ...]
                all_nodes = list(captures)

            # Process captures
            lines = content.splitlines()
            for node, tag in all_nodes:
                # Extract element details
                start_point = node.start_point
                line = start_point[0] + 1  # Convert to 1-based
                column = start_point[1]

                # Get node text
                node_text = (
                    node.text.decode("utf-8")
                    if hasattr(node, "text")
                    else content[node.start_byte : node.end_byte]
                )

                # Extract name from captures
                name = None
                if tag.startswith("name."):
                    name = node_text
                    # Clean up string literals for imports (e.g., Go imports)
                    if tag == "name.import" and name.startswith('"') and name.endswith('"'):
                        name = name[1:-1]  # Remove quotes
                elif tag in ["import", "definition.variable", "definition.constant"]:
                    # For these, the node itself is the name
                    name = node_text.strip()
                else:
                    # Skip non-name captures
                    continue

                # Skip empty names
                if not name:
                    continue

                # Determine element type
                kind = self._tag_to_kind(tag)

                # For some languages, we need to be smarter about the kind
                # For example, Rust uses definition.class for both structs and enums
                if language == "rust" and tag.endswith("definition.class"):
                    # Look at the parent node type to determine the actual kind
                    parent = node.parent
                    if parent and hasattr(parent, "type"):
                        if parent.type == "struct_item":
                            kind = DefinitionKind.STRUCT
                        elif parent.type == "enum_item":
                            kind = DefinitionKind.ENUM
                        elif parent.type == "trait_item":
                            kind = DefinitionKind.TRAIT

                is_definition = tag.startswith("definition.") or tag.startswith("name.definition.")
                is_import = tag == "import" or tag == "name.import"
                is_reference = tag.startswith("reference.") or tag.startswith("name.reference.")

                # Get full line text for context
                full_text = lines[start_point[0]] if start_point[0] < len(lines) else ""

                element = CodeElement(
                    name=name,
                    kind=kind,
                    line=line,
                    column=column,
                    file_path=str(file_path),
                    language=language,
                    is_definition=is_definition,
                    full_text=full_text,
                )

                if is_import:
                    imports.append(element)
                elif is_definition:
                    definitions.append(element)
                elif is_reference:
                    element.is_definition = False
                    references.append(element)

        except Exception as e:
            errors.append(f"Tree-sitter analysis error: {e}")
            logger.error(f"Failed to analyze {file_path} with tree-sitter: {e}")
            # Fallback to regex
            return self._analyze_with_regex(file_path, content, language)

        return FileAnalysis(
            file_path=str(file_path),
            language=language,
            definitions=definitions,
            references=references,
            imports=imports,
            errors=errors,
        )

    def _get_parser(self, language: str):
        """Get or create parser for language."""
        if language in self._parser_cache:
            return self._parser_cache[language]

        try:
            parser = get_parser(language)
            self._parser_cache[language] = parser
            return parser
        except Exception as e:
            logger.debug(f"Could not get parser for {language}: {e}")
            return None

    def _load_query(self, language: str) -> str | None:
        """Load query file for language."""
        if language in self._query_cache:
            return self._query_cache[language]

        query_file = self.query_dir / f"{language}-tags.scm"
        if not query_file.exists():
            logger.debug(f"No query file found for {language}")
            return None

        try:
            query_scm = query_file.read_text(encoding="utf-8")
            self._query_cache[language] = query_scm
            return query_scm
        except Exception as e:
            logger.error(f"Failed to load query file for {language}: {e}")
            return None

    def _tag_to_kind(self, tag: str) -> DefinitionKind:
        """Convert tag string to DefinitionKind."""
        # Remove name. prefix if present
        if tag.startswith("name."):
            tag = tag[5:]  # Remove "name."

        kind_map = {
            "definition.class": DefinitionKind.CLASS,
            "definition.function": DefinitionKind.FUNCTION,
            "definition.method": DefinitionKind.METHOD,
            "definition.variable": DefinitionKind.VARIABLE,
            "definition.constant": DefinitionKind.CONSTANT,
            "definition.interface": DefinitionKind.INTERFACE,
            "definition.module": DefinitionKind.MODULE,
            "definition.struct": DefinitionKind.STRUCT,
            "definition.enum": DefinitionKind.ENUM,
            "definition.trait": DefinitionKind.TRAIT,
            "definition.type": DefinitionKind.TYPE,
            "definition.constructor": DefinitionKind.CONSTRUCTOR,
            "definition.macro": DefinitionKind.MACRO,
            "reference.call": DefinitionKind.FUNCTION,
            "reference.class": DefinitionKind.CLASS,
            "import": DefinitionKind.IMPORT,
            "name.import": DefinitionKind.IMPORT,
        }

        return kind_map.get(tag, DefinitionKind.UNKNOWN)

    def _analyze_with_regex(self, file_path: Path, content: str, language: str) -> FileAnalysis:
        """Fallback regex-based analysis."""
        definitions = []
        references = []
        imports = []
        errors = []

        lines = content.split("\n")

        # Language-specific regex patterns
        patterns = self._get_regex_patterns(language)

        for line_num, line in enumerate(lines, 1):
            # Check for definitions
            for pattern, kind in patterns["definitions"]:
                match = pattern.search(line)
                if match:
                    name = match.group(1) if match.groups() else match.group(0)
                    definitions.append(
                        CodeElement(
                            name=name,
                            kind=kind,
                            line=line_num,
                            column=match.start(),
                            file_path=str(file_path),
                            language=language,
                            is_definition=True,
                            full_text=line,
                        )
                    )

            # Check for imports
            for pattern, kind in patterns["imports"]:
                match = pattern.search(line)
                if match:
                    name = match.group(1) if match.groups() else match.group(0)
                    imports.append(
                        CodeElement(
                            name=name,
                            kind=kind,
                            line=line_num,
                            column=match.start(),
                            file_path=str(file_path),
                            language=language,
                            is_definition=False,
                            full_text=line,
                        )
                    )

        return FileAnalysis(
            file_path=str(file_path),
            language=language,
            definitions=definitions,
            references=references,
            imports=imports,
            errors=errors,
        )

    def _get_regex_patterns(
        self, language: str
    ) -> dict[str, list[tuple[re.Pattern, DefinitionKind]]]:
        """Get regex patterns for fallback analysis."""
        patterns = {
            "python": {
                "definitions": [
                    (re.compile(r"^\s*class\s+(\w+)"), DefinitionKind.CLASS),
                    (re.compile(r"^\s*def\s+(\w+)"), DefinitionKind.FUNCTION),
                    (re.compile(r"^\s*(\w+)\s*="), DefinitionKind.VARIABLE),
                ],
                "imports": [
                    (re.compile(r"^\s*import\s+(\S+)"), DefinitionKind.IMPORT),
                    (re.compile(r"^\s*from\s+(\S+)\s+import"), DefinitionKind.IMPORT),
                ],
            },
            "javascript": {
                "definitions": [
                    (re.compile(r"^\s*class\s+(\w+)"), DefinitionKind.CLASS),
                    (re.compile(r"^\s*function\s+(\w+)"), DefinitionKind.FUNCTION),
                    (re.compile(r"^\s*(?:const|let|var)\s+(\w+)"), DefinitionKind.VARIABLE),
                ],
                "imports": [
                    (re.compile(r'^\s*import\s+.*\s+from\s+[\'"]([^\'"]+)'), DefinitionKind.IMPORT),
                    (
                        re.compile(r'^\s*const\s+.*\s*=\s*require\([\'"]([^\'"]+)'),
                        DefinitionKind.IMPORT,
                    ),
                ],
            },
            "typescript": {
                "definitions": [
                    (re.compile(r"^\s*class\s+(\w+)"), DefinitionKind.CLASS),
                    (re.compile(r"^\s*interface\s+(\w+)"), DefinitionKind.INTERFACE),
                    (re.compile(r"^\s*type\s+(\w+)"), DefinitionKind.TYPE),
                    (re.compile(r"^\s*function\s+(\w+)"), DefinitionKind.FUNCTION),
                    (re.compile(r"^\s*(?:const|let|var)\s+(\w+)"), DefinitionKind.VARIABLE),
                ],
                "imports": [
                    (re.compile(r'^\s*import\s+.*\s+from\s+[\'"]([^\'"]+)'), DefinitionKind.IMPORT),
                ],
            },
        }

        return patterns.get(language, {"definitions": [], "imports": []})

    def detect_language(self, file_path: Path) -> str:
        """
        Detect the programming language of a file.

        Args:
            file_path: Path to the file

        Returns:
            Language name or 'unknown'
        """
        if TREE_SITTER_AVAILABLE and filename_to_lang:
            # Use grep_ast's language detection
            lang = filename_to_lang(str(file_path))
            return lang if lang else "unknown"

        # Fallback to extension-based detection
        suffix = file_path.suffix.lower()
        return self._get_extension_map().get(suffix, "unknown")

    def analyze_directory(
        self,
        directory: str | Path,
        recursive: bool = True,
        file_patterns: list[str] | None = None,
        progress_callback: "callable | None" = None,
    ) -> dict[str, FileAnalysis]:
        """
        Analyze all matching files in a directory.

        Args:
            directory: Directory to analyze
            recursive: Whether to search recursively
            file_patterns: List of glob patterns to match (e.g., ['*.py', '*.js'])
            progress_callback: Optional callback function(current, total, filename) for progress updates

        Returns:
            Dictionary mapping file paths to FileAnalysis objects
        """
        directory = Path(directory)
        results = {}

        if not directory.exists():
            logger.error(f"Directory does not exist: {directory}")
            return results

        # Default patterns if none provided
        if file_patterns is None:
            file_patterns = ["**/*"] if recursive else ["*"]

        # Find all matching files
        files = set()
        for pattern in file_patterns:
            if recursive and not pattern.startswith("**"):
                pattern = "**/" + pattern
            files.update(directory.glob(pattern))

        # Filter to only files with known extensions
        supported_extensions = set(self._get_extension_map().keys())
        files = [f for f in files if f.is_file() and f.suffix.lower() in supported_extensions]
        total_files = len(files)

        # Analyze each file
        for idx, file_path in enumerate(files):
            if progress_callback:
                progress_callback(idx + 1, total_files, file_path.name)

            analysis = self.analyze_file(file_path)
            if analysis.language != "unknown":
                results[str(file_path)] = analysis

        return results

    def get_file_dependencies(self, analysis: FileAnalysis) -> list[str]:
        """
        Extract dependencies (imports) from a file analysis.

        Args:
            analysis: FileAnalysis object

        Returns:
            List of dependency names
        """
        return [imp.name for imp in analysis.imports]

    def find_definition(
        self,
        name: str,
        analyses: str | dict[str, FileAnalysis],
        kind: DefinitionKind | None = None,
    ) -> list[CodeElement]:
        """
        Find all definitions matching a name across analyses.

        Args:
            name: Name to search for
            analyses: Dictionary of file analyses or directory path
            kind: Optional kind filter

        Returns:
            List of matching CodeElement objects
        """
        # Handle both directory path and analyses dict
        if isinstance(analyses, str):
            analyses = self.analyze_directory(analyses)

        matches = []
        for analysis in analyses.values():
            for definition in analysis.definitions:
                if definition.name == name:
                    if kind is None or definition.kind == kind:
                        matches.append(definition)

        return matches

    def get_language_from_path(self, file_path: str | Path) -> str | None:
        """Alias for detect_language for backward compatibility."""
        lang = self.detect_language(Path(file_path))
        return None if lang == "unknown" else lang

    def get_structured_analysis(self, file_path: str | Path) -> dict:
        """
        Get structured analysis results for a file.

        Args:
            file_path: Path to analyze

        Returns:
            Dictionary with structured analysis results
        """
        analysis = self.analyze_file(file_path)

        def element_to_dict(elem: CodeElement) -> dict:
            """Convert CodeElement to dictionary with docstring."""
            result = {
                "name": elem.name,
                "kind": elem.kind.value,
                "line": elem.line,
                "column": elem.column,
                "docstring": elem.docstring,
            }

            # Try to extract docstring if not already set
            if not result["docstring"] and Path(elem.file_path).exists():
                try:
                    lines = Path(elem.file_path).read_text().splitlines()
                    # Look for docstring on the next line after definition
                    if elem.line < len(lines):
                        next_line_idx = elem.line  # elem.line is 1-based, list is 0-based
                        if next_line_idx < len(lines):
                            next_line = lines[next_line_idx].strip()
                            # Check for docstring patterns
                            if next_line.startswith('"""') or next_line.startswith("'''"):
                                # Extract docstring
                                quote = '"""' if next_line.startswith('"""') else "'''"
                                docstring_lines = []
                                for i in range(next_line_idx, len(lines)):
                                    line = lines[i]
                                    docstring_lines.append(line)
                                    if i > next_line_idx and quote in line:
                                        break
                                result["docstring"] = "\n".join(docstring_lines).strip()
                except Exception:
                    pass

            return result

        classes = [
            element_to_dict(d) for d in analysis.definitions if d.kind == DefinitionKind.CLASS
        ]
        functions = [
            element_to_dict(d) for d in analysis.definitions if d.kind == DefinitionKind.FUNCTION
        ]
        methods = [
            element_to_dict(d) for d in analysis.definitions if d.kind == DefinitionKind.METHOD
        ]
        variables = [
            element_to_dict(d) for d in analysis.definitions if d.kind == DefinitionKind.VARIABLE
        ]
        constants = [
            element_to_dict(d) for d in analysis.definitions if d.kind == DefinitionKind.CONSTANT
        ]

        return {
            "file_path": analysis.file_path,
            "language": analysis.language,
            "file_info": {
                "path": analysis.file_path,
                "language": analysis.language,
                "lines": (
                    len(Path(analysis.file_path).read_text().splitlines())
                    if Path(analysis.file_path).exists()
                    else 0
                ),
            },
            "classes": classes,
            "functions": functions,
            "methods": methods,
            "variables": variables,
            "constants": constants,
            "definitions": {
                "classes": classes,
                "functions": functions,
                "methods": methods,
                "variables": variables,
                "constants": constants,
                "other": [
                    element_to_dict(d)
                    for d in analysis.definitions
                    if d.kind
                    not in [
                        DefinitionKind.CLASS,
                        DefinitionKind.FUNCTION,
                        DefinitionKind.METHOD,
                        DefinitionKind.VARIABLE,
                        DefinitionKind.CONSTANT,
                    ]
                ],
            },
            "imports": analysis.imports,
            "references": analysis.references,
            "errors": analysis.errors,
        }

    def get_definitions_summary(self, analyses: dict[str, FileAnalysis]) -> dict[str, int]:
        """
        Get summary counts of definitions by type.

        Args:
            analyses: Dictionary of file analyses

        Returns:
            Dictionary mapping definition types to counts
        """
        summary = {}

        for analysis in analyses.values():
            for definition in analysis.definitions:
                kind_name = definition.kind.value
                summary[kind_name] = summary.get(kind_name, 0) + 1

        return summary

    def get_supported_languages(self) -> list[str]:
        """
        Get list of supported languages.

        Returns:
            List of language names
        """
        # Get languages from query files
        query_languages = []
        if self.query_dir.exists():
            for query_file in self.query_dir.glob("*-tags.scm"):
                lang = query_file.stem.replace("-tags", "")
                query_languages.append(lang)

        # Also include languages from extension map
        extension_langs = set(self._get_extension_map().values())

        # Combine and deduplicate
        all_langs = sorted(set(query_languages) | extension_langs)
        return all_langs

    def get_language_extensions(self, language: str) -> list[str]:
        """
        Get file extensions for a language.

        Args:
            language: Language name

        Returns:
            List of file extensions
        """
        extensions = []
        for ext, lang in self._get_extension_map().items():
            if lang == language:
                extensions.append(ext)
        return extensions

    def _get_extension_map(self) -> dict[str, str]:
        """Get the extension to language mapping."""
        return {
            ".py": "python",
            ".js": "javascript",
            ".jsx": "javascript",
            ".ts": "typescript",
            ".tsx": "typescript",
            ".java": "java",
            ".c": "c",
            ".cpp": "cpp",
            ".cc": "cpp",
            ".cxx": "cpp",
            ".h": "c",
            ".hpp": "cpp",
            ".rs": "rust",
            ".go": "go",
            ".rb": "ruby",
            ".php": "php",
            ".cs": "csharp",
            ".swift": "swift",
            ".kt": "kotlin",
            ".lua": "lua",
            ".r": "r",
            ".R": "r",
            ".m": "matlab",
            ".ml": "ocaml",
            ".mli": "ocaml_interface",
            ".clj": "clojure",
            ".dart": "dart",
            ".elm": "elm",
            ".ex": "elixir",
            ".exs": "elixir",
            ".lisp": "commonlisp",
            ".el": "elisp",
            ".rkt": "racket",
            ".gleam": "gleam",
            ".pony": "pony",
            ".sol": "solidity",
            ".ino": "arduino",
            ".d": "d",
            ".properties": "properties",
            ".rules": "udev",
            ".chatito": "chatito",
            ".sql": "sql",
            ".pls": "sql",
            ".plb": "sql",
            ".pks": "sql",
            ".pkb": "sql",
        }
