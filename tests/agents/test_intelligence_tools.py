"""Tests for native intelligence tools."""

import tempfile
from pathlib import Path

import pytest

from coda.agents.intelligence_tools import (
    analyze_code,
    code_stats,
    find_definition,
    find_pattern,
    get_dependencies,
)


class TestNativeIntelligenceTools:
    """Test suite for native intelligence tools."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

        # Create test Python file
        self.python_file = self.test_dir / "test_module.py"
        self.python_file.write_text(
            '''
"""Test module for intelligence tools."""

import os
import sys
from typing import List, Dict

class Calculator:
    """A simple calculator class."""

    def add(self, a: int, b: int) -> int:
        """Add two numbers."""
        return a + b

    def multiply(self, x: float, y: float) -> float:
        """Multiply two numbers."""
        return x * y

def process_data(items: List[str]) -> Dict[str, int]:
    """Process a list of items."""
    result = {}
    for item in items:
        result[item] = len(item)
    return result

CONSTANT_VALUE = 42
DEBUG_MODE = True
'''
        )

        # Create another Python file
        self.utils_file = self.test_dir / "utils.py"
        self.utils_file.write_text(
            '''
def helper_function():
    """A helper function."""
    return "helper"

class HelperClass:
    pass
'''
        )

        # Create JavaScript file
        self.js_file = self.test_dir / "app.js"
        self.js_file.write_text(
            """
import React from 'react';
import axios from 'axios';

export class UserComponent {
    constructor() {
        this.state = {};
    }

    fetchUser(id) {
        return axios.get(`/api/users/${id}`);
    }
}

export function formatDate(date) {
    return date.toLocaleDateString();
}
"""
        )

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_find_definition(self):
        """Test find_definition tool."""
        # Change to test directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)

            # Test finding a class
            result = find_definition("Calculator")
            assert "Found 1 definition(s) for 'Calculator'" in result
            assert "test_module.py" in result
            assert "class" in result

            # Test finding a function
            result = find_definition("process_data")
            assert "Found 1 definition(s) for 'process_data'" in result
            assert "function" in result

            # Test with kind filter
            result = find_definition("add", kind="method")
            assert "Found 1 definition(s) for 'add'" in result

            # Test not found
            result = find_definition("NonExistent")
            assert "No definitions found" in result

            # Test invalid kind
            result = find_definition("Calculator", kind="invalid")
            assert "Invalid kind" in result

        finally:
            os.chdir(original_cwd)

    def test_analyze_code(self):
        """Test analyze_code tool."""
        # Test Python file analysis
        result = analyze_code(str(self.python_file))
        assert "Analysis of test_module.py (python)" in result
        assert "class" in result
        assert "Calculator" in result
        assert "function" in result
        assert "process_data" in result
        assert "Imports" in result
        assert "os" in result

        # Test JavaScript file analysis
        result = analyze_code(str(self.js_file))
        assert "Analysis of app.js (javascript)" in result
        assert "UserComponent" in result
        assert "formatDate" in result

        # Test non-existent file
        result = analyze_code("/non/existent/file.py")
        assert "File not found" in result

        # Test no file specified
        result = analyze_code()
        assert "Please specify a file path" in result

    def test_get_dependencies(self):
        """Test get_dependencies tool."""
        # Test Python dependencies
        result = get_dependencies(str(self.python_file))
        assert "Dependencies for test_module.py (python)" in result
        assert "os" in result
        assert "sys" in result
        assert "typing" in result

        # Test JavaScript dependencies
        result = get_dependencies(str(self.js_file))
        assert "Dependencies for app.js (javascript)" in result
        assert "react" in result
        assert "axios" in result

        # Test file with no dependencies
        result = get_dependencies(str(self.utils_file))
        assert "No dependencies found" in result

        # Test non-existent file
        result = get_dependencies("/non/existent/file.py")
        assert "File not found" in result

    def test_code_stats(self):
        """Test code_stats tool."""
        # Change to test directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)

            result = code_stats()
            assert "Code statistics" in result
            assert "Total files:" in result
            assert "Total definitions:" in result
            assert "python:" in result
            assert "javascript:" in result
            assert "classes" in result
            assert "functions" in result

            # Test with specific directory
            result = code_stats(str(self.test_dir))
            assert "Code statistics" in result

            # Test non-existent directory
            result = code_stats("/non/existent/dir")
            assert "Directory not found" in result

        finally:
            os.chdir(original_cwd)

    def test_find_pattern(self):
        """Test find_pattern tool."""
        # Change to test directory
        import os

        original_cwd = os.getcwd()
        try:
            os.chdir(self.test_dir)

            # Test finding classes
            result = find_pattern("classes")
            assert "Calculator" in result
            assert "UserComponent" in result
            assert "class:" in result

            # Test finding functions
            result = find_pattern("functions")
            assert "process_data" in result
            assert "formatDate" in result

            # Test finding imports
            result = find_pattern("imports")
            assert "import" in result

            # Test specific name search
            result = find_pattern("calc")
            assert "Calculator" in result

            # Test with file type filter
            result = find_pattern("classes", file_type="py")
            assert "Calculator" in result
            assert "UserComponent" not in result  # JS class

            # Test no matches
            result = find_pattern("xyz123")
            assert "No matches found" in result

        finally:
            os.chdir(original_cwd)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
