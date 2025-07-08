# Coda Tools System

The Coda Tools System provides AI assistants with the ability to perform actions in the real world through a comprehensive set of built-in tools. Based on the Model Context Protocol (MCP), it offers secure, validated, and extensible tool execution.

## Overview

Coda includes **12 built-in tools** across **4 categories**:
- **Filesystem**: File and directory operations
- **System**: System information and command execution  
- **Web**: Search and content fetching
- **Git**: Version control operations

## Quick Start

### Using Tools in Conversation

Tools are automatically available to the AI. Simply ask for tasks that require tool usage:

```
You: "Read the contents of README.md and summarize it"
AI: I'll read the README.md file for you.
[Uses read_file tool]
Based on the contents of README.md, here's a summary...
```

```
You: "What's the status of this git repository?"
AI: Let me check the git status.
[Uses git_status tool]
The repository has 3 modified files and 1 untracked file...
```

### Managing Tools via CLI

Use the `/tools` command to explore and manage available tools:

```bash
# Show tools overview
/tools

# List all tools
/tools list

# List tools by category
/tools list filesystem

# Get detailed information about a tool
/tools info read_file

# Show tool categories
/tools categories

# View tool statistics
/tools stats

# Get detailed help
/tools help
```

## Tool Categories

### Filesystem Tools

#### read_file
Read the contents of text files with encoding support and line limits.

**Parameters:**
- `filepath` (required): Path to the file to read
- `max_lines` (optional): Maximum number of lines to read (default: 1000)
- `encoding` (optional): File encoding (default: utf-8)

**Example:**
```
"Please read the first 50 lines of config.py"
```

#### write_file
Write content to files with backup and directory creation support.

**Parameters:**
- `filepath` (required): Path where to write the file
- `content` (required): Content to write
- `mode` (optional): 'write' (overwrite) or 'append' (default: write)
- `encoding` (optional): File encoding (default: utf-8)
- `create_dirs` (optional): Create parent directories (default: true)

**Example:**
```
"Create a new file called 'notes.txt' with the content 'Meeting notes from today'"
```

#### edit_file
Advanced file editing with replace, insert, and delete operations.

**Parameters:**
- `filepath` (required): Path to the file to edit
- `operation` (required): 'replace', 'insert', or 'delete'
- `search_text` (for replace): Text to search for
- `replacement_text` (for replace/insert): New text
- `line_number` (for insert/delete): Line number (1-based)
- `num_lines` (for delete): Number of lines to delete

**Examples:**
```
"Replace 'TODO: implement' with 'DONE: implemented' in main.py"
"Insert a comment 'Added logging support' at line 25 in utils.py"
"Delete lines 10-15 from old_code.py"
```

#### list_directory
List files and directories with optional recursion and hidden file support.

**Parameters:**
- `path` (optional): Directory path to list (default: current directory)
- `show_hidden` (optional): Show hidden files (default: false)
- `recursive` (optional): List subdirectories recursively (default: false)
- `max_depth` (optional): Maximum recursion depth (default: 3)

**Example:**
```
"Show me all Python files in the src/ directory, including subdirectories"
```

### System Tools

#### shell_execute ⚠️
Execute shell commands with comprehensive safety controls.

**Parameters:**
- `command` (required): Shell command to execute
- `working_directory` (optional): Working directory (default: current)
- `timeout` (optional): Timeout in seconds (default: 30)
- `capture_output` (optional): Capture command output (default: true)
- `allow_dangerous` (optional): Allow dangerous commands (default: false)
- `environment` (optional): Additional environment variables

**Safety Features:**
- Dangerous commands are blocked (rm -rf, sudo, etc.)
- Commands require explicit approval with `allow_dangerous=true`
- Timeout protection prevents hanging commands
- Safe command whitelist for common operations

**Examples:**
```
"Run 'npm test' to execute the test suite"
"List all Python files with 'find . -name \"*.py\"'"
"Show disk usage with 'df -h'" 
```

#### get_current_time
Get current system time with timezone and format options.

**Parameters:**
- `format` (optional): Time format string (default: %Y-%m-%d %H:%M:%S)
- `timezone` (optional): 'local' or 'utc' (default: local)

**Example:**
```
"What time is it in UTC?"
```

### Web Tools

#### fetch_url
Fetch content from URLs with automatic conversion to text or markdown.

**Parameters:**
- `url` (required): URL to fetch content from
- `max_length` (optional): Maximum content length (default: 10000)
- `timeout` (optional): Request timeout in seconds (default: 30)
- `format` (optional): 'raw', 'text', or 'markdown' (default: markdown)
- `follow_redirects` (optional): Follow HTTP redirects (default: true)
- `user_agent` (optional): Custom User-Agent string

**Example:**
```
"Fetch the content from https://example.com and convert it to markdown"
```

#### search_web
Search the web using DuckDuckGo with formatted results.

**Parameters:**
- `query` (required): Search query
- `max_results` (optional): Maximum results to return (default: 5)
- `region` (optional): Search region (default: us-en)
- `safe_search` (optional): Safe search level (default: moderate)
- `time_range` (optional): Time range filter

**Example:**
```
"Search for 'Python async programming best practices' and show me the top 3 results"
```

### Git Tools

