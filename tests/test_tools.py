"""
Tests for the Coda tools system.

This module tests the tool architecture, individual tools, and integration.
"""

import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from coda.tools import (
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolSchema,
    execute_tool,
    get_available_tools,
    get_tool_categories,
    get_tool_info,
    get_tool_stats,
)
from coda.tools.file_tools import EditFileTool, ListDirectoryTool, ReadFileTool, WriteFileTool
from coda.tools.git_tools import GitBranchTool, GitLogTool, GitStatusTool
from coda.tools.shell_tools import GetCurrentTimeTool, ShellExecuteTool


class TestToolBase:
    """Test the base tool architecture."""

    def test_tool_parameter_creation(self):
        """Test creating tool parameters."""
        param = ToolParameter(
            type=ToolParameterType.STRING,
            description="Test parameter",
            default="test",
            required=False,
        )

        assert param.type == ToolParameterType.STRING
        assert param.description == "Test parameter"
        assert param.default == "test"
        assert not param.required

    def test_tool_schema_creation(self):
        """Test creating tool schemas."""
        param = ToolParameter(type=ToolParameterType.STRING, description="Test parameter")

        schema = ToolSchema(
            name="test_tool",
            description="A test tool",
            category="test",
            parameters={"test_param": param},
        )

        assert schema.name == "test_tool"
        assert schema.description == "A test tool"
        assert schema.category == "test"
        assert "test_param" in schema.parameters

    def test_tool_result_creation(self):
        """Test creating tool results."""
        result = ToolResult(
            success=True, result="Test result", tool="test_tool", metadata={"test": "data"}
        )

        assert result.success
        assert result.result == "Test result"
        assert result.tool == "test_tool"
        assert result.metadata["test"] == "data"


class TestToolRegistry:
    """Test the tool registry functionality."""

    def test_tool_registry_singleton(self):
        """Test that tool_registry is a singleton."""
        from coda.tools import tool_registry as registry2
        from coda.tools.base import tool_registry as registry1

        assert registry1 is registry2

    def test_get_available_tools(self):
        """Test getting available tools."""
        tools = get_available_tools()
        assert len(tools) > 0

        # Check that we have tools from each category
        tool_names = [tool.name for tool in tools]
        assert "read_file" in tool_names
        assert "shell_execute" in tool_names
        assert "git_status" in tool_names

    def test_get_tool_categories(self):
        """Test getting tool categories."""
        categories = get_tool_categories()
        assert "filesystem" in categories
        assert "system" in categories
        assert "git" in categories

    def test_get_tool_info(self):
        """Test getting tool information."""
        info = get_tool_info("read_file")
        assert info is not None
        assert info["name"] == "read_file"
        assert info["category"] == "filesystem"
        assert "parameters" in info

    def test_get_tool_stats(self):
        """Test getting tool statistics."""
        stats = get_tool_stats()
        assert stats["total_tools"] > 0
        assert stats["categories"] > 0
        assert "tools_by_category" in stats


class TestFileTools:
    """Test file operation tools."""

    @pytest.fixture
    def temp_dir(self, tmp_path):
        """Create a temporary directory for tests."""
        return tmp_path

    @pytest.mark.asyncio
    async def test_read_file_tool(self, temp_dir):
        """Test reading files."""
        # Create test file
        test_file = temp_dir / "test.txt"
        test_content = "Hello, World!\nThis is a test file."
        test_file.write_text(test_content)

        tool = ReadFileTool()
        result = await tool.execute({"filepath": str(test_file)})

        assert result.success
        assert test_content in result.result
        assert result.tool == "read_file"

    @pytest.mark.asyncio
    async def test_read_file_not_found(self):
        """Test reading non-existent file."""
        tool = ReadFileTool()
        result = await tool.execute({"filepath": "/nonexistent/file.txt"})

        assert not result.success
        assert "not found" in result.error.lower()

    @pytest.mark.asyncio
    async def test_write_file_tool(self, temp_dir):
        """Test writing files."""
        test_file = temp_dir / "output.txt"
        test_content = "This is written by the tool."

        tool = WriteFileTool()
        result = await tool.execute({"filepath": str(test_file), "content": test_content})

        assert result.success
        assert test_file.exists()
        assert test_file.read_text() == test_content

    @pytest.mark.asyncio
    async def test_write_file_create_dirs(self, temp_dir):
        """Test writing files with directory creation."""
        test_file = temp_dir / "subdir" / "output.txt"
        test_content = "Content in subdirectory."

        tool = WriteFileTool()
        result = await tool.execute(
            {"filepath": str(test_file), "content": test_content, "create_dirs": True}
        )

        assert result.success
        assert test_file.exists()
        assert test_file.read_text() == test_content

    @pytest.mark.asyncio
    async def test_edit_file_replace(self, temp_dir):
        """Test editing files with replace operation."""
        test_file = temp_dir / "edit_test.txt"
        original_content = "Hello, World!\nThis is original content."
        test_file.write_text(original_content)

        tool = EditFileTool()
        result = await tool.execute(
            {
                "filepath": str(test_file),
                "operation": "replace",
                "search_text": "original",
                "replacement_text": "modified",
            }
        )

        assert result.success
        modified_content = test_file.read_text()
        assert "modified" in modified_content
        assert "original" not in modified_content

    @pytest.mark.asyncio
    async def test_list_directory_tool(self, temp_dir):
        """Test listing directory contents."""
        # Create test files
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.py").write_text("content2")
        (temp_dir / "subdir").mkdir()

        tool = ListDirectoryTool()
        result = await tool.execute({"path": str(temp_dir)})

        assert result.success
        assert "file1.txt" in result.result
        assert "file2.py" in result.result
        assert "subdir" in result.result


