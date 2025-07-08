"""
Git operations tools for version control tasks.

These tools provide safe Git operations with proper error handling
and repository validation.
"""

import asyncio
import subprocess
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema, tool_registry


class GitStatusTool(BaseTool):
    """Tool for checking Git repository status."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="git_status",
            description="Get the status of a Git repository",
            category="git",
            parameters={
                "repo_path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Path to the Git repository",
                    default=".",
                    required=False,
                ),
                "porcelain": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Use porcelain format for machine-readable output",
                    default=False,
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        repo_path = arguments.get("repo_path", ".")
        porcelain = arguments.get("porcelain", False)

        try:
            path = Path(repo_path).resolve()

            if not self._is_git_repo(path):
                return ToolResult(
                    success=False,
                    error=f"Not a Git repository: {repo_path}",
                    tool="git_status",
                    metadata={"repo_path": str(path)},
                )

            # Build git status command
            cmd = ["git", "status"]
            if porcelain:
                cmd.append("--porcelain")

            # Execute git status
            process = await asyncio.create_subprocess_exec(
                *cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"Git status failed: {stderr.decode('utf-8')}",
                    tool="git_status",
                    metadata={"repo_path": str(path)},
                )

            status_output = stdout.decode("utf-8")

            # Parse status if porcelain format
            metadata = {"repo_path": str(path)}
            if porcelain:
                metadata.update(self._parse_porcelain_status(status_output))

            return ToolResult(
                success=True, result=status_output, tool="git_status", metadata=metadata
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting Git status: {str(e)}",
                tool="git_status",
                metadata={"repo_path": repo_path},
            )

    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is a Git repository."""
        return (path / ".git").exists() or any(
            (parent / ".git").exists() for parent in path.parents
        )

    def _parse_porcelain_status(self, output: str) -> dict[str, Any]:
        """Parse porcelain status output."""
        lines = output.strip().split("\n")
        modified = []
        staged = []
        untracked = []

        for line in lines:
            if not line:
                continue

            index_status = line[0] if len(line) > 0 else " "
            worktree_status = line[1] if len(line) > 1 else " "
            filename = line[3:] if len(line) > 3 else ""

            if index_status != " ":
                staged.append(filename)
            if worktree_status != " ":
                modified.append(filename)
            if index_status == "?" and worktree_status == "?":
                untracked.append(filename)

        return {
            "modified_files": modified,
            "staged_files": staged,
            "untracked_files": untracked,
            "total_changes": len(modified) + len(staged) + len(untracked),
        }


