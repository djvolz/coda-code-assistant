"""
File operation tools for reading, writing, and editing files.

These tools provide safe file operations with proper error handling
and path validation.
"""

import os
import shutil
import time
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema, tool_registry


class ReadFileTool(BaseTool):
    """Tool for reading file contents."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="read_file",
            description="Read the contents of a text file",
            category="filesystem",
            parameters={
                "filepath": ToolParameter(
                    type=ToolParameterType.STRING, description="Path to the file to read"
                ),
                "max_lines": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Maximum number of lines to read",
                    default=1000,
                    required=False,
                    min_value=1,
                    max_value=10000,
                ),
                "encoding": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="File encoding",
                    default="utf-8",
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        filepath = arguments["filepath"]
        max_lines = arguments.get("max_lines", 1000)
        encoding = arguments.get("encoding", "utf-8")

        try:
            # Resolve path and check if it exists
            path = Path(filepath).resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {filepath}",
                    tool="read_file",
                    metadata={"requested_path": filepath},
                )

            if not path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Path is not a file: {filepath}",
                    tool="read_file",
                    metadata={"requested_path": filepath},
                )

            # Read file contents
            with open(path, encoding=encoding) as f:
                lines = f.readlines()

            # Apply line limit
            total_lines = len(lines)
            if total_lines > max_lines:
                content = "".join(lines[:max_lines])
                content += f"\n\n... (truncated, showing first {max_lines} lines of {total_lines})"
            else:
                content = "".join(lines)

            # Get file info
            stat = path.stat()

            return ToolResult(
                success=True,
                result=content,
                tool="read_file",
                metadata={
                    "filepath": str(path),
                    "lines_read": min(total_lines, max_lines),
                    "total_lines": total_lines,
                    "file_size": stat.st_size,
                    "modified_time": stat.st_mtime,
                },
            )

        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                error=f"Failed to decode file with {encoding} encoding. Try a different encoding.",
                tool="read_file",
                metadata={"filepath": filepath, "encoding": encoding},
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error reading file: {str(e)}",
                tool="read_file",
                metadata={"filepath": filepath},
            )


class WriteFileTool(BaseTool):
    """Tool for writing content to files."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="write_file",
            description="Write text content to a file",
            category="filesystem",
            parameters={
                "filepath": ToolParameter(
                    type=ToolParameterType.STRING, description="Path where to write the file"
                ),
                "content": ToolParameter(
                    type=ToolParameterType.STRING, description="Content to write to the file"
                ),
                "mode": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Write mode: 'write' (overwrite) or 'append'",
                    default="write",
                    required=False,
                    enum=["write", "append"],
                ),
                "encoding": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="File encoding",
                    default="utf-8",
                    required=False,
                ),
                "create_dirs": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Create parent directories if they don't exist",
                    default=True,
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        filepath = arguments["filepath"]
        content = arguments["content"]
        mode = arguments.get("mode", "write")
        encoding = arguments.get("encoding", "utf-8")
        create_dirs = arguments.get("create_dirs", True)

        try:
            path = Path(filepath).resolve()

            # Create parent directories if requested
            if create_dirs and not path.parent.exists():
                path.parent.mkdir(parents=True, exist_ok=True)

            # Determine file mode
            file_mode = "w" if mode == "write" else "a"

            # Back up existing file if overwriting
            backup_path = None
            if mode == "write" and path.exists():
                backup_path = path.with_suffix(path.suffix + f".backup.{int(time.time())}")
                shutil.copy2(path, backup_path)

            # Write content
            with open(path, file_mode, encoding=encoding) as f:
                f.write(content)

            # Get file info after writing
            stat = path.stat()

            return ToolResult(
                success=True,
                result=f"Successfully wrote to {path}",
                tool="write_file",
                metadata={
                    "filepath": str(path),
                    "mode": mode,
                    "bytes_written": len(content.encode(encoding)),
                    "file_size": stat.st_size,
                    "backup_path": str(backup_path) if backup_path else None,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error writing file: {str(e)}",
                tool="write_file",
                metadata={"filepath": filepath},
            )


class EditFileTool(BaseTool):
    """Tool for editing specific parts of files."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="edit_file",
            description="Edit a file by replacing text or inserting at specific lines",
            category="filesystem",
            parameters={
                "filepath": ToolParameter(
                    type=ToolParameterType.STRING, description="Path to the file to edit"
                ),
                "operation": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Edit operation type",
                    enum=["replace", "insert", "delete"],
                ),
                "search_text": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Text to search for (required for 'replace' operation)",
                    required=False,
                ),
                "replacement_text": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Replacement text (required for 'replace' and 'insert' operations)",
                    required=False,
                ),
                "line_number": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Line number for 'insert' or 'delete' operations (1-based)",
                    required=False,
                    min_value=1,
                ),
                "num_lines": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Number of lines to delete (for 'delete' operation)",
                    default=1,
                    required=False,
                    min_value=1,
                ),
                "encoding": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="File encoding",
                    default="utf-8",
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        filepath = arguments["filepath"]
        operation = arguments["operation"]
        encoding = arguments.get("encoding", "utf-8")

        try:
            path = Path(filepath).resolve()

            if not path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {filepath}",
                    tool="edit_file",
                    metadata={"filepath": filepath},
                )

            # Read current content
            with open(path, encoding=encoding) as f:
                lines = f.readlines()

            # Create backup
            backup_path = path.with_suffix(path.suffix + f".backup.{int(time.time())}")
            shutil.copy2(path, backup_path)

            # Perform operation
            if operation == "replace":
                search_text = arguments.get("search_text")
                replacement_text = arguments.get("replacement_text", "")

                if not search_text:
                    return ToolResult(
                        success=False,
                        error="search_text is required for replace operation",
                        tool="edit_file",
                    )

                # Join lines and perform replacement
                content = "".join(lines)
                if search_text not in content:
                    return ToolResult(
                        success=False,
                        error=f"Text not found: {search_text}",
                        tool="edit_file",
                        metadata={"filepath": filepath},
                    )

                new_content = content.replace(search_text, replacement_text)
                lines = new_content.splitlines(keepends=True)

            elif operation == "insert":
                line_number = arguments.get("line_number")
                text = arguments.get("replacement_text", "")

                if line_number is None:
                    return ToolResult(
                        success=False,
                        error="line_number is required for insert operation",
                        tool="edit_file",
                    )

                # Ensure text ends with newline
                if not text.endswith("\n"):
                    text += "\n"

                # Insert at specified line (convert to 0-based index)
                insert_index = line_number - 1
                if insert_index > len(lines):
                    insert_index = len(lines)

                lines.insert(insert_index, text)

            elif operation == "delete":
                line_number = arguments.get("line_number")
                num_lines = arguments.get("num_lines", 1)

                if line_number is None:
                    return ToolResult(
                        success=False,
                        error="line_number is required for delete operation",
                        tool="edit_file",
                    )

                # Delete specified lines (convert to 0-based index)
                start_index = line_number - 1
                end_index = min(start_index + num_lines, len(lines))

                if start_index >= len(lines):
                    return ToolResult(
                        success=False,
                        error=f"Line number {line_number} is beyond file length ({len(lines)} lines)",
                        tool="edit_file",
                    )

                del lines[start_index:end_index]

            # Write modified content
            with open(path, "w", encoding=encoding) as f:
                f.writelines(lines)

            return ToolResult(
                success=True,
                result=f"Successfully edited {path}",
                tool="edit_file",
                metadata={
                    "filepath": str(path),
                    "operation": operation,
                    "backup_path": str(backup_path),
                    "lines_after": len(lines),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error editing file: {str(e)}",
                tool="edit_file",
                metadata={"filepath": filepath},
            )


class ListDirectoryTool(BaseTool):
    """Tool for listing directory contents."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="list_directory",
            description="List files and directories in a given path",
            category="filesystem",
            parameters={
                "path": ToolParameter(
                    type=ToolParameterType.STRING, description="Directory path to list", default="."
                ),
                "show_hidden": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Whether to show hidden files",
                    default=False,
                    required=False,
                ),
                "recursive": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="List subdirectories recursively",
                    default=False,
                    required=False,
                ),
                "max_depth": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Maximum depth for recursive listing",
                    default=3,
                    required=False,
                    min_value=1,
                    max_value=10,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        path_str = arguments.get("path", ".")
        show_hidden = arguments.get("show_hidden", False)
        recursive = arguments.get("recursive", False)
        max_depth = arguments.get("max_depth", 3)

        try:
            path = Path(path_str).resolve()

            if not path.exists():
                return ToolResult(
                    success=False, error=f"Directory not found: {path_str}", tool="list_directory"
                )

            if not path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Path is not a directory: {path_str}",
                    tool="list_directory",
                )

            items = []

            if recursive:
                # Recursive listing with depth limit
                for root, dirs, files in os.walk(path):
                    depth = len(Path(root).relative_to(path).parts)
                    if depth >= max_depth:
                        dirs.clear()  # Don't recurse deeper

                    # Filter hidden items if needed
                    if not show_hidden:
                        dirs[:] = [d for d in dirs if not d.startswith(".")]
                        files = [f for f in files if not f.startswith(".")]

                    # Add items with relative paths
                    rel_root = Path(root).relative_to(path)
                    for d in sorted(dirs):
                        items.append(
                            {
                                "type": "directory",
                                "name": str(rel_root / d) if str(rel_root) != "." else d,
                                "path": str(Path(root) / d),
                            }
                        )
                    for f in sorted(files):
                        items.append(
                            {
                                "type": "file",
                                "name": str(rel_root / f) if str(rel_root) != "." else f,
                                "path": str(Path(root) / f),
                                "size": (Path(root) / f).stat().st_size,
                            }
                        )
            else:
                # Non-recursive listing
                for item in sorted(path.iterdir()):
                    if not show_hidden and item.name.startswith("."):
                        continue

                    if item.is_dir():
                        items.append({"type": "directory", "name": item.name, "path": str(item)})
                    else:
                        items.append(
                            {
                                "type": "file",
                                "name": item.name,
                                "path": str(item),
                                "size": item.stat().st_size,
                            }
                        )

            # Format output
            output = f"Contents of {path}:\n\n"
            for item in items:
                if item["type"] == "directory":
                    output += f"📁 {item['name']}/\n"
                else:
                    size_str = self._format_size(item["size"])
                    output += f"📄 {item['name']} ({size_str})\n"

            return ToolResult(
                success=True,
                result=output,
                tool="list_directory",
                metadata={
                    "path": str(path),
                    "total_items": len(items),
                    "directories": len([i for i in items if i["type"] == "directory"]),
                    "files": len([i for i in items if i["type"] == "file"]),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False, error=f"Error listing directory: {str(e)}", tool="list_directory"
            )

    def _format_size(self, size: int) -> str:
        """Format file size in human-readable format."""
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


# Register tools
tool_registry.register(ReadFileTool())
tool_registry.register(WriteFileTool())
tool_registry.register(EditFileTool())
tool_registry.register(ListDirectoryTool())
