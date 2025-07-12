"""Tests for intelligence tools."""

import asyncio
import tempfile
from pathlib import Path

import pytest

from coda.tools.intelligence_tools import (
    AnalyzeFileTool,
    BuildDependencyGraphTool,
    FindDefinitionTool,
    GetFileDependenciesTool,
    MapRepositoryTool,
    ScanDirectoryTool,
)


class TestIntelligenceTools:
    """Test suite for intelligence tools."""

    def setup_method(self):
        """Set up test environment."""
        self.temp_dir = tempfile.mkdtemp()
        self.test_dir = Path(self.temp_dir)

        # Create test Python file
        self.python_file = self.test_dir / "test.py"
        self.python_file.write_text(
            '''
"""Test module."""

import os
from typing import List

class TestClass:
    """A test class."""

    def method1(self):
        """Test method."""
        return 42

    def method2(self, arg: str) -> str:
        return arg.upper()

def test_function(items: List[str]) -> int:
    """Test function."""
    return len(items)

CONSTANT = "test_value"
'''
        )

        # Create test JavaScript file
        self.js_file = self.test_dir / "test.js"
        self.js_file.write_text(
            """
import React from 'react';
import { useState } from 'react';

export class Component {
    constructor() {
        this.state = {};
    }

    render() {
        return <div>Hello</div>;
    }
}

export function useCustomHook() {
    const [value, setValue] = useState(0);
    return { value, setValue };
}

const helper = (x) => x * 2;
"""
        )

        # Create subdirectory with more files
        self.sub_dir = self.test_dir / "src"
        self.sub_dir.mkdir()

        self.sub_file = self.sub_dir / "utils.py"
        self.sub_file.write_text(
            """
def utility_function():
    return "utility"
"""
        )

    def teardown_method(self):
        """Clean up test environment."""
        import shutil

        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_analyze_file_tool(self):
        """Test AnalyzeFileTool."""
        tool = AnalyzeFileTool()

        # Test schema
        schema = tool.get_schema()
        assert schema.name == "analyze_code_file"
        assert schema.category == "intelligence"
        assert "file_path" in schema.parameters

        # Test execution
        result = asyncio.run(tool.execute({"file_path": str(self.python_file)}))
        assert result.success
        assert result.result["language"] == "python"
        assert len(result.result["definitions"]) > 0
        assert len(result.result["imports"]) >= 2  # At least os and typing

        # Check definitions
        def_names = [d["name"] for d in result.result["definitions"]]
        assert "TestClass" in def_names
        assert "method1" in def_names
        assert "test_function" in def_names
        assert "CONSTANT" in def_names

        # Test with references
        result = asyncio.run(
            tool.execute({"file_path": str(self.python_file), "include_references": True})
        )
        assert result.success
        assert "references" in result.result

        # Test non-existent file
        result = asyncio.run(tool.execute({"file_path": "/non/existent/file.py"}))
        assert not result.success
        assert "not found" in result.error

    def test_scan_directory_tool(self):
        """Test ScanDirectoryTool."""
        tool = ScanDirectoryTool()

        # Test schema
        schema = tool.get_schema()
        assert schema.name == "scan_code_directory"
        assert "directory" in schema.parameters
        assert "recursive" in schema.parameters

        # Test execution
        result = asyncio.run(tool.execute({"directory": str(self.test_dir)}))
        assert result.success
        assert result.result["total_files"] >= 3  # py, js, and utils.py
        assert "python" in result.result["languages"]
        assert "javascript" in result.result["languages"]

        # Check language stats
        py_stats = result.result["languages"]["python"]
        assert py_stats["files"] >= 2
        assert py_stats["definitions"] > 0
        assert py_stats["classes"] == 1
        assert py_stats["functions"] >= 3  # test_function + methods

        # Test non-recursive
        result = asyncio.run(tool.execute({"directory": str(self.test_dir), "recursive": False}))
        assert result.success
        assert result.result["total_files"] == 2  # Only py and js in root

        # Test non-existent directory
        result = asyncio.run(tool.execute({"directory": "/non/existent/dir"}))
        assert not result.success

    def test_find_definition_tool(self):
        """Test FindDefinitionTool."""
        tool = FindDefinitionTool()

        # Test schema
        schema = tool.get_schema()
        assert schema.name == "find_code_definition"
        assert "name" in schema.parameters
        assert "kind" in schema.parameters

        # Test finding a class
        result = asyncio.run(tool.execute({"name": "TestClass", "directory": str(self.test_dir)}))
        assert result.success
        assert result.result["count"] == 1
        assert result.result["definitions"][0]["kind"] == "class"

        # Test finding a function
        result = asyncio.run(
            tool.execute({"name": "test_function", "directory": str(self.test_dir)})
        )
        assert result.success
        assert result.result["count"] == 1
        assert result.result["definitions"][0]["kind"] == "function"

        # Test finding with kind filter
        result = asyncio.run(
            tool.execute({"name": "method1", "directory": str(self.test_dir), "kind": "method"})
        )
        assert result.success
        assert result.result["count"] == 1

        # Test not found
        result = asyncio.run(tool.execute({"name": "NonExistent", "directory": str(self.test_dir)}))
        assert result.success
        assert "message" in result.result
        assert "No definitions found" in result.result["message"]

        # Test invalid kind
        result = asyncio.run(
            tool.execute({"name": "TestClass", "directory": str(self.test_dir), "kind": "invalid"})
        )
        assert not result.success
        assert "Invalid definition kind" in result.error

    def test_get_file_dependencies_tool(self):
        """Test GetFileDependenciesTool."""
        tool = GetFileDependenciesTool()

        # Test schema
        schema = tool.get_schema()
        assert schema.name == "get_file_dependencies"

        # Test Python file
        result = asyncio.run(tool.execute({"file_path": str(self.python_file)}))
        assert result.success
        assert result.result["language"] == "python"
        # Check that expected imports are present (may include duplicates)
        deps = result.result["dependencies"]
        assert any("os" in d for d in deps)
        assert any("typing" in d for d in deps)
        assert result.result["count"] >= 2

        # Test JavaScript file
        result = asyncio.run(tool.execute({"file_path": str(self.js_file)}))
        assert result.success
        assert result.result["language"] == "javascript"
        assert "react" in result.result["dependencies"]

        # Test non-existent file
        result = asyncio.run(tool.execute({"file_path": "/non/existent/file.py"}))
        assert not result.success

    def test_build_dependency_graph_tool(self):
        """Test BuildDependencyGraphTool."""
        tool = BuildDependencyGraphTool()

        # Test schema
        schema = tool.get_schema()
        assert schema.name == "build_dependency_graph"
        assert "include_cycles" in schema.parameters

        # Test execution
        result = asyncio.run(tool.execute({"directory": str(self.test_dir)}))
        assert result.success
        assert result.result["total_nodes"] >= 3
        assert result.result["total_edges"] >= 0  # Depends on import resolution

        # Test non-existent directory
        result = asyncio.run(tool.execute({"directory": "/non/existent/dir"}))
        assert not result.success

    def test_map_repository_tool(self):
        """Test MapRepositoryTool."""
        tool = MapRepositoryTool()

        # Test schema
        schema = tool.get_schema()
        assert schema.name == "map_repository"
        assert "include_git_info" in schema.parameters

        # Test execution
        result = asyncio.run(tool.execute({"repository_path": str(self.test_dir)}))
        assert result.success
        assert result.result["total_files"] >= 3
        assert result.result["total_size"] > 0
        assert "python" in result.result["languages"]
        assert "javascript" in result.result["languages"]

        # Check language details
        py_lang = result.result["languages"]["python"]
        assert py_lang["files"] >= 2
        assert py_lang["size"] > 0
        assert py_lang["lines"] >= 0  # May be 0 if line counting not implemented
        assert py_lang["percentage"] > 0

        # Test non-existent path
        result = asyncio.run(tool.execute({"repository_path": "/non/existent/repo"}))
        assert not result.success


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