class GitLogTool(BaseTool):
    """Tool for viewing Git commit history."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="git_log",
            description="View Git commit history",
            category="git",
            parameters={
                "repo_path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Path to the Git repository",
                    default=".",
                    required=False,
                ),
                "max_count": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Maximum number of commits to show",
                    default=10,
                    required=False,
                    min_value=1,
                    max_value=100,
                ),
                "oneline": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Show one commit per line",
                    default=False,
                    required=False,
                ),
                "since": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Show commits since date (e.g., '2 weeks ago', '2023-01-01')",
                    required=False,
                ),
                "author": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Filter commits by author",
                    required=False,
                ),
                "grep": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Filter commits by message content",
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        repo_path = arguments.get("repo_path", ".")
        max_count = arguments.get("max_count", 10)
        oneline = arguments.get("oneline", False)
        since = arguments.get("since")
        author = arguments.get("author")
        grep_pattern = arguments.get("grep")

        try:
            path = Path(repo_path).resolve()

            if not self._is_git_repo(path):
                return ToolResult(
                    success=False,
                    error=f"Not a Git repository: {repo_path}",
                    tool="git_log",
                    metadata={"repo_path": str(path)},
                )

            # Build git log command
            cmd = ["git", "log", f"--max-count={max_count}"]

            if oneline:
                cmd.append("--oneline")
            else:
                cmd.extend(["--pretty=format:%H|%an|%ad|%s", "--date=short"])

            if since:
                cmd.extend([f"--since={since}"])
            if author:
                cmd.extend([f"--author={author}"])
            if grep_pattern:
                cmd.extend([f"--grep={grep_pattern}"])

            # Execute git log
            process = await asyncio.create_subprocess_exec(
                *cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"Git log failed: {stderr.decode('utf-8')}",
                    tool="git_log",
                    metadata={"repo_path": str(path)},
                )

            log_output = stdout.decode("utf-8")

            # Format output for better readability
            if not oneline and log_output:
                formatted_output = self._format_log_output(log_output)
            else:
                formatted_output = log_output

            return ToolResult(
                success=True,
                result=formatted_output,
                tool="git_log",
                metadata={
                    "repo_path": str(path),
                    "commit_count": (
                        len(log_output.strip().split("\n")) if log_output.strip() else 0
                    ),
                    "filters": {"since": since, "author": author, "grep": grep_pattern},
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting Git log: {str(e)}",
                tool="git_log",
                metadata={"repo_path": repo_path},
            )

    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is a Git repository."""
        return (path / ".git").exists() or any(
            (parent / ".git").exists() for parent in path.parents
        )

    def _format_log_output(self, output: str) -> str:
        """Format log output for better readability."""
        lines = output.strip().split("\n")
        formatted = []

        for line in lines:
            if "|" in line:
                parts = line.split("|", 3)
                if len(parts) >= 4:
                    hash_short = parts[0][:8]
                    author = parts[1]
                    date = parts[2]
                    message = parts[3]
                    formatted.append(f"🔸 {hash_short} - {message}")
                    formatted.append(f"   By {author} on {date}")
                    formatted.append("")

        return "\n".join(formatted)


class GitDiffTool(BaseTool):
    """Tool for viewing Git diffs."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="git_diff",
            description="Show changes between commits, commit and working tree, etc",
            category="git",
            parameters={
                "repo_path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Path to the Git repository",
                    default=".",
                    required=False,
                ),
                "target": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Target for diff (commit hash, branch name, or 'staged' for staged changes)",
                    required=False,
                ),
                "file_path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Specific file to diff",
                    required=False,
                ),
                "unified": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Number of lines of unified context",
                    default=3,
                    required=False,
                    min_value=0,
                    max_value=10,
                ),
                "stat": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Show diffstat instead of full diff",
                    default=False,
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        repo_path = arguments.get("repo_path", ".")
        target = arguments.get("target")
        file_path = arguments.get("file_path")
        unified = arguments.get("unified", 3)
        stat = arguments.get("stat", False)

        try:
            path = Path(repo_path).resolve()

            if not self._is_git_repo(path):
                return ToolResult(
                    success=False,
                    error=f"Not a Git repository: {repo_path}",
                    tool="git_diff",
                    metadata={"repo_path": str(path)},
                )

            # Build git diff command
            cmd = ["git", "diff"]

            if stat:
                cmd.append("--stat")
            else:
                cmd.append(f"--unified={unified}")

            if target == "staged":
                cmd.append("--staged")
            elif target:
                cmd.append(target)

            if file_path:
                cmd.append("--")
                cmd.append(file_path)

            # Execute git diff
            process = await asyncio.create_subprocess_exec(
                *cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"Git diff failed: {stderr.decode('utf-8')}",
                    tool="git_diff",
                    metadata={"repo_path": str(path)},
                )

            diff_output = stdout.decode("utf-8")

            if not diff_output.strip():
                return ToolResult(
                    success=True,
                    result="No changes found",
                    tool="git_diff",
                    metadata={"repo_path": str(path), "target": target, "file_path": file_path},
                )

            return ToolResult(
                success=True,
                result=diff_output,
                tool="git_diff",
                metadata={
                    "repo_path": str(path),
                    "target": target,
                    "file_path": file_path,
                    "lines_changed": len(diff_output.split("\n")),
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting Git diff: {str(e)}",
                tool="git_diff",
                metadata={"repo_path": repo_path},
            )

    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is a Git repository."""
        return (path / ".git").exists() or any(
            (parent / ".git").exists() for parent in path.parents
        )