#### git_status
Get the status of a Git repository with optional porcelain format.

**Parameters:**
- `repo_path` (optional): Path to Git repository (default: current directory)
- `porcelain` (optional): Use machine-readable format (default: false)

**Example:**
```
"What's the current status of this git repository?"
```

#### git_log
View Git commit history with filtering options.

**Parameters:**
- `repo_path` (optional): Path to Git repository (default: current directory)
- `max_count` (optional): Maximum commits to show (default: 10)
- `oneline` (optional): Show one commit per line (default: false)
- `since` (optional): Show commits since date (e.g., '2 weeks ago')
- `author` (optional): Filter by author
- `grep` (optional): Filter by commit message content

**Example:**
```
"Show me the last 5 commits by John Smith"
"Show commits from the last week with oneline format"
```

#### git_diff
Show changes between commits, working tree, or staged files.

**Parameters:**
- `repo_path` (optional): Path to Git repository (default: current directory)
- `target` (optional): Target for diff (commit hash, branch, or 'staged')
- `file_path` (optional): Specific file to diff
- `unified` (optional): Lines of context (default: 3)
- `stat` (optional): Show diffstat instead of full diff (default: false)

**Example:**
```
"Show me the changes in staged files"
"Compare the current working directory with the last commit"
```

#### git_branch
List, create, or delete Git branches.

**Parameters:**
- `repo_path` (optional): Path to Git repository (default: current directory)
- `action` (optional): 'list', 'create', 'delete', or 'current' (default: list)
- `branch_name` (optional): Branch name for create/delete actions
- `remote` (optional): Include remote branches in listing (default: false)
- `force` (optional): Force delete branch (default: false)

**Example:**
```
"List all branches including remote ones"
"Create a new branch called 'feature/new-api'"
```

## Safety and Security

### Dangerous Tools
Tools marked with ⚠️ require special attention:
- **shell_execute**: Can execute system commands with potential security risks

### Safety Controls
- **Command Filtering**: Dangerous shell commands are automatically blocked
- **Permission System**: Dangerous operations require explicit approval
- **Path Validation**: File operations use safe path resolution
- **Timeout Protection**: Commands have configurable timeouts
- **Error Handling**: Comprehensive error handling with clear messages

### Best Practices
1. **Review AI Requests**: Always review what tools the AI wants to use
2. **Dangerous Commands**: Be cautious when approving dangerous operations
3. **File Paths**: Use absolute paths when possible
4. **Backups**: Tools automatically create backups for destructive operations
5. **Testing**: Test commands in safe environments first

## Tool Development

### Adding New Tools

Create a new tool by inheriting from `BaseTool`:

```python
from coda.tools.base import BaseTool, ToolSchema, ToolParameter, ToolParameterType, ToolResult

class MyCustomTool(BaseTool):
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="my_tool",
            description="Description of what this tool does",
            category="custom",
            parameters={
                "param1": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Parameter description",
                    required=True
                )
            }
        )
    
    async def execute(self, arguments: dict) -> ToolResult:
        # Implement tool logic here
        return ToolResult(
            success=True,
            result="Tool execution result",
            tool="my_tool"
        )

# Register the tool
from coda.tools.base import tool_registry
tool_registry.register(MyCustomTool())
```

### Tool Architecture

- **BaseTool**: Abstract base class for all tools
- **ToolRegistry**: Global registry for tool management
- **ToolSchema**: Defines tool metadata and parameters
- **ToolResult**: Standardized result format
- **Parameter Validation**: Automatic validation based on schema

## Integration with Sessions

When session management is implemented, tool calls will be automatically logged:

- **Tool Invocations**: Stored with parameters and results
- **Session Replay**: Tool calls can be replayed in session branches
- **Search**: Find sessions by tool usage patterns
- **Analytics**: Track tool usage statistics

## Future Enhancements

### Planned Features
- **External MCP Servers**: Connect to external tool providers
- **Tool Permissions**: Fine-grained permission management
- **Tool Chaining**: Combine multiple tools in sequences
- **Custom Tool SDK**: Simplified tool development framework
- **Tool Marketplace**: Share and discover community tools

### MCP Compatibility
The tool system is designed to be fully compatible with the Model Context Protocol:
- Standard tool definitions
- Resource and prompt support
- External server integration
- Authentication and security

## Troubleshooting

### Common Issues

**Tool not found**
- Check tool name with `/tools list`
- Verify tool is properly registered

**Permission denied**
- Check if tool is marked as dangerous (⚠️)
- Use `allow_dangerous=true` for shell commands if needed
- Verify file/directory permissions

**Command timeout**
- Increase timeout parameter for long-running commands
- Check if command is hanging or requires input

**File encoding errors**
- Specify correct encoding parameter
- Try different encodings (utf-8, latin-1, etc.)

### Getting Help

Use the built-in help system:
```bash
/tools help              # Comprehensive tools help
/tools info <tool_name>  # Detailed tool information
/help                    # General CLI help
```

## API Reference

For detailed API documentation, see:
- `coda.tools.base` - Core tool architecture
- `coda.tools.file_tools` - Filesystem operations
- `coda.tools.shell_tools` - System operations
- `coda.tools.web_tools` - Web operations
- `coda.tools.git_tools` - Git operations