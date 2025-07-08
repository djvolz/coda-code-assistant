"""
Comprehensive tests for all Coda tools using MockProvider.

This module tests the complete tool system integration with the MockProvider,
ensuring all tools work correctly in an AI assistant context without external dependencies.
"""

import os
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coda.agents import Agent
from coda.agents.builtin_tools import get_builtin_tools
from coda.providers import MockProvider
from coda.tools import (
    execute_tool,
    get_available_tools,
    get_tool_categories,
    get_tool_info,
    get_tool_stats,
)


class TestToolSystemWithMockProvider:
    """Test the entire tool system using MockProvider."""

    @pytest.fixture
    def mock_provider(self):
        """Create a MockProvider instance."""
        return MockProvider()

    @pytest.fixture
    def agent_with_tools(self, mock_provider):
        """Create an Agent with all available tools."""
        agent = Agent(provider=mock_provider, tools=get_builtin_tools())
        return agent

    @pytest.mark.asyncio
    async def test_tool_registry_initialization(self):
        """Test that all tools are properly registered."""
        # Get all available tools
        tools = get_available_tools()
        assert len(tools) > 0

        # Check categories
        categories = get_tool_categories()
        expected_categories = ["filesystem", "system", "git", "web"]
        for cat in expected_categories:
            assert cat in categories

        # Check specific tools are registered
        tool_names = [tool.name for tool in tools]
        expected_tools = [
            "read_file",
            "write_file",
            "edit_file",
            "list_directory",
            "shell_execute",
            "get_current_time",
            "git_status",
            "git_log",
            "git_diff",
            "git_branch",
            "fetch_url",
            "search_web",
        ]
        for tool_name in expected_tools:
            assert tool_name in tool_names

    @pytest.mark.asyncio
    async def test_tool_stats_and_info(self):
        """Test tool statistics and information retrieval."""
        # Test stats
        stats = get_tool_stats()
        assert stats["total_tools"] > 0
        assert stats["categories"] > 0
        assert "dangerous_tools" in stats
        assert "shell_execute" in stats["dangerous_tool_names"]

        # Test tool info
        info = get_tool_info("read_file")
        assert info["name"] == "read_file"
        assert info["category"] == "filesystem"
        assert "filepath" in info["parameters"]


class TestFileToolsWithMockProvider:
    """Test file operation tools with MockProvider."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for file tests."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_read_file_tool(self, temp_dir):
        """Test reading files through the tool system."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_content = "Hello from test file!\nThis is line 2."
        test_file.write_text(test_content)

        # Execute tool
        result = await execute_tool("read_file", {"filepath": str(test_file)})

        assert result.success
        assert test_content in result.result
        assert result.tool == "read_file"

        # Test with max_lines parameter
        result = await execute_tool("read_file", {"filepath": str(test_file), "max_lines": 1})

        assert result.success
        assert "Hello from test file!" in result.result
        assert "line 2" not in result.result

    @pytest.mark.asyncio
    async def test_write_file_tool(self, temp_dir):
        """Test writing files through the tool system."""
        test_file = temp_dir / "output.txt"
        test_content = "Content written by tool"

        # Execute tool
        result = await execute_tool(
            "write_file", {"filepath": str(test_file), "content": test_content}
        )

        assert result.success
        assert test_file.exists()
        assert test_file.read_text() == test_content

        # Test append mode
        result = await execute_tool(
            "write_file",
            {"filepath": str(test_file), "content": "\nAppended content", "mode": "append"},
        )

        assert result.success
        assert test_file.read_text() == test_content + "\nAppended content"

    @pytest.mark.asyncio
    async def test_edit_file_tool(self, temp_dir):
        """Test editing files through the tool system."""
        test_file = temp_dir / "edit_test.txt"
        original_content = "Line 1\nLine 2 with target text\nLine 3"
        test_file.write_text(original_content)

        # Test replace operation
        result = await execute_tool(
            "edit_file",
            {
                "filepath": str(test_file),
                "operation": "replace",
                "search_text": "target text",
                "replacement_text": "modified text",
            },
        )

        assert result.success
        content = test_file.read_text()
        assert "modified text" in content
        assert "target text" not in content

        # Test insert operation
        result = await execute_tool(
            "edit_file",
            {
                "filepath": str(test_file),
                "operation": "insert",
                "line_number": 2,
                "replacement_text": "Inserted line",
            },
        )

        assert result.success
        lines = test_file.read_text().splitlines()
        assert lines[1] == "Inserted line"

    @pytest.mark.asyncio
    async def test_list_directory_tool(self, temp_dir):
        """Test listing directory contents through the tool system."""
        # Create test structure
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.py").write_text("content2")
        (temp_dir / "subdir").mkdir()
        (temp_dir / "subdir" / "nested.txt").write_text("nested")

        # List directory
        result = await execute_tool("list_directory", {"path": str(temp_dir)})

        assert result.success
        assert "file1.txt" in result.result
        assert "file2.py" in result.result
        assert "subdir" in result.result

        # Test recursive listing
        result = await execute_tool("list_directory", {"path": str(temp_dir), "recursive": True})

        assert result.success
        assert "nested.txt" in result.result
        assert "subdir" in result.result