class GitBranchTool(BaseTool):
    """Tool for Git branch operations."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="git_branch",
            description="List, create, or delete Git branches",
            category="git",
            parameters={
                "repo_path": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Path to the Git repository",
                    default=".",
                    required=False,
                ),
                "action": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Action to perform",
                    default="list",
                    required=False,
                    enum=["list", "create", "delete", "current"],
                ),
                "branch_name": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Branch name for create/delete actions",
                    required=False,
                ),
                "remote": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Include remote branches in listing",
                    default=False,
                    required=False,
                ),
                "force": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Force delete branch (use with caution)",
                    default=False,
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        repo_path = arguments.get("repo_path", ".")
        action = arguments.get("action", "list")
        branch_name = arguments.get("branch_name")
        remote = arguments.get("remote", False)
        force = arguments.get("force", False)

        try:
            path = Path(repo_path).resolve()

            if not self._is_git_repo(path):
                return ToolResult(
                    success=False,
                    error=f"Not a Git repository: {repo_path}",
                    tool="git_branch",
                    metadata={"repo_path": str(path)},
                )

            if action in ["create", "delete"] and not branch_name:
                return ToolResult(
                    success=False,
                    error=f"branch_name is required for {action} action",
                    tool="git_branch",
                )

            # Build git branch command
            if action == "list":
                cmd = ["git", "branch"]
                if remote:
                    cmd.append("-a")
            elif action == "current":
                cmd = ["git", "branch", "--show-current"]
            elif action == "create":
                cmd = ["git", "branch", branch_name]
            elif action == "delete":
                cmd = ["git", "branch"]
                if force:
                    cmd.append("-D")
                else:
                    cmd.append("-d")
                cmd.append(branch_name)

            # Execute git branch command
            process = await asyncio.create_subprocess_exec(
                *cmd, cwd=path, stdout=subprocess.PIPE, stderr=subprocess.PIPE
            )

            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                return ToolResult(
                    success=False,
                    error=f"Git branch {action} failed: {stderr.decode('utf-8')}",
                    tool="git_branch",
                    metadata={"repo_path": str(path), "action": action},
                )

            output = stdout.decode("utf-8")

            # Format output based on action
            if action == "list":
                formatted_output = self._format_branch_list(output)
            else:
                formatted_output = output.strip() or f"Successfully {action}d branch"
                if branch_name:
                    formatted_output += f": {branch_name}"

            return ToolResult(
                success=True,
                result=formatted_output,
                tool="git_branch",
                metadata={"repo_path": str(path), "action": action, "branch_name": branch_name},
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error with Git branch operation: {str(e)}",
                tool="git_branch",
                metadata={"repo_path": repo_path, "action": action},
            )

    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is a Git repository."""
        return (path / ".git").exists() or any(
            (parent / ".git").exists() for parent in path.parents
        )

    def _format_branch_list(self, output: str) -> str:
        """Format branch list output."""
        lines = output.strip().split("\n")
        formatted = []

        for line in lines:
            line = line.strip()
            if line.startswith("*"):
                # Current branch
                branch_name = line[2:].strip()
                formatted.append(f"🌟 {branch_name} (current)")
            elif line.startswith("remotes/"):
                # Remote branch
                branch_name = line.replace("remotes/", "")
                formatted.append(f"🌐 {branch_name}")
            elif line:
                # Local branch
                formatted.append(f"🌿 {line}")

        return "\n".join(formatted)


# Register tools
tool_registry.register(GitStatusTool())
tool_registry.register(GitLogTool())
tool_registry.register(GitDiffTool())
tool_registry.register(GitBranchTool())
