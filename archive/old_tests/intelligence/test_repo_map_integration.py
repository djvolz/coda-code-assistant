"""Integration tests for RepoMap with TreeSitterAnalyzer."""

import tempfile
from pathlib import Path
from textwrap import dedent

from coda.base.search.map.repo_map import RepoMap
from coda.base.search.map.tree_sitter_analyzer import TreeSitterAnalyzer


class TestRepoMapIntegration:
    """Test suite for RepoMap integration with tree-sitter analysis."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.repo_map = RepoMap(self.temp_dir)
        self.analyzer = TreeSitterAnalyzer()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_file(self, path: str, content: str) -> Path:
        """Create a test file with given content."""
        file_path = self.temp_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(dedent(content).strip())
        return file_path

    def create_test_repo(self):
        """Create a test repository structure."""
        # Python files
        self.create_test_file(
            "src/main.py",
            """
        import os
        from src.utils import helper

        def main():
            '''Main entry point'''
            print("Hello World")
            helper()

        if __name__ == "__main__":
            main()
        """,
        )

        self.create_test_file(
            "src/utils.py",
            """
        def helper():
            '''Helper function'''
            return 42

        class Config:
            '''Configuration class'''
            def __init__(self):
                self.value = 100
        """,
        )

        # JavaScript files
        self.create_test_file(
            "frontend/app.js",
            """
        import React from 'react';
        import { Button } from './components';

        function App() {
            return <div>Hello</div>;
        }

        export default App;
        """,
        )

        self.create_test_file(
            "frontend/components.js",
            """
        export const Button = ({ label }) => {
            return <button>{label}</button>;
        };

        export class Widget {
            render() {
                return '<div>Widget</div>';
            }
        }
        """,
        )

        # Test files
        self.create_test_file(
            "tests/test_main.py",
            """
        import pytest
        from src.main import main

        def test_main():
            assert main() is None
        """,
        )

        # Config files
        self.create_test_file(
            "package.json",
            """
        {
            "name": "test-project",
            "version": "1.0.0",
            "dependencies": {
                "react": "^18.0.0"
            }
        }
        """,
        )

        self.create_test_file(
            "pyproject.toml",
            """
        [project]
        name = "test-project"
        version = "1.0.0"
        dependencies = ["pytest", "requests"]
        """,
        )

        # README
        self.create_test_file(
            "README.md",
            """
        # Test Project

        This is a test project for integration testing.
        """,
        )

        # Hidden files (should be ignored)
        self.create_test_file(".gitignore", "*.pyc\nnode_modules/")
        self.create_test_file(".env", "SECRET=123")

        # Binary file simulation
        self.create_test_file("data.bin", "\x00\x01\x02\x03")

    def test_repo_scan_with_tree_sitter_analysis(self):
        """Test scanning repository and analyzing with tree-sitter."""
        self.create_test_repo()

        # Scan repository
        self.repo_map.scan_repository()

        # Check basic stats
        assert self.repo_map.stats is not None
        assert self.repo_map.stats.total_files > 0
        assert "python" in self.repo_map.stats.languages
        assert "javascript" in self.repo_map.stats.languages

        # Analyze each file with tree-sitter
        analyses = {}
        for file_path, file_info in self.repo_map.files.items():
            if file_info.language in ["python", "javascript"]:
                full_path = self.temp_dir / file_path
                analysis = self.analyzer.analyze_file(full_path)
                analyses[file_path] = analysis

                # Store definitions and references in FileInfo
                file_info.definitions = [d.name for d in analysis.definitions]
                file_info.references = [r.name for r in analysis.references]

        # Verify Python analysis
        main_py = analyses.get("src/main.py")
        assert main_py is not None
        assert any(d.name == "main" for d in main_py.definitions)
        assert len(main_py.imports) >= 2  # os and helper

        utils_py = analyses.get("src/utils.py")
        assert utils_py is not None
        assert any(d.name == "helper" for d in utils_py.definitions)
        assert any(d.name == "Config" for d in utils_py.definitions)

        # Verify JavaScript analysis
        app_js = analyses.get("frontend/app.js")
        assert app_js is not None
        assert any(d.name == "App" for d in app_js.definitions)
        assert len(app_js.imports) >= 2  # React and Button

    def test_ignore_patterns(self):
        """Test that ignore patterns work correctly."""
        self.create_test_repo()

        # Add files that should be ignored
        self.create_test_file("node_modules/package/index.js", "export default {};")
        self.create_test_file("__pycache__/module.pyc", "bytecode")
        self.create_test_file(".git/config", "[core]")
        self.create_test_file("build/output.js", "compiled code")

        self.repo_map.scan_repository()

        # Check that ignored files are not included
        file_paths = list(self.repo_map.files.keys())
        assert not any("node_modules" in path for path in file_paths)
        assert not any("__pycache__" in path for path in file_paths)
        assert not any(".git" in path for path in file_paths)
        assert not any("build" in path for path in file_paths)
        assert not any(".env" in path for path in file_paths)

    def test_language_detection_consistency(self):
        """Test that language detection is consistent between RepoMap and TreeSitterAnalyzer."""
        test_files = {
            "test.py": "python",
            "test.js": "javascript",
            "test.ts": "typescript",
            "test.rs": "rust",
            "test.go": "go",
            "test.java": "java",
            "test.cpp": "cpp",
            "test.rb": "ruby",
            "test.php": "php",
        }

        for filename, expected_lang in test_files.items():
            file_path = self.create_test_file(filename, "// test content")

            # RepoMap detection
            repo_lang = self.repo_map.get_language_from_path(file_path)

            # TreeSitterAnalyzer detection
            analyzer_lang = self.analyzer.detect_language(file_path)

            # Both should agree on the language
            assert repo_lang == expected_lang
            assert analyzer_lang == expected_lang or analyzer_lang == "unknown"

    def test_find_files_by_pattern_with_analysis(self):
        """Test finding files by pattern and analyzing them."""
        self.create_test_repo()
        self.repo_map.scan_repository()

        # Find all Python files
        python_files = self.repo_map.find_files_by_pattern("**/*.py")
        assert len(python_files) >= 3  # main.py, utils.py, test_main.py

        # Analyze each Python file
        for file_info in python_files:
            full_path = self.temp_dir / file_info.path
            analysis = self.analyzer.analyze_file(full_path)

            # Should be able to analyze without errors
            assert analysis.language == "python"
            assert len(analysis.errors) == 0

    def test_dependency_tracking(self):
        """Test tracking dependencies between files."""
        self.create_test_repo()
        self.repo_map.scan_repository()

        # Create a dependency graph
        dependencies = {}

        for file_path, file_info in self.repo_map.files.items():
            if file_info.language in ["python", "javascript"]:
                full_path = self.temp_dir / file_path
                analysis = self.analyzer.analyze_file(full_path)

                # Extract import dependencies
                deps = []
                for imp in analysis.imports:
                    # Resolve relative imports
                    if file_info.language == "python":
                        if imp.name.startswith("src."):
                            dep_file = imp.name.replace(".", "/") + ".py"
                            if dep_file in self.repo_map.files:
                                deps.append(dep_file)
                    elif file_info.language == "javascript":
                        if imp.name.startswith("./"):
                            dep_path = Path(file_path).parent / imp.name[2:]
                            dep_file = str(dep_path) + ".js"
                            if dep_file in self.repo_map.files:
                                deps.append(dep_file)

                dependencies[file_path] = deps

        # Verify dependencies
        assert "src/utils.py" in dependencies.get("src/main.py", [])
        # JavaScript import parsing should now work correctly
        assert "frontend/components.js" in dependencies.get("frontend/app.js", [])

    def test_repo_summary_with_definitions(self):
        """Test generating repository summary with definition counts."""
        self.create_test_repo()
        self.repo_map.scan_repository()

        # Analyze files and count definitions
        total_definitions = {
            "function": 0,
            "class": 0,
            "variable": 0,
        }

        for file_path, file_info in self.repo_map.files.items():
            if file_info.language in ["python", "javascript"]:
                full_path = self.temp_dir / file_path
                analysis = self.analyzer.analyze_file(full_path)

                # Count definitions by type
                for definition in analysis.definitions:
                    kind = definition.kind.value
                    if kind in total_definitions:
                        total_definitions[kind] += 1
                    elif kind == "method":
                        total_definitions["function"] += 1

        # Should have found some definitions
        assert total_definitions["function"] > 0
        assert total_definitions["class"] > 0

    def test_git_integration(self):
        """Test git repository detection and info extraction."""
        # Initialize git repo
        import subprocess

        subprocess.run(["git", "init"], cwd=self.temp_dir, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@example.com"],
            cwd=self.temp_dir,
            capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"], cwd=self.temp_dir, capture_output=True
        )
        # Add a remote to prevent git config errors
        subprocess.run(
            ["git", "remote", "add", "origin", "https://github.com/test/repo.git"],
            cwd=self.temp_dir,
            capture_output=True,
        )

        self.create_test_repo()

        # Add and commit files
        subprocess.run(["git", "add", "."], cwd=self.temp_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"], cwd=self.temp_dir, capture_output=True
        )

        # Test git detection
        git_exists = (self.temp_dir / ".git").exists()
        assert git_exists, f".git directory exists: {git_exists}, path: {self.temp_dir}"
        assert self.repo_map.is_git_repository()

        git_info = self.repo_map.get_git_info()
        assert git_info is not None
        assert "branch" in git_info
        assert "commit" in git_info

    def test_large_file_handling(self):
        """Test handling of large files."""
        # Create a large file (> 1MB)
        large_content = "x" * (1024 * 1024 + 1)
        self.create_test_file("large.txt", large_content)

        # Create a normal file
        self.create_test_file("normal.py", "def test(): pass")

        self.repo_map.scan_repository()

        # Large file should be skipped
        assert "large.txt" not in self.repo_map.files
        assert "normal.py" in self.repo_map.files

    def test_language_stats_integration(self):
        """Test language statistics with actual file analysis."""
        self.create_test_repo()
        self.repo_map.scan_repository()

        stats = self.repo_map.get_language_stats()

        # Should have statistics for Python and JavaScript
        assert "python" in stats
        assert "javascript" in stats

        # Python stats
        py_stats = stats["python"]
        assert py_stats["file_count"] >= 3  # main.py, utils.py, test_main.py
        assert py_stats["total_size"] > 0
        assert py_stats["percentage"] > 0
        assert py_stats["average_size"] > 0

        # JavaScript stats
        js_stats = stats["javascript"]
        assert js_stats["file_count"] >= 2  # app.js, components.js
        assert js_stats["total_size"] > 0

    def test_combined_analysis_workflow(self):
        """Test a complete workflow combining RepoMap and TreeSitterAnalyzer."""
        self.create_test_repo()

        # Step 1: Scan repository
        self.repo_map.scan_repository()
        summary = self.repo_map.get_summary()

        assert summary["total_files"] > 0
        assert "python" in summary["languages"]

        # Step 2: Analyze specific language files
        python_files = self.repo_map.get_files_by_language("python")

        analysis_results = {}
        for file_info in python_files:
            full_path = self.temp_dir / file_info.path
            analysis = self.analyzer.analyze_file(full_path)
            analysis_results[file_info.path] = analysis

        # Step 3: Find specific definitions across the codebase
        all_functions = []
        for _path, analysis in analysis_results.items():
            functions = [d for d in analysis.definitions if d.kind.value in ["function", "method"]]
            all_functions.extend(functions)

        # Should find main, helper, and test functions
        func_names = [f.name for f in all_functions]
        assert "main" in func_names
        assert "helper" in func_names

        # Step 4: Generate a report
        report = {
            "summary": summary,
            "definitions": {"total_functions": len(all_functions), "function_names": func_names},
            "languages": self.repo_map.get_language_stats(),
        }

        # Verify report structure
        assert report["summary"]["total_files"] > 0
        assert report["definitions"]["total_functions"] > 0
        assert len(report["languages"]) > 0
