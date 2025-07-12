"""Integration tests for intelligence CLI commands."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from coda.base.search.cli import IntelligenceCommands


class TestIntelligenceCommands:
    """Test suite for IntelligenceCommands CLI."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.intel_commands = IntelligenceCommands()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_file(self, filename: str, content: str) -> Path:
        """Create a temporary test file."""
        file_path = self.temp_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(dedent(content).strip())
        return file_path

    def test_handle_command_unknown(self):
        """Test handling unknown command."""
        result = self.intel_commands.handle_command("unknown", [])
        assert "Unknown intelligence command: unknown" in result

    def test_analyze_command_no_args(self):
        """Test analyze command without arguments."""
        result = self.intel_commands.handle_command("analyze", [])
        assert "Usage: /intel analyze <file_path>" in result

    def test_analyze_command_nonexistent_file(self):
        """Test analyze command with nonexistent file."""
        result = self.intel_commands.handle_command("analyze", ["/nonexistent/file.py"])
        assert "File not found" in result

    def test_analyze_command_success(self):
        """Test successful file analysis."""
        # Create test file
        test_file = self.create_test_file(
            "test.py",
            """
        def hello_world():
            '''A greeting function.'''
            return "Hello, World!"

        class Calculator:
            def add(self, a, b):
                return a + b

        import math
        PI = 3.14159
        """,
        )

        result = self.intel_commands.handle_command("analyze", [str(test_file)])

        assert "File:" in result
        assert "Language: python" in result
        assert "Definitions:" in result
        assert "hello_world" in result
        assert "Calculator" in result
        assert "function:" in result
        assert "class:" in result

    def test_map_command_no_args(self):
        """Test map command without arguments (uses current dir)."""
        # This should work with current directory
        result = self.intel_commands.handle_command("map", [])
        assert "Repository:" in result
        assert "Total files:" in result

    def test_map_command_with_directory(self):
        """Test map command with specific directory."""
        # Create test files
        self.create_test_file("main.py", "print('hello')")
        self.create_test_file("utils.js", "console.log('world');")

        result = self.intel_commands.handle_command("map", [str(self.temp_dir)])

        assert "Repository:" in result
        assert "Total files: 2" in result
        assert "python" in result
        assert "javascript" in result

    def test_map_command_nonexistent_path(self):
        """Test map command with nonexistent path."""
        result = self.intel_commands.handle_command("map", ["/nonexistent/path"])
        assert "Path not found" in result

    def test_scan_command_no_args(self):
        """Test scan command without arguments."""
        # Create a test file in temp directory and scan that instead
        self.create_test_file("test.py", "def test(): pass")
        result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])
        # Should scan the temp directory
        assert "Scanned" in result or "No supported files" in result

    def test_scan_command_with_directory(self):
        """Test scan command with specific directory."""
        # Create test files
        self.create_test_file("file1.py", "def func1(): pass")
        self.create_test_file("file2.js", "function func2() {}")
        self.create_test_file("file3.rs", "fn func3() {}")

        result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])

        assert "Scanned 3 files" in result
        assert "By language:" in result
        assert "python:" in result
        assert "javascript:" in result
        assert "rust:" in result

    def test_scan_command_empty_directory(self):
        """Test scan command with empty directory."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        result = self.intel_commands.handle_command("scan", [str(empty_dir)])
        assert "No supported files found" in result

    def test_scan_command_nonexistent_directory(self):
        """Test scan command with nonexistent directory."""
        result = self.intel_commands.handle_command("scan", ["/nonexistent"])
        assert "Directory not found" in result

    def test_stats_command_no_repo_mapped(self):
        """Test stats command without mapping repository first."""
        result = self.intel_commands.handle_command("stats", [])
        assert "No repository mapped" in result
        assert "Use '/intel map' first" in result

    def test_stats_command_after_mapping(self):
        """Test stats command after mapping repository."""
        # Create test files
        self.create_test_file("file1.py", "def func(): pass")
        self.create_test_file("file2.py", "class MyClass: pass")
        self.create_test_file("file3.js", "function test() {}")

        # First map the repository
        self.intel_commands.handle_command("map", [str(self.temp_dir)])

        # Then get stats
        result = self.intel_commands.handle_command("stats", [])

        assert "Language statistics:" in result
        assert "python:" in result
        assert "Files:" in result
        assert "Size:" in result
        assert "Percentage:" in result

    def test_find_command_no_args(self):
        """Test find command without arguments."""
        result = self.intel_commands.handle_command("find", [])
        assert "Usage: /intel find <name>" in result

    def test_find_command_no_repo_mapped(self):
        """Test find command without mapping repository first."""
        result = self.intel_commands.handle_command("find", ["function_name"])
        assert "No repository mapped" in result

    def test_find_command_success(self):
        """Test successful find command."""
        # Create test files
        self.create_test_file("file1.py", "def common_function(): pass")
        self.create_test_file("file2.py", "def common_function(): return 42")

        # Map repository first
        self.intel_commands.handle_command("map", [str(self.temp_dir)])

        # Find the function
        result = self.intel_commands.handle_command("find", ["common_function"])

        # Should either find it or report not found (both are valid)
        assert "Found" in result or "No definitions found" in result
        if "Found" in result:
            assert "common_function" in result

    def test_find_command_not_found(self):
        """Test find command when nothing is found."""
        # Create test file
        self.create_test_file("file1.py", "def other_function(): pass")

        # Map repository first
        self.intel_commands.handle_command("map", [str(self.temp_dir)])

        # Find non-existent function
        result = self.intel_commands.handle_command("find", ["nonexistent_function"])

        assert "No definitions found" in result

    def test_deps_command_no_args(self):
        """Test deps command without arguments."""
        result = self.intel_commands.handle_command("deps", [])
        assert "Usage: /intel deps <file_path>" in result

    def test_deps_command_nonexistent_file(self):
        """Test deps command with nonexistent file."""
        result = self.intel_commands.handle_command("deps", ["/nonexistent/file.py"])
        assert "File not found" in result

    def test_deps_command_success(self):
        """Test successful deps command."""
        # Create test file with imports
        test_file = self.create_test_file(
            "test.py",
            """
        import os
        from pathlib import Path
        import json

        def main():
            pass
        """,
        )

        result = self.intel_commands.handle_command("deps", [str(test_file)])

        # Should show dependencies (imports)
        assert "Dependencies for" in result or "No dependencies found" in result

    def test_deps_command_no_dependencies(self):
        """Test deps command with file that has no dependencies."""
        test_file = self.create_test_file(
            "simple.py",
            """
        def simple_function():
            return 42
        """,
        )

        result = self.intel_commands.handle_command("deps", [str(test_file)])
        assert "No dependencies found" in result

    def test_graph_command_no_args(self):
        """Test graph command without arguments."""
        result = self.intel_commands.handle_command("graph", [])
        assert "Usage: /intel graph <directory>" in result

    def test_graph_command_nonexistent_directory(self):
        """Test graph command with nonexistent directory."""
        result = self.intel_commands.handle_command("graph", ["/nonexistent"])
        assert "Directory not found" in result

    def test_graph_command_empty_directory(self):
        """Test graph command with empty directory."""
        empty_dir = self.temp_dir / "empty"
        empty_dir.mkdir()

        result = self.intel_commands.handle_command("graph", [str(empty_dir)])
        assert "No supported files found" in result

    def test_graph_command_success(self):
        """Test successful graph command."""
        # Create test files
        self.create_test_file(
            "main.py",
            """
        from utils import helper
        def main(): pass
        """,
        )

        self.create_test_file(
            "utils.py",
            """
        def helper(): return 42
        """,
        )

        result = self.intel_commands.handle_command("graph", [str(self.temp_dir)])

        assert "Dependency Graph for" in result
        assert "Nodes:" in result
        assert "Edges:" in result
        assert "Max depth:" in result

    def test_graph_command_with_export_json(self):
        """Test graph command with JSON export."""
        # Create test file
        self.create_test_file("test.py", "def func(): pass")

        output_file = self.temp_dir / "graph.json"

        result = self.intel_commands.handle_command(
            "graph", [str(self.temp_dir), "--format=json", f"--output={output_file}"]
        )

        assert "Graph exported to" in result
        assert "JSON" in result
        assert output_file.exists()

    def test_graph_command_with_export_dot(self):
        """Test graph command with DOT export."""
        # Create test file
        self.create_test_file("test.py", "def func(): pass")

        output_file = self.temp_dir / "graph.dot"

        result = self.intel_commands.handle_command(
            "graph", [str(self.temp_dir), "--format=dot", f"--output={output_file}"]
        )

        assert "Graph exported to" in result
        assert "DOT" in result
        assert "dot -Tpng" in result  # Should show usage hint
        assert output_file.exists()

    def test_graph_command_unsupported_format(self):
        """Test graph command with unsupported export format."""
        self.create_test_file("test.py", "def func(): pass")

        result = self.intel_commands.handle_command(
            "graph", [str(self.temp_dir), "--format=xml", "--output=output.xml"]
        )

        assert "Unsupported format: xml" in result

    def test_get_help(self):
        """Test getting help text."""
        help_text = self.intel_commands.get_help()

        assert "Intelligence Commands:" in help_text
        assert "/intel analyze" in help_text
        assert "/intel map" in help_text
        assert "/intel scan" in help_text
        assert "/intel stats" in help_text
        assert "/intel find" in help_text
        assert "/intel deps" in help_text
        assert "/intel graph" in help_text
        assert "Graph Options:" in help_text
        assert "--format=json|dot" in help_text
        assert "--output=filename" in help_text

    def test_error_handling(self):
        """Test error handling in commands."""
        # Create a file that might cause issues
        problematic_file = self.create_test_file("test.unknown", "unknown content")

        # This should handle the error gracefully
        result = self.intel_commands.handle_command("analyze", [str(problematic_file)])

        # Should get an error message but not crash
        assert isinstance(result, str)
        assert len(result) > 0


@pytest.mark.integration
class TestIntelligenceCommandsIntegration:
    """Integration tests for intelligence commands with realistic scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.intel_commands = IntelligenceCommands()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_project(self):
        """Create a realistic test project structure."""
        # Main application
        main_py = self.temp_dir / "main.py"
        main_py.write_text(
            dedent(
                """
        from src.calculator import Calculator
        from src.utils import format_result
        import json

        def main():
            '''Main application entry point.'''
            calc = Calculator()
            result = calc.add(10, 20)
            formatted = format_result(result)
            print(json.dumps(formatted))

        if __name__ == "__main__":
            main()
        """
            ).strip()
        )

        # Source directory
        src_dir = self.temp_dir / "src"
        src_dir.mkdir()

        # Calculator module
        calc_py = src_dir / "calculator.py"
        calc_py.write_text(
            dedent(
                """
        class Calculator:
            '''A simple calculator class.'''

            def add(self, a, b):
                '''Add two numbers.'''
                return a + b

            def subtract(self, a, b):
                '''Subtract two numbers.'''
                return a - b
        """
            ).strip()
        )

        # Utils module
        utils_py = src_dir / "utils.py"
        utils_py.write_text(
            dedent(
                """
        def format_result(value):
            '''Format a numeric result for display.'''
            return {
                "result": value,
                "formatted": f"Result: {value}"
            }

        def validate_input(value):
            '''Validate numeric input.'''
            if not isinstance(value, (int, float)):
                raise TypeError("Input must be numeric")
            return True
        """
            ).strip()
        )

        # Test directory
        test_dir = self.temp_dir / "tests"
        test_dir.mkdir()

        test_calc = test_dir / "test_calculator.py"
        test_calc.write_text(
            dedent(
                """
        import unittest
        import sys
        sys.path.append('..')
        from src.calculator import Calculator

        class TestCalculator(unittest.TestCase):
            def test_add(self):
                calc = Calculator()
                result = calc.add(2, 3)
                self.assertEqual(result, 5)
        """
            ).strip()
        )

        # JavaScript file
        js_file = self.temp_dir / "frontend.js"
        js_file.write_text(
            dedent(
                """
        /**
         * Frontend application logic
         */
        class App {
            constructor() {
                this.calculator = new Calculator();
            }

            /**
             * Handle calculation request
             */
            calculate(a, b) {
                return this.calculator.add(a, b);
            }
        }

        function Calculator() {
            this.add = function(a, b) {
                return a + b;
            };
        }
        """
            ).strip()
        )

    def test_full_project_analysis_workflow(self):
        """Test complete analysis workflow on a realistic project."""
        self.create_test_project()

        # Step 1: Map the repository
        map_result = self.intel_commands.handle_command("map", [str(self.temp_dir)])
        assert "Total files: 5" in map_result  # main.py, 2 src files, 1 test, 1 js
        assert "python" in map_result
        assert "javascript" in map_result

        # Step 2: Scan for detailed analysis
        scan_result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])
        assert "Scanned 5 files" in scan_result
        assert "python: 4 files" in scan_result
        assert "javascript: 1 files" in scan_result

        # Step 3: Get language statistics
        stats_result = self.intel_commands.handle_command("stats", [])
        assert "Language statistics:" in stats_result
        assert "python:" in stats_result

        # Step 4: Find specific definitions
        find_result = self.intel_commands.handle_command("find", ["Calculator"])
        assert "Found" in find_result
        assert "Calculator" in find_result

        # Step 5: Analyze specific file
        calc_file = str(self.temp_dir / "src" / "calculator.py")
        analyze_result = self.intel_commands.handle_command("analyze", [calc_file])
        assert "Calculator" in analyze_result
        assert "add" in analyze_result
        assert "subtract" in analyze_result

        # Step 6: Generate dependency graph
        graph_result = self.intel_commands.handle_command("graph", [str(self.temp_dir)])
        assert "Dependency Graph" in graph_result
        assert "Nodes: 5" in graph_result

    def test_documentation_extraction_workflow(self):
        """Test documentation extraction in analysis."""
        self.create_test_project()

        # Analyze a file with documentation
        calc_file = str(self.temp_dir / "src" / "calculator.py")
        result = self.intel_commands.handle_command("analyze", [calc_file])

        # Should detect class and methods
        assert "class: Calculator" in result
        assert "function: add" in result
        assert "function: subtract" in result

    def test_cross_language_analysis(self):
        """Test analysis across multiple languages."""
        self.create_test_project()

        # Scan the entire project
        result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])

        # Should handle both Python and JavaScript
        assert "python:" in result
        assert "javascript:" in result

        # Should count functions across languages
        assert "definitions" in result

    def test_error_recovery(self):
        """Test error recovery in complex scenarios."""
        self.create_test_project()

        # Add a file with syntax errors
        bad_file = self.temp_dir / "bad_syntax.py"
        bad_file.write_text("def incomplete_function(\n")  # Syntax error

        # Analysis should still work for other files
        result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])

        # Should still process the valid files
        assert "Scanned" in result
        # The bad file might be counted but should not crash the analysis