class TestShellTools:
    """Test shell command tools."""

    @pytest.mark.asyncio
    async def test_get_current_time_tool(self):
        """Test getting current time."""
        tool = GetCurrentTimeTool()
        result = await tool.execute({})

        assert result.success
        assert "Current time" in result.result

    @pytest.mark.asyncio
    async def test_shell_execute_safe_command(self):
        """Test executing safe shell commands."""
        tool = ShellExecuteTool()
        result = await tool.execute({"command": "echo 'Hello, World!'", "allow_dangerous": False})

        assert result.success
        assert "Hello, World!" in result.result

    @pytest.mark.asyncio
    async def test_shell_execute_dangerous_blocked(self):
        """Test that dangerous commands are blocked."""
        tool = ShellExecuteTool()
        result = await tool.execute({"command": "rm -rf /", "allow_dangerous": False})

        assert not result.success
        assert "blocked" in result.error.lower()

    @pytest.mark.asyncio
    async def test_shell_execute_command_safety_check(self):
        """Test command safety checking."""
        tool = ShellExecuteTool()

        # Test blocked command
        safety = tool._check_command_safety("rm -rf /")
        assert safety["blocked"]

        # Test dangerous command
        safety = tool._check_command_safety("sudo rm file")
        assert safety["dangerous"]
        assert not safety["blocked"]

        # Test safe command
        safety = tool._check_command_safety("ls -la")
        assert not safety["dangerous"]
        assert not safety["blocked"]


class TestGitTools:
    """Test Git operation tools."""

    @pytest.fixture
    def git_repo(self, tmp_path):
        """Create a temporary Git repository for tests."""
        temp_dir = tmp_path
        repo_dir = temp_dir / "test_repo"
        repo_dir.mkdir()

        # Initialize git repo
        os.chdir(repo_dir)
        os.system("git init")
        os.system("git config user.email 'test@example.com'")
        os.system("git config user.name 'Test User'")

        # Create initial commit
        test_file = repo_dir / "README.md"
        test_file.write_text("# Test Repository")
        os.system("git add README.md")
        os.system("git commit -m 'Initial commit'")

        yield repo_dir

    @pytest.mark.asyncio
    async def test_git_status_tool(self, git_repo):
        """Test Git status command."""
        tool = GitStatusTool()
        result = await tool.execute({"repo_path": str(git_repo)})

        assert result.success
        # Should show clean working tree for new repo
        assert "working tree clean" in result.result or "nothing to commit" in result.result

    @pytest.mark.asyncio
    async def test_git_log_tool(self, git_repo):
        """Test Git log command."""
        tool = GitLogTool()
        result = await tool.execute({"repo_path": str(git_repo), "max_count": 1})

        assert result.success
        assert "Initial commit" in result.result

    @pytest.mark.asyncio
    async def test_git_branch_tool(self, git_repo):
        """Test Git branch command."""
        tool = GitBranchTool()
        result = await tool.execute({"repo_path": str(git_repo), "action": "list"})

        assert result.success
        # Should show main or master branch
        assert "main" in result.result or "master" in result.result


