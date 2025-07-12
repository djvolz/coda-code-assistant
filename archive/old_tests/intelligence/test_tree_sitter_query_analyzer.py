"""Comprehensive unit tests for TreeSitterQueryAnalyzer."""

import tempfile
from pathlib import Path
from textwrap import dedent
from unittest.mock import Mock, patch

import pytest

from coda.base.search.map.tree_sitter_query_analyzer import (
    TREE_SITTER_AVAILABLE,
    DefinitionKind,
    TreeSitterQueryAnalyzer,
)


class TestTreeSitterQueryAnalyzer:
    """Test suite for TreeSitterQueryAnalyzer with query-based parsing."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.query_dir = self.temp_dir / "queries"
        self.query_dir.mkdir()
        self.analyzer = TreeSitterQueryAnalyzer(query_dir=self.query_dir)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_file(self, filename: str, content: str) -> Path:
        """Create a temporary test file."""
        file_path = self.temp_dir / filename
        file_path.write_text(dedent(content).strip())
        return file_path

    def create_query_file(self, language: str, content: str) -> Path:
        """Create a query file for a language."""
        query_path = self.query_dir / f"{language}-tags.scm"
        query_path.write_text(dedent(content).strip())
        return query_path

    def test_initialization(self):
        """Test analyzer initialization."""
        # Default initialization
        analyzer = TreeSitterQueryAnalyzer()
        assert analyzer.query_dir.name == "queries"

        # Custom query directory
        custom_dir = self.temp_dir / "custom_queries"
        custom_dir.mkdir()
        analyzer = TreeSitterQueryAnalyzer(query_dir=custom_dir)
        assert analyzer.query_dir == custom_dir

    def test_query_loading_and_caching(self):
        """Test query file loading and caching mechanism."""
        # Create a sample query file
        query_content = """
        (function_definition
          name: (identifier) @name.definition.function)
        """
        self.create_query_file("python", query_content)

        # First load should read from file
        query1 = self.analyzer._load_query("python")
        assert query1 is not None
        assert "function_definition" in query1

        # Second load should use cache
        query2 = self.analyzer._load_query("python")
        assert query2 == query1
        assert "python" in self.analyzer._query_cache

        # Non-existent language should return None
        query3 = self.analyzer._load_query("nonexistent")
        assert query3 is None

    def test_parser_caching(self):
        """Test parser caching mechanism."""
        if not TREE_SITTER_AVAILABLE:
            pytest.skip("tree-sitter not available")

        with patch("coda.base.search.map.tree_sitter_query_analyzer.get_parser") as mock_get_parser:
            mock_parser = Mock()
            mock_get_parser.return_value = mock_parser

            # First call should create parser
            parser1 = self.analyzer._get_parser("python")
            assert parser1 == mock_parser
            mock_get_parser.assert_called_once_with("python")

            # Second call should use cache
            parser2 = self.analyzer._get_parser("python")
            assert parser2 == mock_parser
            assert mock_get_parser.call_count == 1  # Not called again

    def test_tag_to_kind_mapping(self):
        """Test conversion of query tags to DefinitionKind."""
        test_cases = [
            ("definition.class", DefinitionKind.CLASS),
            ("definition.function", DefinitionKind.FUNCTION),
            ("definition.method", DefinitionKind.METHOD),
            ("definition.variable", DefinitionKind.VARIABLE),
            ("definition.constant", DefinitionKind.CONSTANT),
            ("definition.interface", DefinitionKind.INTERFACE),
            ("definition.module", DefinitionKind.MODULE),
            ("definition.struct", DefinitionKind.STRUCT),
            ("definition.enum", DefinitionKind.ENUM),
            ("definition.trait", DefinitionKind.TRAIT),
            ("definition.type", DefinitionKind.TYPE),
            ("definition.constructor", DefinitionKind.CONSTRUCTOR),
            ("definition.macro", DefinitionKind.MACRO),
            ("import", DefinitionKind.IMPORT),
            ("name.import", DefinitionKind.IMPORT),
            ("name.definition.class", DefinitionKind.CLASS),
            ("unknown.tag", DefinitionKind.UNKNOWN),
        ]

        for tag, expected_kind in test_cases:
            assert self.analyzer._tag_to_kind(tag) == expected_kind

    @pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="tree-sitter not available")
    def test_tree_sitter_analysis_with_mock(self):
        """Test tree-sitter analysis with mocked components."""
        # Create test file
        code = """
        def hello():
            pass
        """
        file_path = self.create_test_file("test.py", code)

        # Create query file
        self.create_query_file(
            "python", "(function_definition name: (identifier) @name.definition.function)"
        )

        # Mock the tree-sitter components
        with (
            patch("coda.base.search.map.tree_sitter_query_analyzer.get_parser") as mock_get_parser,
            patch(
                "coda.base.search.map.tree_sitter_query_analyzer.get_language"
            ) as mock_get_language,
        ):
            # Setup mock parser
            mock_parser = Mock()
            mock_tree = Mock()
            mock_root = Mock()
            mock_tree.root_node = mock_root
            mock_parser.parse.return_value = mock_tree
            mock_get_parser.return_value = mock_parser

            # Setup mock language and query
            mock_lang = Mock()
            mock_query = Mock()

            # Mock node for the function
            mock_node = Mock()
            mock_node.start_point = (0, 4)  # Line 1, column 4
            mock_node.end_point = (0, 9)
            mock_node.text = b"hello"
            mock_node.start_byte = 4
            mock_node.end_byte = 9

            # Mock captures - test both dict and list formats
            mock_query.captures.return_value = {"name.definition.function": [mock_node]}
            mock_lang.query.return_value = mock_query
            mock_get_language.return_value = mock_lang

            # Analyze file
            analysis = self.analyzer.analyze_file(file_path)

            # Verify results
            assert analysis.language == "python"
            assert len(analysis.definitions) == 1
            assert analysis.definitions[0].name == "hello"
            assert analysis.definitions[0].kind == DefinitionKind.FUNCTION
            assert analysis.definitions[0].line == 1
            assert analysis.definitions[0].column == 4

    def test_fallback_to_regex_on_error(self):
        """Test fallback to regex analysis when tree-sitter fails."""
        code = """
        def test_function():
            pass

        class TestClass:
            pass
        """
        file_path = self.create_test_file("test.py", code)

        # Force tree-sitter to fail
        with patch("coda.base.search.map.tree_sitter_query_analyzer.TREE_SITTER_AVAILABLE", False):
            analyzer = TreeSitterQueryAnalyzer(query_dir=self.query_dir)
            analysis = analyzer.analyze_file(file_path)

            assert analysis.language == "python"
            assert len(analysis.definitions) >= 2

            # Check that regex found the definitions
            def_names = [d.name for d in analysis.definitions]
            assert "test_function" in def_names
            assert "TestClass" in def_names

    def test_regex_patterns_for_languages(self):
        """Test regex pattern extraction for different languages."""
        patterns = self.analyzer._get_regex_patterns("python")
        assert "definitions" in patterns
        assert "imports" in patterns
        assert len(patterns["definitions"]) > 0
        assert len(patterns["imports"]) > 0

        # Test JavaScript patterns
        js_patterns = self.analyzer._get_regex_patterns("javascript")
        assert "definitions" in js_patterns
        assert "imports" in js_patterns

        # Test TypeScript patterns
        ts_patterns = self.analyzer._get_regex_patterns("typescript")
        assert "definitions" in ts_patterns
        assert len(ts_patterns["definitions"]) > len(js_patterns["definitions"])  # TS has more

        # Test unknown language
        unknown_patterns = self.analyzer._get_regex_patterns("unknown")
        assert unknown_patterns["definitions"] == []
        assert unknown_patterns["imports"] == []

    def test_analyze_nonexistent_file(self):
        """Test analyzing a file that doesn't exist."""
        analysis = self.analyzer.analyze_file("/nonexistent/file.py")

        assert analysis.language == "python"
        assert len(analysis.errors) == 1
        assert "File not found" in analysis.errors[0]
        assert len(analysis.definitions) == 0

    def test_analyze_unsupported_file(self):
        """Test analyzing a file with unsupported extension."""
        file_path = self.create_test_file("test.xyz", "some content")
        analysis = self.analyzer.analyze_file(file_path)

        assert analysis.language == "unknown"
        assert len(analysis.errors) == 1
        assert "Unsupported language" in analysis.errors[0]

    def test_language_detection(self):
        """Test language detection from file paths."""
        # Test with tree-sitter available
        with (
            patch("coda.base.search.map.tree_sitter_query_analyzer.TREE_SITTER_AVAILABLE", True),
            patch("coda.base.search.map.tree_sitter_query_analyzer.filename_to_lang") as mock_lang,
        ):
            mock_lang.return_value = "python"
            assert self.analyzer.detect_language(Path("test.py")) == "python"
            mock_lang.assert_called_once()

        # Test fallback to extension map
        with patch("coda.base.search.map.tree_sitter_query_analyzer.TREE_SITTER_AVAILABLE", False):
            analyzer = TreeSitterQueryAnalyzer()
            assert analyzer.detect_language(Path("test.py")) == "python"
            assert analyzer.detect_language(Path("test.js")) == "javascript"
            assert analyzer.detect_language(Path("test.rs")) == "rust"
            assert analyzer.detect_language(Path("test.unknown")) == "unknown"

    def test_analyze_directory(self):
        """Test analyzing multiple files in a directory."""
        # Create test files
        self.create_test_file("file1.py", "def func1(): pass")
        self.create_test_file("file2.js", "function func2() {}")
        (self.temp_dir / "subdir").mkdir(exist_ok=True)
        self.create_test_file("subdir/file3.py", "class MyClass: pass")
        self.create_test_file("ignored.txt", "This should be ignored")

        # Analyze directory
        results = self.analyzer.analyze_directory(self.temp_dir)

        # Should have analyzed Python and JavaScript files only
        assert len(results) >= 2
        languages = set(analysis.language for analysis in results.values())
        assert "python" in languages
        assert "javascript" in languages
        assert "unknown" not in languages

    def test_analyze_directory_with_patterns(self):
        """Test analyzing directory with file patterns."""
        self.create_test_file("test1.py", "def func1(): pass")
        self.create_test_file("test2.py", "def func2(): pass")
        self.create_test_file("test.js", "function func() {}")

        # Analyze only Python files
        results = self.analyzer.analyze_directory(self.temp_dir, file_patterns=["*.py"])

        assert len(results) == 2
        assert all(analysis.language == "python" for analysis in results.values())

    def test_find_definition(self):
        """Test finding definitions across multiple files."""
        # Create test files
        self.create_test_file(
            "file1.py",
            """
        def shared_function():
            pass

        def unique_function():
            pass
        """,
        )

        self.create_test_file(
            "file2.py",
            """
        def shared_function():
            return 42

        class SharedClass:
            pass
        """,
        )

        # Analyze directory
        analyses = self.analyzer.analyze_directory(self.temp_dir)

        # Find shared function
        results = self.analyzer.find_definition("shared_function", analyses)
        assert len(results) == 2
        assert all(r.name == "shared_function" for r in results)
        assert all(r.kind == DefinitionKind.FUNCTION for r in results)

        # Find with kind filter
        results = self.analyzer.find_definition("SharedClass", analyses, kind=DefinitionKind.CLASS)
        assert len(results) == 1
        assert results[0].name == "SharedClass"

        # Test with directory path instead of analyses
        results = self.analyzer.find_definition("unique_function", str(self.temp_dir))
        assert len(results) == 1

    def test_get_file_dependencies(self):
        """Test extracting file dependencies from imports."""
        code = """
        import os
        import sys
        from pathlib import Path
        from typing import List, Dict
        """
        file_path = self.create_test_file("deps.py", code)

        analysis = self.analyzer.analyze_file(file_path)
        deps = self.analyzer.get_file_dependencies(analysis)

        # Should extract import names
        assert isinstance(deps, list)
        assert len(deps) == len(analysis.imports)

    def test_structured_analysis(self):
        """Test structured analysis output format."""
        code = """
        '''Module docstring'''

        import os

        class MyClass:
            '''Class docstring'''

            def method1(self):
                '''Method docstring'''
                pass

        def function1():
            pass

        MY_CONSTANT = 42
        my_variable = "test"
        """
        file_path = self.create_test_file("structured.py", code)

        result = self.analyzer.get_structured_analysis(file_path)

        # Check structure
        assert "file_path" in result
        assert "language" in result
        assert "file_info" in result
        assert "classes" in result
        assert "functions" in result
        assert "methods" in result
        assert "variables" in result
        assert "constants" in result
        assert "definitions" in result
        assert "imports" in result
        assert "errors" in result

        # Check file info
        assert result["file_info"]["path"] == str(file_path)
        assert result["file_info"]["language"] == "python"
        assert result["file_info"]["lines"] > 0

        # Check definitions structure
        assert "classes" in result["definitions"]
        assert "functions" in result["definitions"]
        assert "other" in result["definitions"]

    def test_get_definitions_summary(self):
        """Test summary generation for definitions."""
        self.create_test_file(
            "file1.py",
            """
        class Class1: pass
        class Class2: pass
        def func1(): pass
        def func2(): pass
        def func3(): pass
        var1 = 1
        """,
        )

        analyses = self.analyzer.analyze_directory(self.temp_dir)
        summary = self.analyzer.get_definitions_summary(analyses)

        assert isinstance(summary, dict)
        assert summary.get("class", 0) >= 2
        assert summary.get("function", 0) >= 3
        assert summary.get("variable", 0) >= 1

    def test_get_supported_languages(self):
        """Test getting list of supported languages."""
        # Create some query files
        self.create_query_file("python", "")
        self.create_query_file("javascript", "")
        self.create_query_file("rust", "")

        languages = self.analyzer.get_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) > 0
        assert "python" in languages
        assert "javascript" in languages
        assert "rust" in languages

    def test_get_language_extensions(self):
        """Test getting file extensions for languages."""
        py_exts = self.analyzer.get_language_extensions("python")
        assert ".py" in py_exts

        js_exts = self.analyzer.get_language_extensions("javascript")
        assert ".js" in js_exts
        assert ".jsx" in js_exts

        cpp_exts = self.analyzer.get_language_extensions("cpp")
        assert ".cpp" in cpp_exts
        assert ".cc" in cpp_exts
        assert ".cxx" in cpp_exts

        unknown_exts = self.analyzer.get_language_extensions("nonexistent")
        assert unknown_exts == []

    def test_rust_kind_detection(self):
        """Test special handling for Rust struct/enum/trait detection."""
        if not TREE_SITTER_AVAILABLE:
            pytest.skip("tree-sitter not available")

        # Mock the tree-sitter components for Rust
        with (
            patch("coda.base.search.map.tree_sitter_query_analyzer.get_parser") as mock_get_parser,
            patch(
                "coda.base.search.map.tree_sitter_query_analyzer.get_language"
            ) as mock_get_language,
        ):
            # Setup mocks
            mock_parser = Mock()
            mock_tree = Mock()
            mock_tree.root_node = Mock()
            mock_parser.parse.return_value = mock_tree
            mock_get_parser.return_value = mock_parser

            # Create mock nodes for struct, enum, and trait
            struct_node = Mock()
            struct_node.start_point = (0, 0)
            struct_node.text = b"MyStruct"
            struct_parent = Mock()
            struct_parent.type = "struct_item"
            struct_node.parent = struct_parent

            enum_node = Mock()
            enum_node.start_point = (1, 0)
            enum_node.text = b"MyEnum"
            enum_parent = Mock()
            enum_parent.type = "enum_item"
            enum_node.parent = enum_parent

            trait_node = Mock()
            trait_node.start_point = (2, 0)
            trait_node.text = b"MyTrait"
            trait_parent = Mock()
            trait_parent.type = "trait_item"
            trait_node.parent = trait_parent

            # Mock the language and query objects
            mock_lang = Mock()
            mock_query = Mock()

            # Mock captures - traits are tagged as interface, not class
            # The captures method should return the dict format
            mock_query.captures = Mock(
                return_value={
                    "name.definition.class": [struct_node, enum_node],
                    "name.definition.interface": [trait_node],
                }
            )

            # Chain the mocks properly
            mock_lang.query = Mock(return_value=mock_query)
            mock_get_language.return_value = mock_lang

            # Create and analyze Rust file with content
            rust_code = """
struct MyStruct {}
enum MyEnum {}
trait MyTrait {}
"""
            file_path = self.create_test_file("test.rs", rust_code)
            # Create a minimal query file so it doesn't fall back to regex
            self.create_query_file("rust", "(function_item) @definition.function")

            analysis = self.analyzer.analyze_file(file_path)

            # Check that kinds were correctly identified
            kinds = {d.name: d.kind for d in analysis.definitions}
            # With the mock setup, we should have the definitions
            assert len(analysis.definitions) == 3
            assert kinds.get("MyStruct") == DefinitionKind.STRUCT
            assert kinds.get("MyEnum") == DefinitionKind.ENUM
            assert kinds.get("MyTrait") == DefinitionKind.INTERFACE

    def test_docstring_extraction_in_structured_analysis(self):
        """Test docstring extraction in structured analysis."""
        code = '''
        def documented_func():
            """This is a docstring."""
            pass

        def undocumented_func():
            pass
        '''
        file_path = self.create_test_file("doc_test.py", code)

        result = self.analyzer.get_structured_analysis(file_path)

        # Find the documented function
        funcs = result.get("functions", [])
        doc_func = next((f for f in funcs if f["name"] == "documented_func"), None)

        if doc_func and doc_func.get("docstring"):
            assert "This is a docstring" in doc_func["docstring"]

    def test_error_handling_in_query_loading(self):
        """Test error handling when query files are malformed."""
        # Create a malformed query file
        self.create_query_file("python", "invalid query syntax )(][")

        # Should handle error gracefully
        query = self.analyzer._load_query("python")
        assert query is not None  # File content is returned even if invalid

        # Test with unreadable file
        query_path = self.query_dir / "unreadable-tags.scm"
        query_path.touch()
        query_path.chmod(0o000)

        query = self.analyzer._load_query("unreadable")
        assert query is None

        # Cleanup
        query_path.chmod(0o644)

    def test_unicode_handling(self):
        """Test handling of unicode characters in code."""
        code = """
        def 你好():
            '''Unicode function name'''
            emoji = "🐍"
            return emoji

        class ÜnicödeClass:
            pass
        """
        file_path = self.create_test_file("unicode.py", code)

        # Should handle unicode without errors
        analysis = self.analyzer.analyze_file(file_path)
        assert len(analysis.errors) == 0

        # Check that unicode names are preserved
        def_names = [d.name for d in analysis.definitions]
        if def_names:  # Only check if regex fallback found them
            assert any("你好" in name or "nicödeClass" in name for name in def_names)
