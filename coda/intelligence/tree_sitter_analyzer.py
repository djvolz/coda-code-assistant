"""
Tree-sitter analyzer for code structure analysis.

This module provides tree-sitter based code parsing and analysis capabilities,
inspired by aider's approach but simplified for our use case.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple, Union
from dataclasses import dataclass
from enum import Enum
import re

# Try to import tree-sitter, fallback to regex-only mode if not available
try:
    import tree_sitter
    from tree_sitter_languages import get_language, get_parser
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False
    tree_sitter = None
    get_language = None
    get_parser = None

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
    parent_scope: Optional[str] = None
    docstring: Optional[str] = None
    modifiers: List[str] = None
    parameters: List[str] = None
    return_type: Optional[str] = None
    
    def __post_init__(self):
        if self.modifiers is None:
            self.modifiers = []
        if self.parameters is None:
            self.parameters = []
    
    def __str__(self) -> str:
        return f"{self.name} ({self.kind.value})"
    
    def __repr__(self) -> str:
        return (f"CodeElement(name='{self.name}', kind={self.kind}, "
                f"line={self.line}, file='{self.file_path}', "
                f"is_definition={self.is_definition})")


@dataclass
class FileAnalysis:
    """Analysis results for a single file."""
    
    file_path: str
    language: str
    definitions: List[CodeElement]
    references: List[CodeElement]
    imports: List[CodeElement]
    errors: List[str]
    
    def __post_init__(self):
        if self.definitions is None:
            self.definitions = []
        if self.references is None:
            self.references = []
        if self.imports is None:
            self.imports = []
        if self.errors is None:
            self.errors = []


class TreeSitterAnalyzer:
    """
    Tree-sitter based code analyzer.
    
    This class provides functionality to parse code files and extract
    definitions, references, and other structural information.
    """
    
    def __init__(self):
        """Initialize the analyzer."""
        self.supported_languages = {
            'python': ['.py'],
            'javascript': ['.js', '.jsx'],
            'typescript': ['.ts', '.tsx'],
            'rust': ['.rs'],
            'go': ['.go'],
            'java': ['.java'],
            'c': ['.c', '.h'],
            'cpp': ['.cpp', '.cxx', '.cc', '.hpp'],
            'csharp': ['.cs'],
            'ruby': ['.rb'],
            'php': ['.php'],
            'swift': ['.swift'],
            'kotlin': ['.kt'],
            'scala': ['.scala'],
        }
        
        # Tree-sitter language parsers (only if available)
        self.parsers = {}
        self.languages = {}
        
        if TREE_SITTER_AVAILABLE:
            self._initialize_tree_sitter()
        
        # Tree-sitter queries for extracting definitions
        self.queries = {
            'python': """
                (function_definition
                    name: (identifier) @name.definition.function) @definition.function
                (class_definition
                    name: (identifier) @name.definition.class) @definition.class
                (assignment
                    left: (identifier) @name.definition.variable) @definition.variable
                (import_statement
                    name: (dotted_name) @name.reference.module) @import.module
                (import_from_statement
                    module_name: (dotted_name) @name.reference.module) @import.module
                (decorated_definition
                    definition: (function_definition
                        name: (identifier) @name.definition.function)) @definition.function
                (decorated_definition
                    definition: (class_definition
                        name: (identifier) @name.definition.class)) @definition.class
            """,
            'javascript': """
                (function_declaration
                    name: (identifier) @name.definition.function) @definition.function
                (class_declaration
                    name: (identifier) @name.definition.class) @definition.class
                (variable_declaration
                    (variable_declarator
                        name: (identifier) @name.definition.variable)) @definition.variable
                (method_definition
                    name: (property_identifier) @name.definition.method) @definition.method
                (import_statement
                    source: (string) @name.reference.module) @import.module
            """,
            'typescript': """
                (function_declaration
                    name: (identifier) @name.definition.function) @definition.function
                (class_declaration
                    name: (type_identifier) @name.definition.class) @definition.class
                (interface_declaration
                    name: (type_identifier) @name.definition.interface) @definition.interface
                (variable_declaration
                    (variable_declarator
                        name: (identifier) @name.definition.variable)) @definition.variable
                (method_definition
                    name: (property_identifier) @name.definition.method) @definition.method
                (import_statement
                    source: (string) @name.reference.module) @import.module
            """,
            'rust': """
                (function_item
                    name: (identifier) @name.definition.function) @definition.function
                (struct_item
                    name: (type_identifier) @name.definition.struct) @definition.struct
                (enum_item
                    name: (type_identifier) @name.definition.enum) @definition.enum
                (trait_item
                    name: (type_identifier) @name.definition.trait) @definition.trait
                (macro_definition
                    name: (identifier) @name.definition.macro) @definition.macro
                (use_declaration
                    argument: (scoped_identifier) @name.reference.module) @import.module
            """,
            'go': """
                (function_declaration
                    name: (identifier) @name.definition.function) @definition.function
                (type_declaration
                    (type_spec
                        name: (type_identifier) @name.definition.type)) @definition.type
                (var_declaration
                    (var_spec
                        name: (identifier) @name.definition.variable)) @definition.variable
                (import_declaration
                    (import_spec
                        path: (interpreted_string_literal) @name.reference.module)) @import.module
            """,
            'c': """
                (function_definition
                    declarator: (function_declarator
                        declarator: (identifier) @name.definition.function)) @definition.function
                (declaration
                    declarator: (init_declarator
                        declarator: (identifier) @name.definition.variable)) @definition.variable
                (struct_specifier
                    name: (type_identifier) @name.definition.struct) @definition.struct
                (enum_specifier
                    name: (type_identifier) @name.definition.enum) @definition.enum
                (preproc_include
                    path: (string_literal) @name.reference.module) @import.module
                (preproc_include
                    path: (system_lib_string) @name.reference.module) @import.module
            """,
            'cpp': """
                (function_definition
                    declarator: (function_declarator
                        declarator: (identifier) @name.definition.function)) @definition.function
                (class_specifier
                    name: (type_identifier) @name.definition.class) @definition.class
                (struct_specifier
                    name: (type_identifier) @name.definition.struct) @definition.struct
                (enum_specifier
                    name: (type_identifier) @name.definition.enum) @definition.enum
                (namespace_definition
                    name: (identifier) @name.definition.module) @definition.module
                (declaration
                    declarator: (init_declarator
                        declarator: (identifier) @name.definition.variable)) @definition.variable
                (preproc_include
                    path: (string_literal) @name.reference.module) @import.module
                (preproc_include
                    path: (system_lib_string) @name.reference.module) @import.module
            """,
            'java': """
                (class_declaration
                    name: (identifier) @name.definition.class) @definition.class
                (interface_declaration
                    name: (identifier) @name.definition.interface) @definition.interface
                (method_declaration
                    name: (identifier) @name.definition.method) @definition.method
                (constructor_declaration
                    name: (identifier) @name.definition.method) @definition.method
                (field_declaration
                    declarator: (variable_declarator
                        name: (identifier) @name.definition.variable)) @definition.variable
                (import_declaration
                    (scoped_identifier) @name.reference.module) @import.module
                (package_declaration
                    (scoped_identifier) @name.definition.module) @definition.module
            """,
        }
        
        self.language_map = {}
        for lang, extensions in self.supported_languages.items():
            for ext in extensions:
                self.language_map[ext] = lang
        
        # Simple patterns for fallback when tree-sitter is not available
        self.simple_patterns = {
            'python': {
                'function': r'^\s*def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                'class': r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*[:\(]',
                'variable': r'^\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=',
                'import': r'^\s*(?:from\s+\S+\s+)?import\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            },
            'javascript': {
                'function': r'^\s*(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*function|\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*function)',
                'class': r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'variable': r'^\s*(?:var|let|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'import': r'^\s*import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            },
            'typescript': {
                'function': r'^\s*(?:function\s+([a-zA-Z_][a-zA-Z0-9_]*)|([a-zA-Z_][a-zA-Z0-9_]*)\s*:\s*function|\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*function)',
                'class': r'^\s*class\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'interface': r'^\s*interface\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'variable': r'^\s*(?:var|let|const)\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'import': r'^\s*import\s+(?:\{[^}]*\}|\*\s+as\s+\w+|\w+)\s+from\s+[\'"]([^\'"]+)[\'"]',
            },
            'rust': {
                'function': r'^\s*(?:pub\s+)?fn\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                'struct': r'^\s*(?:pub\s+)?struct\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'enum': r'^\s*(?:pub\s+)?enum\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'trait': r'^\s*(?:pub\s+)?trait\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'macro': r'^\s*macro_rules!\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'import': r'^\s*use\s+([a-zA-Z_][a-zA-Z0-9_:]*)',
            },
            'go': {
                'function': r'^\s*func\s+(?:\([^)]*\)\s+)?([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                'struct': r'^\s*type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+struct',
                'interface': r'^\s*type\s+([a-zA-Z_][a-zA-Z0-9_]*)\s+interface',
                'variable': r'^\s*var\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'import': r'^\s*import\s+(?:\(|"([^"]+)"|[\'"]([^\'"]+)[\'"])',
            },
            'java': {
                'class': r'^\s*(?:public\s+)?class\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'interface': r'^\s*(?:public\s+)?interface\s+([a-zA-Z_][a-zA-Z0-9_]*)',
                'method': r'^\s*(?:public|private|protected)?\s*(?:static\s+)?(?:\w+\s+)+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(',
                'import': r'^\s*import\s+([a-zA-Z_][a-zA-Z0-9_.]*)',
            },
        }
    
    def get_language_from_path(self, file_path: Union[str, Path]) -> Optional[str]:
        """
        Determine the programming language from file extension.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Language name or None if not supported
        """
        path = Path(file_path)
        return self.language_map.get(path.suffix.lower())
    
    def _initialize_tree_sitter(self):
        """Initialize tree-sitter parsers for supported languages."""
        if not TREE_SITTER_AVAILABLE:
            return
        
        # Initialize parsers for supported languages
        for language in self.supported_languages.keys():
            try:
                self.languages[language] = get_language(language)
                self.parsers[language] = get_parser(language)
                logger.debug(f"Initialized tree-sitter parser for {language}")
            except Exception as e:
                logger.warning(f"Failed to initialize tree-sitter for {language}: {e}")
                continue
    
    def analyze_file(self, file_path: Union[str, Path]) -> FileAnalysis:
        """
        Analyze a single file and extract code elements.
        
        Args:
            file_path: Path to the file to analyze
            
        Returns:
            FileAnalysis object with extracted elements
        """
        file_path = Path(file_path)
        language = self.get_language_from_path(file_path)
        
        if not language:
            return FileAnalysis(
                file_path=str(file_path),
                language="unknown",
                definitions=[],
                references=[],
                imports=[],
                errors=["Unsupported language"]
            )
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError, UnicodeDecodeError) as e:
            return FileAnalysis(
                file_path=str(file_path),
                language=language,
                definitions=[],
                references=[],
                imports=[],
                errors=[f"Error reading file: {e}"]
            )
        
        # Use tree-sitter if available, otherwise fall back to regex
        if TREE_SITTER_AVAILABLE and language in self.parsers:
            return self._analyze_with_tree_sitter(file_path, content, language)
        else:
            return self._analyze_with_regex(file_path, content, language)
    
    def _analyze_with_tree_sitter(self, file_path: Path, content: str, language: str) -> FileAnalysis:
        """
        Analyze file content using tree-sitter.
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            FileAnalysis object
        """
        definitions = []
        references = []
        imports = []
        errors = []
        
        try:
            parser = self.parsers[language]
            tree = parser.parse(bytes(content, 'utf-8'))
            
            if language in self.queries:
                query_string = self.queries[language]
                lang_obj = self.languages[language]
                query = lang_obj.query(query_string)
                
                captures = query.captures(tree.root_node)
                
                for node, capture_name in captures:
                    node_text = content[node.start_byte:node.end_byte]
                    line_num = node.start_point[0] + 1
                    col_num = node.start_point[1]
                    
                    # Parse capture name to determine element type
                    if capture_name.startswith('name.definition.'):
                        kind_str = capture_name.split('.')[-1]
                        kind = self._string_to_kind(kind_str)
                        
                        element = CodeElement(
                            name=node_text,
                            kind=kind,
                            line=line_num,
                            column=col_num,
                            file_path=str(file_path),
                            language=language,
                            is_definition=True
                        )
                        definitions.append(element)
                        
                    elif capture_name.startswith('name.reference.'):
                        kind_str = capture_name.split('.')[-1]
                        kind = self._string_to_kind(kind_str)
                        
                        element = CodeElement(
                            name=node_text,
                            kind=kind,
                            line=line_num,
                            column=col_num,
                            file_path=str(file_path),
                            language=language,
                            is_definition=False
                        )
                        
                        if kind == DefinitionKind.IMPORT or 'import' in capture_name:
                            imports.append(element)
                        else:
                            references.append(element)
                            
        except Exception as e:
            errors.append(f"Tree-sitter parsing error: {e}")
            logger.error(f"Tree-sitter error in {file_path}: {e}")
            # Fall back to regex parsing
            return self._analyze_with_regex(file_path, content, language)
        
        return FileAnalysis(
            file_path=str(file_path),
            language=language,
            definitions=definitions,
            references=references,
            imports=imports,
            errors=errors
        )
    
    def _analyze_with_regex(self, file_path: Path, content: str, language: str) -> FileAnalysis:
        """
        Analyze file content using regex patterns.
        
        Args:
            file_path: Path to the file
            content: File content
            language: Programming language
            
        Returns:
            FileAnalysis object
        """
        definitions = []
        references = []
        imports = []
        errors = []
        
        if language not in self.simple_patterns:
            errors.append(f"No patterns defined for language: {language}")
            return FileAnalysis(
                file_path=str(file_path),
                language=language,
                definitions=definitions,
                references=references,
                imports=imports,
                errors=errors
            )
        
        patterns = self.simple_patterns[language]
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, 1):
            for kind_str, pattern in patterns.items():
                try:
                    match = re.search(pattern, line)
                    if match:
                        # Extract the name from the first capturing group
                        name = None
                        for group in match.groups():
                            if group:
                                name = group
                                break
                        
                        if name:
                            kind = self._string_to_kind(kind_str)
                            element = CodeElement(
                                name=name,
                                kind=kind,
                                line=line_num,
                                column=match.start(),
                                file_path=str(file_path),
                                language=language,
                                is_definition=True
                            )
                            
                            if kind == DefinitionKind.IMPORT:
                                imports.append(element)
                            else:
                                definitions.append(element)
                                
                except re.error as e:
                    errors.append(f"Regex error in pattern {kind_str}: {e}")
        
        return FileAnalysis(
            file_path=str(file_path),
            language=language,
            definitions=definitions,
            references=references,
            imports=imports,
            errors=errors
        )
    
    def _string_to_kind(self, kind_str: str) -> DefinitionKind:
        """Convert string to DefinitionKind enum."""
        try:
            return DefinitionKind(kind_str)
        except ValueError:
            return DefinitionKind.UNKNOWN
    
    def analyze_directory(self, directory: Union[str, Path], 
                         recursive: bool = True) -> Dict[str, FileAnalysis]:
        """
        Analyze all supported files in a directory.
        
        Args:
            directory: Path to the directory
            recursive: Whether to analyze subdirectories
            
        Returns:
            Dictionary mapping file paths to FileAnalysis objects
        """
        directory = Path(directory)
        results = {}
        
        pattern = "**/*" if recursive else "*"
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and self.get_language_from_path(file_path):
                try:
                    analysis = self.analyze_file(file_path)
                    results[str(file_path)] = analysis
                except Exception as e:
                    logger.error(f"Error analyzing {file_path}: {e}")
                    results[str(file_path)] = FileAnalysis(
                        file_path=str(file_path),
                        language="unknown",
                        definitions=[],
                        references=[],
                        imports=[],
                        errors=[f"Analysis error: {e}"]
                    )
        
        return results
    
    def get_definitions_summary(self, analyses: Dict[str, FileAnalysis]) -> Dict[str, int]:
        """
        Get a summary of definitions by kind.
        
        Args:
            analyses: Dictionary of file analyses
            
        Returns:
            Dictionary with counts by definition kind
        """
        summary = {}
        
        for analysis in analyses.values():
            for definition in analysis.definitions:
                kind = definition.kind.value
                summary[kind] = summary.get(kind, 0) + 1
        
        return summary
    
    def find_definition(self, name: str, analyses: Dict[str, FileAnalysis]) -> List[CodeElement]:
        """
        Find all definitions of a given name.
        
        Args:
            name: Name to search for
            analyses: Dictionary of file analyses
            
        Returns:
            List of CodeElement objects with matching names
        """
        results = []
        
        for analysis in analyses.values():
            for definition in analysis.definitions:
                if definition.name == name:
                    results.append(definition)
        
        return results
    
    def get_file_dependencies(self, analysis: FileAnalysis) -> List[str]:
        """
        Extract file dependencies from imports.
        
        Args:
            analysis: FileAnalysis object
            
        Returns:
            List of imported modules/files
        """
        dependencies = []
        
        for import_element in analysis.imports:
            dependencies.append(import_element.name)
        
        return dependencies
    
    def get_supported_languages(self) -> List[str]:
        """
        Get list of supported programming languages.
        
        Returns:
            List of supported language names
        """
        return list(self.supported_languages.keys())
    
    def get_language_extensions(self, language: str) -> List[str]:
        """
        Get file extensions for a given language.
        
        Args:
            language: Programming language name
            
        Returns:
            List of file extensions
        """
        return self.supported_languages.get(language, [])
    
    def extract_documentation(self, content: str, element: CodeElement) -> Optional[str]:
        """
        Extract documentation/docstring for a code element.
        
        Args:
            content: File content
            element: Code element
            
        Returns:
            Documentation string or None
        """
        lines = content.split('\n')
        
        if element.language == 'python':
            return self._extract_python_docstring(lines, element.line)
        elif element.language in ['javascript', 'typescript']:
            return self._extract_js_doc_comment(lines, element.line)
        elif element.language in ['c', 'cpp']:
            return self._extract_c_doc_comment(lines, element.line)
        elif element.language == 'java':
            return self._extract_javadoc_comment(lines, element.line)
        elif element.language == 'rust':
            return self._extract_rust_doc_comment(lines, element.line)
        
        return None
    
    def _extract_python_docstring(self, lines: List[str], element_line: int) -> Optional[str]:
        """Extract Python docstring."""
        if element_line >= len(lines):
            return None
        
        # Look for docstring in the next few lines
        for i in range(element_line, min(element_line + 5, len(lines))):
            line = lines[i].strip()
            
            # Triple quoted strings
            if '"""' in line or "'''" in line:
                quote = '"""' if '"""' in line else "'''"
                
                # Single line docstring
                if line.count(quote) == 2:
                    return line.strip(quote).strip()
                
                # Multi-line docstring
                docstring_lines = []
                start_line = i
                found_end = False
                
                # First line might have content after opening quotes
                first_content = line.split(quote, 1)
                if len(first_content) > 1:
                    docstring_lines.append(first_content[1])
                
                for j in range(start_line + 1, min(start_line + 20, len(lines))):
                    if j >= len(lines):
                        break
                    
                    doc_line = lines[j]
                    if quote in doc_line:
                        # Found closing quotes
                        end_content = doc_line.split(quote)[0]
                        if end_content.strip():
                            docstring_lines.append(end_content)
                        found_end = True
                        break
                    else:
                        docstring_lines.append(doc_line)
                
                if found_end:
                    return '\n'.join(docstring_lines).strip()
        
        return None
    
    def _extract_js_doc_comment(self, lines: List[str], element_line: int) -> Optional[str]:
        """Extract JavaScript JSDoc comment."""
        # Look backwards for JSDoc comment
        for i in range(element_line - 2, max(0, element_line - 10), -1):
            if i < 0 or i >= len(lines):
                continue
            
            line = lines[i].strip()
            if line.startswith('/**'):
                # Found JSDoc start
                doc_lines = []
                for j in range(i, element_line):
                    if j >= len(lines):
                        break
                    doc_line = lines[j].strip()
                    if doc_line.startswith('*'):
                        doc_line = doc_line[1:].strip()
                    if doc_line.endswith('*/'):
                        doc_line = doc_line[:-2].strip()
                    if doc_line.startswith('/**'):
                        doc_line = doc_line[3:].strip()
                    if doc_line:
                        doc_lines.append(doc_line)
                
                return '\n'.join(doc_lines).strip() if doc_lines else None
        
        return None
    
    def _extract_c_doc_comment(self, lines: List[str], element_line: int) -> Optional[str]:
        """Extract C/C++ documentation comment."""
        # Look backwards for documentation comment
        for i in range(element_line - 2, max(0, element_line - 10), -1):
            if i < 0 or i >= len(lines):
                continue
            
            line = lines[i].strip()
            if line.startswith('/**') or line.startswith('///'):
                # Found doc comment start
                doc_lines = []
                for j in range(i, element_line):
                    if j >= len(lines):
                        break
                    doc_line = lines[j].strip()
                    if doc_line.startswith('/**'):
                        doc_line = doc_line[3:].strip()
                    elif doc_line.startswith('*'):
                        doc_line = doc_line[1:].strip()
                    elif doc_line.startswith('///'):
                        doc_line = doc_line[3:].strip()
                    if doc_line.endswith('*/'):
                        doc_line = doc_line[:-2].strip()
                    if doc_line:
                        doc_lines.append(doc_line)
                
                return '\n'.join(doc_lines).strip() if doc_lines else None
        
        return None
    
    def _extract_javadoc_comment(self, lines: List[str], element_line: int) -> Optional[str]:
        """Extract Java Javadoc comment."""
        return self._extract_js_doc_comment(lines, element_line)  # Same format as JSDoc
    
    def _extract_rust_doc_comment(self, lines: List[str], element_line: int) -> Optional[str]:
        """Extract Rust documentation comment."""
        # Look backwards for /// or //! comments
        doc_lines = []
        for i in range(element_line - 2, max(0, element_line - 20), -1):
            if i < 0 or i >= len(lines):
                continue
            
            line = lines[i].strip()
            if line.startswith('///') or line.startswith('//!'):
                doc_content = line[3:].strip()
                doc_lines.insert(0, doc_content)
            else:
                break
        
        return '\n'.join(doc_lines).strip() if doc_lines else None
    
    def get_structured_analysis(self, file_path: Union[str, Path]) -> Dict:
        """
        Get a structured analysis of a file with hierarchical information.
        
        Args:
            file_path: Path to the file
            
        Returns:
            Structured analysis dictionary
        """
        analysis = self.analyze_file(file_path)
        
        # Organize by scope/hierarchy
        structure = {
            'file_info': {
                'path': analysis.file_path,
                'language': analysis.language,
                'errors': analysis.errors
            },
            'modules': [],
            'classes': [],
            'functions': [],
            'variables': [],
            'imports': []
        }
        
        # Read file content for documentation extraction
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
        except (IOError, OSError, UnicodeDecodeError):
            content = ""
        
        # Process definitions
        for definition in analysis.definitions:
            # Extract documentation
            if content:
                definition.docstring = self.extract_documentation(content, definition)
            
            element_dict = {
                'name': definition.name,
                'line': definition.line,
                'column': definition.column,
                'docstring': definition.docstring,
                'modifiers': definition.modifiers,
                'parameters': definition.parameters,
                'return_type': definition.return_type
            }
            
            if definition.kind == DefinitionKind.MODULE:
                structure['modules'].append(element_dict)
            elif definition.kind == DefinitionKind.CLASS:
                structure['classes'].append(element_dict)
            elif definition.kind in [DefinitionKind.FUNCTION, DefinitionKind.METHOD]:
                structure['functions'].append(element_dict)
            elif definition.kind in [DefinitionKind.VARIABLE, DefinitionKind.CONSTANT]:
                structure['variables'].append(element_dict)
        
        # Process imports
        for import_item in analysis.imports:
            structure['imports'].append({
                'name': import_item.name,
                'line': import_item.line,
                'column': import_item.column
            })
        
        return structure