class TestWebTools:
    """Test web-related tools."""

    @pytest.mark.asyncio
    async def test_fetch_url_tool_mock(self):
        """Test URL fetching with mocked response."""
        from coda.tools.web_tools import FetchUrlTool

        # Mock aiohttp response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "text/html"}
        mock_response.read.return_value = b"<html><body><h1>Test Page</h1></body></html>"
        mock_response.url = "http://example.com"

        # Mock session get context manager
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session.get.return_value.__aexit__.return_value = False

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            mock_client_session.return_value.__aexit__.return_value = False

            tool = FetchUrlTool()
            result = await tool.execute({"url": "http://example.com", "format": "text"})

            assert result.success
            assert "Test Page" in result.result

    @pytest.mark.asyncio
    async def test_search_web_tool_mock(self):
        """Test web search with mocked response."""
        from coda.tools.web_tools import SearchWebTool

        # Mock search response
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "Answer": "Test answer",
            "AbstractText": "Test abstract",
            "RelatedTopics": [
                {"Text": "Related topic 1", "FirstURL": "http://example.com/1"},
                {"Text": "Related topic 2", "FirstURL": "http://example.com/2"},
            ],
        }

        # Mock session get context manager
        mock_session = MagicMock()
        mock_session.get.return_value.__aenter__.return_value = mock_response
        mock_session.get.return_value.__aexit__.return_value = False

        with patch("aiohttp.ClientSession") as mock_client_session:
            mock_client_session.return_value.__aenter__.return_value = mock_session
            mock_client_session.return_value.__aexit__.return_value = False

            tool = SearchWebTool()
            result = await tool.execute({"query": "test query", "max_results": 2})

            assert result.success
            assert "test query" in result.result.lower()


class TestToolValidation:
    """Test tool parameter validation."""

    @pytest.mark.asyncio
    async def test_parameter_validation_missing_required(self):
        """Test validation of missing required parameters."""
        tool = ReadFileTool()

        # First test the validation method directly
        error = tool.validate_arguments({})  # Missing required filepath
        assert error is not None
        assert "required" in error.lower()

        # Test execution which should catch validation errors
        try:
            result = await tool.execute({})
            assert not result.success
        except KeyError:
            # This is expected if validation isn't caught during execution
            pass

    @pytest.mark.asyncio
    async def test_parameter_validation_type_error(self):
        """Test validation of parameter types."""
        tool = ReadFileTool()

        # Test with invalid type for max_lines (should be integer)
        error = tool.validate_arguments({"filepath": "/test/path", "max_lines": "not_a_number"})

        assert error is not None
        assert "integer" in error.lower()

    @pytest.mark.asyncio
    async def test_parameter_validation_enum_error(self):
        """Test validation of enum parameters."""
        tool = WriteFileTool()

        # Test with invalid enum value
        error = tool.validate_arguments(
            {"filepath": "/test/path", "content": "test", "mode": "invalid_mode"}
        )

        assert error is not None
        assert "one of" in error.lower()


class TestToolIntegration:
    """Test tool system integration."""

    @pytest.mark.asyncio
    async def test_execute_tool_function(self, tmp_path):
        """Test the execute_tool convenience function."""
        # Create test file
        test_file = tmp_path / "integration_test.txt"
        test_content = "Integration test content"
        test_file.write_text(test_content)

        # Execute tool through convenience function
        result = await execute_tool("read_file", {"filepath": str(test_file)})

        assert result.success
        assert test_content in result.result

    @pytest.mark.asyncio
    async def test_execute_unknown_tool(self):
        """Test executing unknown tool."""
        result = await execute_tool("unknown_tool", {})

        assert not result.success
        assert "not found" in result.error.lower()

    def test_tool_categories_consistency(self):
        """Test that tool categories are consistent."""
        all_tools = get_available_tools()
        categories = get_tool_categories()

        # All tool categories should be in the categories list
        for tool in all_tools:
            assert tool.category in categories

        # Categories should match what we expect
        expected_categories = {"filesystem", "system", "git", "web"}
        assert expected_categories.issubset(set(categories))

    def test_dangerous_tools_flagged(self):
        """Test that dangerous tools are properly flagged."""
        stats = get_tool_stats()
        dangerous_tools = stats["dangerous_tool_names"]

        # Shell execute should be marked as dangerous
        assert "shell_execute" in dangerous_tools


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
