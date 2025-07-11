"""Test Kotlin language support in tree-sitter analyzer."""

import tempfile
from pathlib import Path

import pytest

from coda.base.search import TreeSitterAnalyzer


class TestKotlinSupport:
    """Test tree-sitter analysis for Kotlin files."""

    def setup_method(self):
        """Set up test environment."""
        self.analyzer = TreeSitterAnalyzer()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_kotlin_language_detection(self):
        """Test that .kt files are detected as Kotlin."""
        test_file = Path(self.temp_dir) / "test.kt"
        test_file.write_text('fun main() { println("Hello") }')

        assert self.analyzer.detect_language(test_file) == "kotlin"

    def test_kotlin_basic_parsing(self):
        """Test basic Kotlin parsing capabilities."""
        kotlin_code = """
package com.example

import java.util.*

data class User(val name: String, val age: Int)

class UserService {
    fun getUser(id: Long): User? {
        return null
    }
}

fun main() {
    println("Hello, Kotlin!")
}
"""
        test_file = Path(self.temp_dir) / "test.kt"
        test_file.write_text(kotlin_code)

        analysis = self.analyzer.analyze_file(test_file)

        assert analysis.language == "kotlin"
        assert len(analysis.imports) > 0
        assert len(analysis.definitions) > 0

        # Check for specific definitions
        class_names = [d.name for d in analysis.definitions if d.kind.value == "class"]
        assert "User" in class_names
        assert "UserService" in class_names

        function_names = [d.name for d in analysis.definitions if d.kind.value == "function"]
        assert "getUser" in function_names
        assert "main" in function_names

    def test_kotlin_object_declaration(self):
        """Test parsing of Kotlin object declarations."""
        kotlin_code = """
object AppConfig {
    const val VERSION = "1.0.0"
    val name = "MyApp"
}

object DatabaseManager {
    fun connect() {
        // Implementation
    }
}
"""
        test_file = Path(self.temp_dir) / "test.kt"
        test_file.write_text(kotlin_code)

        analysis = self.analyzer.analyze_file(test_file)

        # Object declarations should be recognized as classes
        class_names = [d.name for d in analysis.definitions if d.kind.value == "class"]
        assert "AppConfig" in class_names
        assert "DatabaseManager" in class_names

    def test_kotlin_imports(self):
        """Test parsing of Kotlin import statements."""
        kotlin_code = """
package com.example.app

import java.util.*
import kotlin.collections.ArrayList
import kotlinx.coroutines.flow.Flow

class MyClass {
    // Implementation
}
"""
        test_file = Path(self.temp_dir) / "test.kt"
        test_file.write_text(kotlin_code)

        analysis = self.analyzer.analyze_file(test_file)

        import_names = [imp.name for imp in analysis.imports]
        assert "java.util" in import_names
        assert "kotlin.collections.ArrayList" in import_names
        assert "kotlinx.coroutines.flow.Flow" in import_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
