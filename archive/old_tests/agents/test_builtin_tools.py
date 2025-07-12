"""Unit tests for built-in agent tools."""

import os
import subprocess
from datetime import datetime
from unittest.mock import patch

import pytest

from coda.agents.builtin_tools import (
    fetch_data,
    format_json,
    get_builtin_tools,
    get_current_directory,
    get_datetime,
    list_files,
    parse_json,
    read_file,
    run_command,
    write_file,
)


class TestBuiltinTools:
    """Test all built-in tools."""

    def test_get_current_directory(self):
        """Test getting current directory."""
        result = get_current_directory()
        assert result == os.getcwd()
        assert os.path.isabs(result)

    def test_list_files(self, tmp_path):
        """Test listing files in a directory."""
        # Create test files
        (tmp_path / "file1.txt").write_text("content1")
        (tmp_path / "file2.py").write_text("content2")
        (tmp_path / "subdir").mkdir()

        # Test listing files
        files = list_files(str(tmp_path))
        assert sorted(files) == ["file1.txt", "file2.py", "subdir"]

        # Test default (current directory)
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            files = list_files()
            assert sorted(files) == ["file1.txt", "file2.py", "subdir"]
        finally:
            os.chdir(original_cwd)

        # Test non-existent directory
        result = list_files("/non/existent/path")
        assert len(result) == 1
        assert "Error listing directory" in result[0]

    def test_read_file(self, tmp_path):
        """Test reading file contents."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_content = "Hello\nWorld\n🚀"
        test_file.write_text(test_content, encoding="utf-8")

        # Test successful read
        content = read_file(str(test_file))
        assert content == test_content

        # Test non-existent file
        result = read_file("/non/existent/file.txt")
        assert "Error reading file" in result

        # Test reading binary file (should fail gracefully)
        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03")
        result = read_file(str(binary_file))
        # Should either read with some encoding issues or error
        assert isinstance(result, str)

    def test_write_file(self, tmp_path):
        """Test writing file contents."""
        test_file = tmp_path / "output.txt"
        test_content = "Test content\nwith multiple lines\n"

        # Test successful write
        result = write_file(str(test_file), test_content)
        assert "Successfully wrote to" in result
        assert test_file.read_text() == test_content

        # Test overwriting existing file
        new_content = "New content"
        result = write_file(str(test_file), new_content)
        assert "Successfully wrote to" in result
        assert test_file.read_text() == new_content

        # Test writing to protected location
        result = write_file("/root/protected.txt", "content")
        assert "Error writing file" in result

        # Test writing unicode content
        unicode_content = "Unicode: 你好世界 🌍"
        unicode_file = tmp_path / "unicode.txt"
        result = write_file(str(unicode_file), unicode_content)
        assert "Successfully wrote to" in result
        assert unicode_file.read_text(encoding="utf-8") == unicode_content

    def test_run_command(self):
        """Test executing shell commands."""
        # Test successful command
        result = run_command("echo 'Hello World'")
        assert result["success"] is True
        assert result["returncode"] == 0
        assert "Hello World" in result["stdout"]
        assert result["stderr"] == ""

        # Test command with error
        result = run_command("ls /non/existent/directory")
        assert result["success"] is False
        assert result["returncode"] != 0
        assert result["stderr"] != ""

        # Test command with both stdout and stderr
        result = run_command("echo 'stdout' && echo 'stderr' >&2")
        assert "stdout" in result["stdout"]
        assert "stderr" in result["stderr"]

        # Test timeout
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("cmd", 30)):
            result = run_command("sleep 60")
            assert result["success"] is False
            assert "timed out" in result["stderr"]
            assert result["returncode"] == -1

    def test_get_datetime(self):
        """Test getting current datetime."""
        before = datetime.now()
        result = get_datetime()
        after = datetime.now()

        # Parse the result
        parsed = datetime.fromisoformat(result)

        # Check it's between before and after
        assert before <= parsed <= after

        # Check format
        assert "T" in result  # ISO format includes T separator
        assert len(result) > 15  # Should include date and time

    def test_parse_json(self):
        """Test JSON parsing."""
        # Test valid JSON
        valid_json = '{"name": "test", "value": 42, "items": [1, 2, 3]}'
        result = parse_json(valid_json)
        assert result == {"name": "test", "value": 42, "items": [1, 2, 3]}

        # Test empty object
        assert parse_json("{}") == {}

        # Test array
        assert parse_json("[1, 2, 3]") == [1, 2, 3]

        # Test invalid JSON
        result = parse_json("not valid json")
        assert "error" in result
        assert "Invalid JSON" in result["error"]

        # Test malformed JSON
        result = parse_json('{"key": value}')  # value not quoted
        assert "error" in result

        # Test unicode
        unicode_json = '{"message": "Hello 世界"}'
        result = parse_json(unicode_json)
        assert result["message"] == "Hello 世界"

    def test_format_json(self):
        """Test JSON formatting."""
        # Test basic formatting
        data = {"name": "test", "value": 42, "items": [1, 2, 3]}
        result = format_json(data)
        assert isinstance(result, str)
        assert '"name": "test"' in result
        assert '"value": 42' in result

        # Test with custom indent
        result_indent4 = format_json(data, indent=4)
        assert result_indent4.count(" " * 4) > 0

        # Test sorting keys
        data_unsorted = {"z": 1, "a": 2, "m": 3}
        result = format_json(data_unsorted)
        lines = result.strip().split("\n")
        # Check that 'a' comes before 'z' in the output
        a_index = next(i for i, line in enumerate(lines) if '"a"' in line)
        z_index = next(i for i, line in enumerate(lines) if '"z"' in line)
        assert a_index < z_index

        # Test with non-serializable data
        class CustomObject:
            pass

        result = format_json({"obj": CustomObject()})
        assert "Error formatting JSON" in result

    @pytest.mark.asyncio
    async def test_fetch_data(self):
        """Test async data fetching simulation."""
        url = "https://api.example.com/data"

        start_time = datetime.now()
        result = await fetch_data(url)
        end_time = datetime.now()

        # Check response structure
        assert result["url"] == url
        assert result["status"] == 200
        assert "data" in result
        assert result["data"]["message"] == "This is simulated data"
        assert "timestamp" in result["data"]

        # Check that it actually waited (simulated delay)
        elapsed = (end_time - start_time).total_seconds()
        assert elapsed >= 0.5  # Should wait at least 0.5 seconds

    def test_get_builtin_tools(self):
        """Test getting all built-in tools."""
        tools = get_builtin_tools()

        # Check we have the expected number of tools
        assert len(tools) == 9

        # Check all tools are included
        expected_tools = {
            get_current_directory,
            list_files,
            read_file,
            write_file,
            run_command,
            get_datetime,
            parse_json,
            format_json,
            fetch_data,
        }
        assert set(tools) == expected_tools

        # Check all tools have the required attributes
        for tool in tools:
            assert hasattr(tool, "_is_tool")
            assert hasattr(tool, "_tool_name")
            assert hasattr(tool, "_tool_description")
            assert tool._is_tool is True

    def test_tool_decorations(self):
        """Test that all tools are properly decorated."""
        tools = get_builtin_tools()

        for tool in tools:
            # Check tool attributes
            assert hasattr(tool, "_is_tool")
            assert tool._is_tool is True

            # Check tool has name and description
            assert hasattr(tool, "_tool_name")
            assert hasattr(tool, "_tool_description")
            assert tool._tool_name
            assert tool._tool_description

            # Check callable
            assert callable(tool)

    def test_edge_cases(self, tmp_path):
        """Test edge cases for various tools."""
        # Test empty file
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")
        assert read_file(str(empty_file)) == ""

        # Test file with only whitespace
        whitespace_file = tmp_path / "whitespace.txt"
        whitespace_file.write_text("   \n\t\n   ")
        assert read_file(str(whitespace_file)) == "   \n\t\n   "

        # Test very long file path
        long_path = tmp_path / ("a" * 200 + ".txt")
        try:
            write_file(str(long_path), "content")
            # Should either succeed or fail gracefully
        except Exception:
            pass

        # Test command with special characters
        result = run_command("echo 'test \"quotes\" and $vars'")
        assert "test" in result["stdout"]

        # Test JSON with nested structures
        nested_data = {"level1": {"level2": {"level3": [1, 2, 3]}}}
        formatted = format_json(nested_data)
        assert "level3" in formatted

    @pytest.mark.parametrize(
        "command,expected_success",
        [
            ("true", True),
            ("false", False),
            ("exit 0", True),
            ("exit 1", False),
        ],
    )
    def test_run_command_exit_codes(self, command, expected_success):
        """Test various command exit codes."""
        result = run_command(command)
        assert result["success"] == expected_success