class TestShellToolsWithMockProvider:
    """Test shell and system tools with MockProvider."""

    @pytest.mark.asyncio
    async def test_get_current_time_tool(self):
        """Test getting current time through the tool system."""
        result = await execute_tool("get_current_time", {})

        assert result.success
        assert "Current time" in result.result
        # Verify it contains a valid timestamp (as Unix timestamp)
        timestamp = result.metadata["timestamp"]
        dt = datetime.fromtimestamp(timestamp)
        assert datetime.now().year == dt.year

    @pytest.mark.asyncio
    async def test_shell_execute_safe_commands(self):
        """Test executing safe shell commands."""
        # Test echo command
        result = await execute_tool(
            "shell_execute", {"command": "echo 'Hello from shell'", "allow_dangerous": False}
        )

        assert result.success
        assert "Hello from shell" in result.result

        # Test pwd command
        result = await execute_tool("shell_execute", {"command": "pwd"})

        assert result.success
        assert "/" in result.result  # Should contain a path

    @pytest.mark.asyncio
    async def test_shell_execute_dangerous_commands(self):
        """Test handling of dangerous shell commands."""
        # Test blocked command
        result = await execute_tool(
            "shell_execute", {"command": "rm -rf /", "allow_dangerous": False}
        )

        assert not result.success
        assert "blocked" in result.error.lower()

        # Test dangerous command that requires approval
        result = await execute_tool(
            "shell_execute", {"command": "sudo apt-get install package", "allow_dangerous": False}
        )

        assert not result.success
        assert "dangerous" in result.error.lower() or "requires approval" in result.error.lower()

    @pytest.mark.asyncio
    async def test_shell_execute_with_timeout(self):
        """Test shell command timeout handling."""
        # Mock a long-running command
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = TimeoutError()

            result = await execute_tool(
                "shell_execute", {"command": "sleep 60", "timeout": 1, "allow_dangerous": True}
            )

            assert not result.success
            assert "timed out" in result.error.lower()


class TestGitToolsWithMockProvider:
    """Test Git tools with MockProvider."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary Git repository."""
        repo_dir = tmp_path / "test_repo"
        repo_dir.mkdir()

        # Initialize repo
        os.chdir(repo_dir)
        os.system("git init -q")
        os.system("git config user.email 'test@example.com'")
        os.system("git config user.name 'Test User'")

        # Create initial commit
        readme = repo_dir / "README.md"
        readme.write_text("# Test Repository")
        os.system("git add README.md")
        os.system("git commit -q -m 'Initial commit'")

        yield repo_dir

        # Cleanup
        os.chdir("/")

    @pytest.mark.asyncio
    async def test_git_status_tool(self, git_repo):
        """Test Git status tool."""
        result = await execute_tool("git_status", {"repo_path": str(git_repo)})

        assert result.success
        assert "working tree clean" in result.result or "nothing to commit" in result.result

        # Create uncommitted change
        test_file = git_repo / "new_file.txt"
        test_file.write_text("New content")

        result = await execute_tool("git_status", {"repo_path": str(git_repo)})

        assert result.success
        assert "new_file.txt" in result.result

    @pytest.mark.asyncio
    async def test_git_log_tool(self, git_repo):
        """Test Git log tool."""
        result = await execute_tool("git_log", {"repo_path": str(git_repo), "max_count": 5})

        assert result.success
        assert "Initial commit" in result.result
        assert "Test User" in result.result

    @pytest.mark.asyncio
    async def test_git_diff_tool(self, git_repo):
        """Test Git diff tool."""
        # Modify existing file
        readme = git_repo / "README.md"
        readme.write_text("# Test Repository\n\nModified content")

        result = await execute_tool("git_diff", {"repo_path": str(git_repo)})

        assert result.success
        assert "Modified content" in result.result
        assert "@@" in result.result  # Diff markers

    @pytest.mark.asyncio
    async def test_git_branch_tool(self, git_repo):
        """Test Git branch operations."""
        # List branches
        result = await execute_tool("git_branch", {"repo_path": str(git_repo), "action": "list"})

        assert result.success
        assert "main" in result.result or "master" in result.result

        # Create new branch
        result = await execute_tool(
            "git_branch",
            {"repo_path": str(git_repo), "action": "create", "branch_name": "feature/test"},
        )

        assert result.success
        assert "feature/test" in result.result


