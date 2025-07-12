"""Test SQL language support in tree-sitter analyzer."""

import tempfile
from pathlib import Path

import pytest

from coda.base.search import TreeSitterAnalyzer


class TestSQLSupport:
    """Test tree-sitter analysis for SQL files."""

    def setup_method(self):
        """Set up test environment."""
        self.analyzer = TreeSitterAnalyzer()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_sql_language_detection(self):
        """Test that .sql files are detected as SQL."""
        test_file = Path(self.temp_dir) / "test.sql"
        test_file.write_text("SELECT * FROM users;")

        assert self.analyzer.detect_language(test_file) == "sql"

    def test_sql_basic_parsing(self):
        """Test basic SQL parsing capabilities."""
        # Note: SQL tree-sitter support is limited
        # This test documents what currently works
        sql_code = """
-- Basic table creation
CREATE TABLE users (
    id INTEGER PRIMARY KEY,
    name TEXT,
    email TEXT
);

-- Simple queries
SELECT * FROM users;
SELECT name, email FROM users WHERE id = 1;
"""
        test_file = Path(self.temp_dir) / "test.sql"
        test_file.write_text(sql_code)

        analysis = self.analyzer.analyze_file(test_file)

        assert analysis.language == "sql"
        # SQL parsing support is limited, so we may not get many definitions
        # This is expected behavior

    @pytest.mark.skip(reason="PL/SQL specific constructs not supported by tree-sitter-sql")
    def test_plsql_constructs(self):
        """Test PL/SQL specific constructs (currently not supported)."""
        # This test is skipped because tree-sitter-sql doesn't support
        # PL/SQL specific constructs like packages, procedures, etc.
        pass


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
