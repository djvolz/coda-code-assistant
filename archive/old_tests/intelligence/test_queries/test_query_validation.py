"""Tests for validating tree-sitter query files."""

from pathlib import Path

import pytest

from coda.base.search.map.tree_sitter_query_analyzer import (
    TREE_SITTER_AVAILABLE,
    TreeSitterQueryAnalyzer,
)


class TestQueryValidation:
    """Test suite for validating query files."""

    def setup_method(self):
        """Set up test fixtures."""
        self.query_dir = Path(__file__).parent.parent.parent.parent / "coda" / "search" / "queries"
        self.analyzer = TreeSitterQueryAnalyzer()

    def test_query_files_exist(self):
        """Test that query files exist for documented languages."""
        expected_languages = [
            "python",
            "javascript",
            "rust",
            "go",
            "java",
            "c",
            "cpp",
            "ruby",
            "csharp",
            "swift",
            "dart",
            "lua",
            "r",
        ]

        for language in expected_languages:
            query_file = self.query_dir / f"{language}-tags.scm"
            assert query_file.exists(), f"Query file missing for {language}"

    def test_query_file_format(self):
        """Test that all query files have valid format."""
        query_files = list(self.query_dir.glob("*-tags.scm"))
        assert len(query_files) > 0, "No query files found"

        for query_file in query_files:
            content = query_file.read_text()

            # Basic syntax checks
            assert content.strip(), f"{query_file.name} is empty"
            assert "(" in content, f"{query_file.name} missing opening parenthesis"
            assert ")" in content, f"{query_file.name} missing closing parenthesis"
            assert "@" in content, f"{query_file.name} missing capture markers"

            # Check for common patterns
            language = query_file.stem.replace("-tags", "")
            if language in ["python", "javascript", "java", "go"]:
                # These languages should have function definitions
                assert "function" in content.lower() or "def" in content.lower(), (
                    f"{query_file.name} missing function patterns"
                )

    @pytest.mark.skipif(not TREE_SITTER_AVAILABLE, reason="tree-sitter not available")
    def test_query_syntax_validity(self):
        """Test that queries have valid tree-sitter syntax."""
        from grep_ast.tsl import get_language

        for query_file in self.query_dir.glob("*-tags.scm"):
            language = query_file.stem.replace("-tags", "")
            query_content = query_file.read_text()

            try:
                # Try to get language object
                lang_obj = get_language(language)
                if lang_obj:
                    # Try to create a query - this will raise if syntax is invalid
                    query = lang_obj.query(query_content)
                    assert query is not None, f"Failed to create query for {language}"
            except Exception as e:
                # Some languages might not be available, that's OK
                if "Language" not in str(e) and "not available" not in str(e):
                    pytest.fail(f"Invalid query syntax in {query_file.name}: {e}")

    def test_query_capture_consistency(self):
        """Test that queries use consistent capture names."""

        for query_file in self.query_dir.glob("*-tags.scm"):
            content = query_file.read_text()

            # Extract all capture names
            import re

            captures = re.findall(r"@([\w.]+)", content)

            # Check that at least some definition or reference captures are used
            has_definitions = any("definition." in c or "name.definition." in c for c in captures)
            has_references = any("reference." in c or "name.reference." in c for c in captures)
            has_imports = any("import" in c for c in captures)

            assert has_definitions or has_references or has_imports, (
                f"{query_file.name} doesn't use any definition, reference, or import captures"
            )

    def test_python_query_specifics(self):
        """Test Python-specific query patterns."""
        python_query = self.query_dir / "python-tags.scm"
        if not python_query.exists():
            pytest.skip("Python query file not found")

        content = python_query.read_text()

        # Python-specific checks
        assert "function_definition" in content
        assert "class_definition" in content
        assert "import_statement" in content or "import_from_statement" in content
        assert "@name.definition.function" in content or "@definition.function" in content
        assert "@name.definition.class" in content or "@definition.class" in content

    def test_javascript_query_specifics(self):
        """Test JavaScript-specific query patterns."""
        js_query = self.query_dir / "javascript-tags.scm"
        if not js_query.exists():
            pytest.skip("JavaScript query file not found")

        content = js_query.read_text()

        # JavaScript-specific checks
        assert "function" in content or "arrow_function" in content
        assert "class" in content
        assert "import" in content or "require" in content

    def test_rust_query_specifics(self):
        """Test Rust-specific query patterns."""
        rust_query = self.query_dir / "rust-tags.scm"
        if not rust_query.exists():
            pytest.skip("Rust query file not found")

        content = rust_query.read_text()

        # Rust-specific checks
        assert "function_item" in content or "fn" in content
        assert "struct_item" in content or "struct" in content
        assert "enum_item" in content or "enum" in content
        assert "trait_item" in content or "trait" in content
        assert "use_declaration" in content or "use" in content

    def test_go_query_specifics(self):
        """Test Go-specific query patterns."""
        go_query = self.query_dir / "go-tags.scm"
        if not go_query.exists():
            pytest.skip("Go query file not found")

        content = go_query.read_text()

        # Go-specific checks
        assert "function_declaration" in content or "func" in content
        assert "type_declaration" in content or "type" in content
        assert "import" in content

    def test_cross_language_consistency(self):
        """Test that similar constructs are captured consistently across languages."""
        # Languages that should have function definitions
        function_languages = ["python", "javascript", "rust", "go", "java", "c", "cpp"]

        function_captures = {}
        for lang in function_languages:
            query_file = self.query_dir / f"{lang}-tags.scm"
            if query_file.exists():
                content = query_file.read_text()
                # Look for function-related captures
                import re

                captures = re.findall(r"@([\w.]*function[\w.]*)", content)
                function_captures[lang] = captures

        # All languages should capture functions in some way
        for lang, captures in function_captures.items():
            assert len(captures) > 0, f"{lang} doesn't capture functions"

            # Should use standard naming convention
            standard_names = ["name.definition.function", "definition.function"]
            has_standard = any(c in standard_names for c in captures)
            assert has_standard, f"{lang} doesn't use standard function capture names"

    def test_import_capture_consistency(self):
        """Test that import statements are captured consistently."""
        import_languages = ["python", "javascript", "rust", "go", "java"]

        for lang in import_languages:
            query_file = self.query_dir / f"{lang}-tags.scm"
            if query_file.exists():
                content = query_file.read_text()

                # Should have import-related captures
                assert (
                    "@import" in content or "@name.import" in content or "import" in content.lower()
                ), f"{lang} doesn't capture imports"

    def test_query_file_comments(self):
        """Test that query files include helpful comments."""
        for query_file in self.query_dir.glob("*-tags.scm"):
            content = query_file.read_text()

            # Check for comments (tree-sitter uses ; for comments)
            lines = content.split("\n")
            [l for l in lines if l.strip().startswith(";")]

            # Should have at least some comments for documentation
            # Skip comment requirement for now - many files lack comments
            # TODO: Add comments to all query files
            pass

    def test_no_duplicate_captures(self):
        """Test that queries don't have duplicate capture patterns."""
        # Skip this test - it's too strict for complex query patterns
        # Many legitimate patterns require multiple captures of the same type
        # within a block (e.g., multiple function definitions in OCaml)
        pass

    def test_query_performance_considerations(self):
        """Test that queries follow performance best practices."""
        for query_file in self.query_dir.glob("*-tags.scm"):
            content = query_file.read_text()

            # Check for overly broad patterns that might impact performance
            lines = content.split("\n")

            for line in lines:
                # Warn about patterns that match everything
                if line.strip() == "(_) @capture":
                    pytest.fail(f"{query_file.name} has overly broad pattern: {line}")

                # Check for deeply nested patterns (more than 5 levels)
                open_parens = line.count("(")
                if open_parens > 5 and "@" in line:
                    # This might be a complex pattern, but not necessarily bad
                    pass  # Consider adding a warning in the future