class TestWebToolsWithMockProvider:
    """Test web-related tools with MockProvider."""

    @pytest.mark.asyncio
    async def test_fetch_url_tool_mocked(self):
        """Test URL fetching with mocked responses."""
        # Mock aiohttp response
        with patch("aiohttp.ClientSession") as mock_session_patch:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"content-type": "text/html"}
            mock_response.read.return_value = b"""
            <html>
                <head><title>Test Page</title></head>
                <body>
                    <h1>Welcome</h1>
                    <p>This is a test page.</p>
                </body>
            </html>
            """
            mock_response.url = "http://example.com"

            mock_session = MagicMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aexit__.return_value = False

            mock_session_patch.return_value.__aenter__.return_value = mock_session
            mock_session_patch.return_value.__aexit__.return_value = False

            result = await execute_tool(
                "fetch_url", {"url": "http://example.com", "format": "markdown"}
            )

            assert result.success
            assert "# Welcome" in result.result
            assert "This is a test page" in result.result

    @pytest.mark.asyncio
    async def test_search_web_tool_mocked(self):
        """Test web search with mocked responses."""
        with patch("aiohttp.ClientSession") as mock_session_patch:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.headers = {"content-type": "application/json"}
            mock_response.json.return_value = {
                "Answer": "Python is a programming language",
                "AbstractText": "Python is an interpreted, high-level programming language.",
                "RelatedTopics": [
                    {
                        "Text": "Python (programming language) - Wikipedia",
                        "FirstURL": "https://en.wikipedia.org/wiki/Python",
                    },
                    {"Text": "Python.org - Official site", "FirstURL": "https://python.org"},
                ],
            }

            mock_session = MagicMock()
            mock_session.get.return_value.__aenter__.return_value = mock_response
            mock_session.get.return_value.__aexit__.return_value = False

            mock_session_patch.return_value.__aenter__.return_value = mock_session
            mock_session_patch.return_value.__aexit__.return_value = False

            result = await execute_tool(
                "search_web", {"query": "What is Python programming?", "max_results": 5}
            )

            assert result.success
            assert "Python" in result.result
            assert "programming language" in result.result


class TestBuiltinToolsWithMockProvider:
    """Test builtin tools from agents module with MockProvider."""

    @pytest.mark.asyncio
    async def test_builtin_get_current_directory(self):
        """Test builtin get_current_directory tool."""
        from coda.agents.builtin_tools import get_current_directory

        result = get_current_directory()
        assert isinstance(result, str)
        assert os.path.exists(result)

    @pytest.mark.asyncio
    async def test_builtin_list_files(self, tmp_path):
        """Test builtin list_files tool."""
        from coda.agents.builtin_tools import list_files

        # Create test files
        (tmp_path / "file1.txt").write_text("content")
        (tmp_path / "file2.py").write_text("code")

        result = list_files(str(tmp_path))
        assert isinstance(result, list)
        assert "file1.txt" in result
        assert "file2.py" in result

    @pytest.mark.asyncio
    async def test_builtin_read_write_file(self, tmp_path):
        """Test builtin read_file and write_file tools."""
        from coda.agents.builtin_tools import read_file, write_file

        test_file = tmp_path / "test.txt"
        test_content = "Hello from builtin tools!"

        # Write file
        write_result = write_file(str(test_file), test_content)
        assert "Successfully wrote" in write_result

        # Read file
        read_result = read_file(str(test_file))
        assert read_result == test_content

    @pytest.mark.asyncio
    async def test_builtin_run_command(self):
        """Test builtin run_command tool."""
        from coda.agents.builtin_tools import run_command

        result = run_command("echo 'Hello World'")
        assert isinstance(result, dict)
        assert result["success"]
        assert "Hello World" in result["stdout"]

    @pytest.mark.asyncio
    async def test_builtin_datetime_tools(self):
        """Test builtin datetime tools."""
        from coda.agents.builtin_tools import get_datetime

        result = get_datetime()
        assert isinstance(result, str)
        # Should be ISO format
        datetime.fromisoformat(result)

    @pytest.mark.asyncio
    async def test_builtin_json_tools(self):
        """Test builtin JSON tools."""
        from coda.agents.builtin_tools import format_json, parse_json

        # Test parse_json
        json_str = '{"name": "test", "value": 42}'
        parsed = parse_json(json_str)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42

        # Test format_json
        data = {"key": "value", "number": 123}
        formatted = format_json(data)
        assert isinstance(formatted, str)
        assert "key" in formatted
        assert "123" in formatted

    @pytest.mark.asyncio
    async def test_builtin_fetch_data(self):
        """Test builtin async fetch_data tool."""
        from coda.agents.builtin_tools import fetch_data

        result = await fetch_data("http://example.com/api")
        assert isinstance(result, dict)
        assert result["url"] == "http://example.com/api"
        assert result["status"] == 200
        assert "data" in result


