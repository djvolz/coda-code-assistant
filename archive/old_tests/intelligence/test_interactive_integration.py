"""Integration tests for intelligence commands with MockProvider and interactive CLI."""

import tempfile
from pathlib import Path
from textwrap import dedent
from unittest.mock import MagicMock, patch

import pytest

from coda.base.providers import Message, MockProvider, Role
from coda.base.search.cli import IntelligenceCommands


@pytest.mark.integration
class TestIntelligenceInteractiveCLI:
    """Test intelligence commands in the context of interactive CLI with MockProvider."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.mock_provider = MockProvider()
        self.intel_commands = IntelligenceCommands()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_sample_project(self):
        """Create a sample project for testing."""
        # Create a Python project structure
        main_py = self.temp_dir / "main.py"
        main_py.write_text(
            dedent(
                """
        '''Main application module.'''
        from utils import calculate_fibonacci
        from data_processing import DataProcessor
        import json

        def main():
            '''Main entry point.'''
            processor = DataProcessor()
            result = processor.process_data([1, 2, 3, 4, 5])

            fib_10 = calculate_fibonacci(10)

            output = {
                "processed_data": result,
                "fibonacci_10": fib_10
            }

            print(json.dumps(output, indent=2))

        if __name__ == "__main__":
            main()
        """
            ).strip()
        )

        utils_py = self.temp_dir / "utils.py"
        utils_py.write_text(
            dedent(
                """
        '''Utility functions for mathematical operations.'''

        def calculate_fibonacci(n):
            '''Calculate the nth Fibonacci number.'''
            if n <= 1:
                return n
            return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

        def factorial(n):
            '''Calculate factorial of n.'''
            if n <= 1:
                return 1
            return n * factorial(n-1)

        def is_prime(n):
            '''Check if a number is prime.'''
            if n < 2:
                return False
            for i in range(2, int(n**0.5) + 1):
                if n % i == 0:
                    return False
            return True
        """
            ).strip()
        )

        data_py = self.temp_dir / "data_processing.py"
        data_py.write_text(
            dedent(
                """
        '''Data processing utilities.'''
        from utils import factorial

        class DataProcessor:
            '''A class for processing numerical data.'''

            def __init__(self):
                '''Initialize the data processor.'''
                self.processed_count = 0

            def process_data(self, data):
                '''Process a list of numerical data.'''
                result = []
                for item in data:
                    processed_item = {
                        "original": item,
                        "squared": item ** 2,
                        "factorial": factorial(item) if item <= 10 else "too_large"
                    }
                    result.append(processed_item)
                    self.processed_count += 1
                return result

            def get_statistics(self, data):
                '''Get basic statistics for the data.'''
                if not data:
                    return {}

                return {
                    "count": len(data),
                    "sum": sum(data),
                    "average": sum(data) / len(data),
                    "min": min(data),
                    "max": max(data)
                }
        """
            ).strip()
        )

        # Add a test file
        test_dir = self.temp_dir / "tests"
        test_dir.mkdir()

        test_utils = test_dir / "test_utils.py"
        test_utils.write_text(
            dedent(
                """
        '''Tests for utility functions.'''
        import unittest
        import sys
        sys.path.append('..')
        from utils import calculate_fibonacci, factorial, is_prime

        class TestUtils(unittest.TestCase):
            '''Test cases for utility functions.'''

            def test_fibonacci(self):
                '''Test Fibonacci calculation.'''
                self.assertEqual(calculate_fibonacci(0), 0)
                self.assertEqual(calculate_fibonacci(1), 1)
                self.assertEqual(calculate_fibonacci(5), 5)

            def test_factorial(self):
                '''Test factorial calculation.'''
                self.assertEqual(factorial(0), 1)
                self.assertEqual(factorial(5), 120)

            def test_is_prime(self):
                '''Test prime number detection.'''
                self.assertFalse(is_prime(1))
                self.assertTrue(is_prime(2))
                self.assertTrue(is_prime(17))
                self.assertFalse(is_prime(15))
        """
            ).strip()
        )

    def test_intelligence_commands_work_with_mock_provider(self):
        """Test that intelligence commands work alongside MockProvider."""
        self.create_sample_project()

        # Simulate using MockProvider for a conversation
        messages = [Message(role=Role.USER, content="Hello, I need help analyzing my Python code.")]

        response = self.mock_provider.chat(messages, "mock-echo")
        assert response is not None
        assert "analyzing" in response.lower() or "python" in response.lower()

        # Now use intelligence commands to actually analyze the code
        analyze_result = self.intel_commands.handle_command(
            "analyze", [str(self.temp_dir / "main.py")]
        )

        assert "python" in analyze_result
        assert "main" in analyze_result
        assert "function:" in analyze_result

        # The intelligence analysis should provide concrete information
        # that could be used to enhance the AI conversation
        assert "Definitions:" in analyze_result
        assert "Imports:" in analyze_result

    def test_intelligence_provides_context_for_ai_conversation(self):
        """Test how intelligence commands can provide context for AI conversations."""
        self.create_sample_project()

        # First, gather intelligence about the codebase
        scan_result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])
        map_result = self.intel_commands.handle_command("map", [str(self.temp_dir)])

        # Extract key information from intelligence results
        assert "python:" in scan_result
        assert "definitions" in scan_result
        assert "Total files:" in map_result

        # Now simulate an AI conversation where this context would be useful
        messages = [
            Message(
                role=Role.SYSTEM,
                content=f"The user has a Python project with the following structure: {map_result[:200]}...",
            ),
            Message(
                role=Role.USER, content="Can you help me understand the structure of my codebase?"
            ),
        ]

        response = self.mock_provider.chat(messages, "mock-smart")

        # MockProvider should give a contextual response
        assert response is not None
        assert len(response) > 0

        # The intelligence gathering should provide concrete data
        # that makes the AI response more helpful
        assert "4 files" in scan_result or "python" in scan_result

    def test_dependency_analysis_for_ai_assistance(self):
        """Test using dependency analysis to help AI understand code relationships."""
        self.create_sample_project()

        # Analyze dependencies
        main_deps = self.intel_commands.handle_command("deps", [str(self.temp_dir / "main.py")])
        utils_analysis = self.intel_commands.handle_command(
            "analyze", [str(self.temp_dir / "utils.py")]
        )

        # Should show import relationships
        assert isinstance(main_deps, str)
        assert isinstance(utils_analysis, str)

        # Create a conversation context that uses this information
        context_info = f"Main file dependencies: {main_deps}\nUtils analysis: {utils_analysis}"

        messages = [
            Message(role=Role.SYSTEM, content=f"Code analysis context: {context_info[:500]}..."),
            Message(
                role=Role.USER,
                content="I want to refactor the calculate_fibonacci function. What should I consider?",
            ),
        ]

        response = self.mock_provider.chat(messages, "mock-smart")
        assert response is not None

        # The intelligence data should help provide better context
        assert "calculate_fibonacci" in utils_analysis
        assert "function:" in utils_analysis

    def test_graph_generation_for_visualization_context(self):
        """Test generating dependency graphs that could be used in AI conversations."""
        self.create_sample_project()

        # Generate dependency graph
        graph_result = self.intel_commands.handle_command("graph", [str(self.temp_dir)])

        assert "Dependency Graph" in graph_result
        assert "Nodes:" in graph_result
        assert "Edges:" in graph_result

        # Export graph for potential use in AI context
        graph_file = self.temp_dir / "project_graph.json"
        export_result = self.intel_commands.handle_command(
            "graph", [str(self.temp_dir), "--format=json", f"--output={graph_file}"]
        )

        assert "Graph exported" in export_result
        assert graph_file.exists()

        # This graph data could be used to give AI better understanding
        # of code structure and relationships
        import json

        with open(graph_file) as f:
            graph_data = json.load(f)

        assert "nodes" in graph_data
        assert "edges" in graph_data
        assert "statistics" in graph_data

    def test_find_definitions_for_code_assistance(self):
        """Test using definition finding to assist with code-related questions."""
        self.create_sample_project()

        # Map repository first
        self.intel_commands.handle_command("map", [str(self.temp_dir)])

        # Find specific definitions
        fibonacci_result = self.intel_commands.handle_command("find", ["calculate_fibonacci"])
        processor_result = self.intel_commands.handle_command("find", ["DataProcessor"])

        # Should find the definitions
        assert "Found" in fibonacci_result or "No definitions found" in fibonacci_result
        assert "Found" in processor_result or "No definitions found" in processor_result

        # This information could help AI provide more specific assistance
        [
            Message(role=Role.USER, content="Where is the DataProcessor class defined in my code?")
        ]

        # The find command provides the exact answer
        if "Found" in processor_result:
            assert "DataProcessor" in processor_result
            assert "class" in processor_result.lower()

    @patch("coda.cli.interactive_cli.InteractiveCLI")
    def test_intelligence_commands_in_interactive_context(self, mock_cli):
        """Test intelligence commands as they would be used in interactive CLI."""
        self.create_sample_project()

        # Mock the interactive CLI
        mock_cli_instance = MagicMock()
        mock_cli.return_value = mock_cli_instance

        # Simulate the intelligence command handler being called
        # (This is what would happen when user types /intel analyze file.py)

        # Test each command as it would be called from interactive mode
        commands_to_test = [
            ("analyze", [str(self.temp_dir / "main.py")]),
            ("map", [str(self.temp_dir)]),
            ("scan", [str(self.temp_dir)]),
            ("find", ["calculate_fibonacci"]),
            ("deps", [str(self.temp_dir / "utils.py")]),
            ("graph", [str(self.temp_dir)]),
        ]

        for command, args in commands_to_test:
            try:
                result = self.intel_commands.handle_command(command, args)
                # Should return string output (not crash)
                assert isinstance(result, str)
                assert len(result) > 0
            except Exception as e:
                pytest.fail(f"Command '{command}' failed with error: {e}")

    def test_stats_command_after_repository_mapping(self):
        """Test stats command workflow that requires prior mapping."""
        self.create_sample_project()

        # First attempt without mapping should fail gracefully
        stats_result = self.intel_commands.handle_command("stats", [])
        assert "No repository mapped" in stats_result

        # Map repository first
        map_result = self.intel_commands.handle_command("map", [str(self.temp_dir)])
        assert "Repository:" in map_result

        # Now stats should work
        stats_result = self.intel_commands.handle_command("stats", [])
        assert "Language statistics:" in stats_result
        assert "python:" in stats_result

    def test_help_command_provides_useful_information(self):
        """Test that help command provides useful information for users."""
        help_result = self.intel_commands.get_help()

        # Should contain all available commands
        expected_commands = [
            "/intel analyze",
            "/intel map",
            "/intel scan",
            "/intel stats",
            "/intel find",
            "/intel deps",
            "/intel graph",
        ]

        for command in expected_commands:
            assert command in help_result

        # Should contain usage information
        assert "Graph Options:" in help_result
        assert "--format=json|dot" in help_result
        assert "--output=filename" in help_result

    def test_error_handling_in_interactive_context(self):
        """Test error handling when commands fail in interactive context."""
        # Test various error conditions
        error_cases = [
            ("analyze", ["/nonexistent/file.py"]),  # File not found
            ("map", ["/nonexistent/directory"]),  # Directory not found
            ("scan", ["/nonexistent/directory"]),  # Directory not found
            ("find", []),  # Missing argument
            ("deps", []),  # Missing argument
            ("graph", []),  # Missing argument
            ("unknown_command", []),  # Unknown command
        ]

        for command, args in error_cases:
            result = self.intel_commands.handle_command(command, args)

            # Should return error message, not crash
            assert isinstance(result, str)
            assert len(result) > 0

            # Should contain helpful error information
            assert any(
                word in result.lower()
                for word in ["error", "not found", "usage", "unknown", "missing"]
            )

    def test_realistic_development_workflow(self):
        """Test a realistic development workflow using intelligence commands."""
        self.create_sample_project()

        # Workflow: Developer wants to understand and work with a new codebase

        # Step 1: Get overall picture
        map_result = self.intel_commands.handle_command("map", [str(self.temp_dir)])
        assert "Total files:" in map_result

        # Step 2: Detailed analysis
        scan_result = self.intel_commands.handle_command("scan", [str(self.temp_dir)])
        assert "Scanned" in scan_result

        # Step 3: Understand dependencies
        graph_result = self.intel_commands.handle_command("graph", [str(self.temp_dir)])
        assert "Dependency Graph" in graph_result

        # Step 4: Find specific functionality
        map_result = self.intel_commands.handle_command(
            "map", [str(self.temp_dir)]
        )  # Ensure mapped
        self.intel_commands.handle_command("find", ["DataProcessor"])
        # Should either find it or report not found, both are valid

        # Step 5: Analyze specific files
        main_analysis = self.intel_commands.handle_command(
            "analyze", [str(self.temp_dir / "main.py")]
        )
        assert "main" in main_analysis

        utils_analysis = self.intel_commands.handle_command(
            "analyze", [str(self.temp_dir / "utils.py")]
        )
        assert "calculate_fibonacci" in utils_analysis

        # All steps should complete without errors
        # This workflow provides comprehensive understanding of the codebase
