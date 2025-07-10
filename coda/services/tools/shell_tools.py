"""
Shell command execution tools with safety controls.

These tools provide secure shell command execution with comprehensive
safety checks and user confirmation for dangerous operations.
"""

import asyncio
import os
import shlex
import signal
import subprocess
import time
from pathlib import Path
from typing import Any

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult, ToolSchema, tool_registry


class ShellExecuteTool(BaseTool):
    """Tool for executing shell commands with safety controls."""

    # Dangerous command patterns that require explicit approval
    DANGEROUS_PATTERNS = {
        "rm -rf",
        "rm -fr",
        "rm -r",
        "rm -f",
        "sudo",
        "su ",
        "su\n",
        "su\t",
        "chmod 777",
        "chmod a+rwx",
        "mkfs",
        "fdisk",
        "parted",
        "dd if=",
        "dd of=",
        "kill -9",
        "killall",
        "reboot",
        "shutdown",
        "passwd",
        "chpasswd",
        "iptables",
        "ufw",
        "crontab",
        "at ",
        "curl | sh",
        "wget | sh",
        "curl | bash",
        "wget | bash",
        "> /dev/",
        "> /proc/",
        "> /sys/",
        "eval $",
        "exec $",
    }

    # Commands that are completely blocked
    BLOCKED_PATTERNS = {
        "rm -rf /",
        "rm -rf /*",
        "rm -rf ~",
        "rm -fr /",
        "rm -fr /*",
        "rm -fr ~",
        "chown -R",
        "chmod -R 777",
        "format c:",
        "del /s",
        "DROP TABLE",
        "DROP DATABASE",
        ":(){ :|:& };:",  # Fork bomb
        "dd if=/dev/zero of=/",
        "mkfs.ext4 /",
        "mkfs /",
    }

    # Safe commands that don't need warnings
    SAFE_COMMANDS = {
        "ls",
        "dir",
        "pwd",
        "cd",
        "cat",
        "less",
        "more",
        "head",
        "tail",
        "grep",
        "find",
        "locate",
        "which",
        "whereis",
        "file",
        "stat",
        "echo",
        "printf",
        "date",
        "whoami",
        "id",
        "uname",
        "hostname",
        "ps",
        "top",
        "htop",
        "free",
        "df",
        "du",
        "mount",
        "lsblk",
        "git",
        "svn",
        "hg",
        "bzr",
        "python",
        "python3",
        "pip",
        "pip3",
        "node",
        "npm",
        "yarn",
        "make",
        "cmake",
        "gcc",
        "clang",
        "javac",
        "rustc",
        "curl",
        "wget",
        "ping",
        "traceroute",
        "nslookup",
        "dig",
        "ssh",
        "scp",
        "rsync",
        "tar",
        "zip",
        "unzip",
        "gzip",
        "gunzip",
    }

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="shell_execute",
            description="Execute shell commands with safety controls and approval for dangerous operations",
            category="system",
            dangerous=True,
            parameters={
                "command": ToolParameter(
                    type=ToolParameterType.STRING, description="Shell command to execute"
                ),
                "working_directory": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Working directory for command execution",
                    default=".",
                    required=False,
                ),
                "timeout": ToolParameter(
                    type=ToolParameterType.INTEGER,
                    description="Timeout in seconds",
                    default=30,
                    required=False,
                    min_value=1,
                    max_value=300,
                ),
                "capture_output": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Whether to capture and return command output",
                    default=True,
                    required=False,
                ),
                "allow_dangerous": ToolParameter(
                    type=ToolParameterType.BOOLEAN,
                    description="Allow execution of potentially dangerous commands",
                    default=False,
                    required=False,
                ),
                "environment": ToolParameter(
                    type=ToolParameterType.OBJECT,
                    description="Additional environment variables (as key-value pairs)",
                    required=False,
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        command = arguments["command"].strip()
        working_dir = arguments.get("working_directory", ".")
        timeout = arguments.get("timeout", 30)
        capture_output = arguments.get("capture_output", True)
        allow_dangerous = arguments.get("allow_dangerous", False)
        environment = arguments.get("environment", {})

        # Validate command
        safety_result = self._check_command_safety(command)
        if safety_result["blocked"]:
            return ToolResult(
                success=False,
                error=f"Command blocked for security: {safety_result['reason']}",
                tool="shell_execute",
                metadata={"command": command, "safety_level": "blocked"},
            )

        if safety_result["dangerous"] and not allow_dangerous:
            return ToolResult(
                success=False,
                error=f"Dangerous command requires explicit approval: {safety_result['reason']}. Set allow_dangerous=true to proceed.",
                tool="shell_execute",
                metadata={"command": command, "safety_level": "dangerous"},
            )

        # Validate working directory
        try:
            work_path = Path(working_dir).resolve()
            if not work_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Working directory does not exist: {working_dir}",
                    tool="shell_execute",
                )
            if not work_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Working directory is not a directory: {working_dir}",
                    tool="shell_execute",
                )
        except Exception as e:
            return ToolResult(
                success=False, error=f"Invalid working directory: {str(e)}", tool="shell_execute"
            )

        # Prepare environment
        env = os.environ.copy()
        if isinstance(environment, dict):
            env.update(environment)

        start_time = time.time()

        try:
            # Execute command
            process = await asyncio.create_subprocess_shell(
                command,
                cwd=work_path,
                env=env,
                stdout=subprocess.PIPE if capture_output else None,
                stderr=subprocess.PIPE if capture_output else None,
                preexec_fn=os.setsid if os.name != "nt" else None,  # Create process group on Unix
            )

            try:
                stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            except TimeoutError:
                # Kill the process group to ensure cleanup
                if os.name != "nt":
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                else:
                    process.terminate()

                try:
                    await asyncio.wait_for(process.wait(), timeout=5)
                except TimeoutError:
                    if os.name != "nt":
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()

                return ToolResult(
                    success=False,
                    error=f"Command timed out after {timeout} seconds",
                    tool="shell_execute",
                    metadata={
                        "command": command,
                        "timeout": timeout,
                        "execution_time": time.time() - start_time,
                    },
                )

            execution_time = time.time() - start_time

            # Format output
            result_parts = []
            result_parts.append(f"Command: {command}")
            result_parts.append(f"Exit code: {process.returncode}")
            result_parts.append(f"Execution time: {execution_time:.2f}s")

            if capture_output:
                if stdout:
                    stdout_text = stdout.decode("utf-8", errors="replace")
                    result_parts.append(f"\nSTDOUT:\n{stdout_text}")

                if stderr:
                    stderr_text = stderr.decode("utf-8", errors="replace")
                    result_parts.append(f"\nSTDERR:\n{stderr_text}")

            result_text = "\n".join(result_parts)

            return ToolResult(
                success=process.returncode == 0,
                result=result_text,
                tool="shell_execute",
                metadata={
                    "command": command,
                    "exit_code": process.returncode,
                    "execution_time": execution_time,
                    "working_directory": str(work_path),
                    "safety_level": safety_result["level"],
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Command execution failed: {str(e)}",
                tool="shell_execute",
                metadata={"command": command, "execution_time": time.time() - start_time},
            )

    def _check_command_safety(self, command: str) -> dict[str, Any]:
        """
        Check if a command is safe to execute.

        Returns:
            Dict with 'blocked', 'dangerous', 'level', and 'reason' keys
        """
        command_lower = command.lower().strip()

        # Check for completely blocked patterns
        for pattern in self.BLOCKED_PATTERNS:
            if pattern in command_lower:
                return {
                    "blocked": True,
                    "dangerous": True,
                    "level": "blocked",
                    "reason": f"Contains blocked pattern: {pattern}",
                }

        # Check for dangerous patterns
        for pattern in self.DANGEROUS_PATTERNS:
            if pattern in command_lower:
                return {
                    "blocked": False,
                    "dangerous": True,
                    "level": "dangerous",
                    "reason": f"Contains dangerous pattern: {pattern}",
                }

        # Check if command starts with a safe command
        first_command = shlex.split(command)[0] if command else ""
        if first_command in self.SAFE_COMMANDS:
            return {
                "blocked": False,
                "dangerous": False,
                "level": "safe",
                "reason": "Known safe command",
            }

        # Check for suspicious patterns
        suspicious_patterns = [
            "|",
            "&&",
            "||",
            ";",
            "`",
            "$(",
            "eval",
            "exec",
            "source",
            ".",
            "curl",
            "wget",
            "nc",
            "netcat",
        ]

        for pattern in suspicious_patterns:
            if pattern in command:
                return {
                    "blocked": False,
                    "dangerous": True,
                    "level": "suspicious",
                    "reason": f"Contains potentially dangerous pattern: {pattern}",
                }

        # Default to requiring approval for unknown commands
        return {
            "blocked": False,
            "dangerous": True,
            "level": "unknown",
            "reason": "Unknown command requires approval",
        }


class GetCurrentTimeTool(BaseTool):
    """Tool for getting current system time."""

    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="get_current_time",
            description="Get the current date and time",
            category="system",
            parameters={
                "format": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Time format string (Python strftime format)",
                    default="%Y-%m-%d %H:%M:%S",
                    required=False,
                ),
                "timezone": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="Timezone (local or UTC)",
                    default="local",
                    required=False,
                    enum=["local", "utc"],
                ),
            },
        )

    async def execute(self, arguments: dict[str, Any]) -> ToolResult:
        time_format = arguments.get("format", "%Y-%m-%d %H:%M:%S")
        timezone = arguments.get("timezone", "local")

        try:
            import datetime

            if timezone == "utc":
                now = datetime.datetime.utcnow()
                timezone_info = "UTC"
            else:
                now = datetime.datetime.now()
                timezone_info = "Local"

            formatted_time = now.strftime(time_format)

            return ToolResult(
                success=True,
                result=f"Current time ({timezone_info}): {formatted_time}",
                tool="get_current_time",
                metadata={
                    "timestamp": now.timestamp(),
                    "timezone": timezone_info,
                    "format": time_format,
                },
            )

        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error getting current time: {str(e)}",
                tool="get_current_time",
            )


# Register tools
tool_registry.register(ShellExecuteTool())
tool_registry.register(GetCurrentTimeTool())