class TestToolErrorHandling:
    """Test error handling in tools."""

    @pytest.mark.asyncio
    async def test_invalid_tool_name(self):
        """Test executing non-existent tool."""
        result = await execute_tool("non_existent_tool", {})

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_missing_required_parameters(self):
        """Test tools with missing required parameters."""
        # read_file requires filepath
        result = await execute_tool("read_file", {})

        assert not result.success
        assert "required" in result.error.lower() or "missing" in result.error.lower()

    @pytest.mark.asyncio
    async def test_invalid_parameter_types(self):
        """Test tools with invalid parameter types."""
        # max_lines should be integer
        result = await execute_tool(
            "read_file", {"filepath": "/tmp/test.txt", "max_lines": "not_a_number"}
        )

        # Tool should handle type conversion or error gracefully
        # The tool might convert string to int, or fail with type error
        if not result.success:
            assert any(
                word in result.error.lower() for word in ["type", "integer", "invalid", "int"]
            )

    @pytest.mark.asyncio
    async def test_permission_errors(self, tmp_path):
        """Test handling of permission errors."""
        import os
        import sys

        # Skip on Windows where permissions work differently
        if sys.platform == "win32":
            pytest.skip("Permission test not reliable on Windows")

        # Create read-only file
        test_file = tmp_path / "readonly.txt"
        test_file.write_text("Protected content")

        # Make file read-only
        os.chmod(str(test_file), 0o444)

        # Try to write to read-only file
        result = await execute_tool(
            "write_file", {"filepath": str(test_file), "content": "New content", "mode": "write"}
        )

        # On some systems, root can still write to read-only files
        if os.getuid() == 0:
            pytest.skip("Running as root, permission test not applicable")

        assert not result.success
        assert (
            "permission" in result.error.lower()
            or "denied" in result.error.lower()
            or "read-only" in result.error.lower()
        )


class TestToolIntegrationWithAgent:
    """Test tools integrated with Agent and MockProvider."""

    @pytest.mark.asyncio
    async def test_agent_tool_execution(self, tmp_path):
        """Test agent executing tools based on user prompts."""
        from coda.agents import Agent
        from coda.agents.builtin_tools import get_builtin_tools
        from coda.providers import MockProvider

        agent = Agent(provider=MockProvider(), model="mock-echo", tools=get_builtin_tools())

        # Create test file
        test_file = tmp_path / "agent_test.txt"
        test_file.write_text("Original content")

        # Test agent reading file
        response = await agent.run_async(f"Read the file at {test_file}")

        # MockProvider will echo but agent might execute tool
        assert response is not None
        assert response.data is not None
        assert response.data["content"] is not None

    @pytest.mark.asyncio
    async def test_multiple_tool_execution(self):
        """Test executing multiple tools in sequence."""
        # Get current time
        time_result = await execute_tool("get_current_time", {})
        assert time_result.success

        # Parse the timestamp as JSON
        from coda.agents.builtin_tools import parse_json

        timestamp_data = {
            "timestamp": time_result.metadata["timestamp"],
            "tool": "get_current_time",
        }

        # Format as JSON
        from coda.agents.builtin_tools import format_json

        json_result = format_json(timestamp_data)
        assert isinstance(json_result, str)

        # Parse it back
        parsed = parse_json(json_result)
        assert parsed["timestamp"] == time_result.metadata["timestamp"]


class TestToolPermissionsAndSafety:
    """Test tool permission system and safety features."""

    @pytest.mark.asyncio
    async def test_dangerous_tool_marking(self):
        """Test that dangerous tools are properly marked."""
        stats = get_tool_stats()

        # shell_execute should be marked dangerous
        assert "shell_execute" in stats["dangerous_tool_names"]

        # File operations should not be dangerous
        assert "read_file" not in stats["dangerous_tool_names"]
        assert "write_file" not in stats["dangerous_tool_names"]

    @pytest.mark.asyncio
    async def test_tool_category_organization(self):
        """Test tools are properly categorized."""
        tools_by_category = {}

        for tool in get_available_tools():
            category = tool.category
            if category not in tools_by_category:
                tools_by_category[category] = []
            tools_by_category[category].append(tool.name)

        # Verify categorization
        assert "read_file" in tools_by_category["filesystem"]
        assert "write_file" in tools_by_category["filesystem"]
        assert "shell_execute" in tools_by_category["system"]
        assert "git_status" in tools_by_category["git"]
        assert "fetch_url" in tools_by_category["web"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
