"""Built-in tools for agents using the @tool decorator."""

import json
import os
import subprocess
from datetime import datetime
from typing import Any

from .decorators import tool
from .intelligence_tools import (
    analyze_code,
    code_stats,
    find_definition,
    find_pattern,
    get_dependencies,
)


@tool(description="Get the current working directory")
def get_current_directory() -> str:
    """Get the current working directory."""
    return os.getcwd()


@tool(description="List files in a directory")
def list_files(directory: str = ".") -> list[str]:
    """
    List files in the specified directory.

    Args:
        directory: Directory path (default: current directory)

    Returns:
        List of file names
    """
    try:
        files = os.listdir(directory)
        return sorted(files)
    except Exception as e:
        return [f"Error listing directory: {str(e)}"]


@tool(description="Read a text file")
def read_file(file_path: str) -> str:
    """
    Read the contents of a text file.

    Args:
        file_path: Path to the file

    Returns:
        File contents or error message
    """
    try:
        with open(file_path, encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {str(e)}"


@tool(description="Write to a text file")
def write_file(file_path: str, content: str) -> str:
    """
    Write content to a text file.

    Args:
        file_path: Path to the file
        content: Content to write

    Returns:
        Success message or error
    """
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
        return f"Successfully wrote to {file_path}"
    except Exception as e:
        return f"Error writing file: {str(e)}"


@tool(description="Execute a shell command")
def run_command(command: str) -> dict[str, Any]:
    """
    Execute a shell command and return the result.

    Args:
        command: Shell command to execute

    Returns:
        Dictionary with stdout, stderr, and return code
    """
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        return {
            "stdout": result.stdout,
            "stderr": result.stderr,
            "returncode": result.returncode,
            "success": result.returncode == 0,
        }
    except subprocess.TimeoutExpired:
        return {
            "stdout": "",
            "stderr": "Command timed out after 30 seconds",
            "returncode": -1,
            "success": False,
        }
    except Exception as e:
        return {"stdout": "", "stderr": str(e), "returncode": -1, "success": False}


@tool(description="Get current date and time")
def get_datetime() -> str:
    """Get the current date and time."""
    return datetime.now().isoformat()


@tool(description="Parse JSON string")
def parse_json(json_string: str) -> dict[str, Any]:
    """
    Parse a JSON string.

    Args:
        json_string: JSON string to parse

    Returns:
        Parsed JSON object or error message
    """
    try:
        return json.loads(json_string)
    except Exception as e:
        return {"error": f"Invalid JSON: {str(e)}"}


@tool(description="Format data as JSON")
def format_json(data: dict[str, Any], indent: int = 2) -> str:
    """
    Format data as pretty-printed JSON.

    Args:
        data: Data to format
        indent: Indentation level (default: 2)

    Returns:
        Formatted JSON string
    """
    try:
        return json.dumps(data, indent=indent, sort_keys=True)
    except Exception as e:
        return f"Error formatting JSON: {str(e)}"


# Async example
@tool(description="Simulate an async API call")
async def fetch_data(url: str) -> dict[str, Any]:
    """
    Simulate fetching data from an API (async).

    Args:
        url: URL to fetch from

    Returns:
        Simulated response data
    """
    # In real implementation, you'd use aiohttp or httpx
    import asyncio

    await asyncio.sleep(0.5)  # Simulate network delay

    return {
        "url": url,
        "status": 200,
        "data": {"message": "This is simulated data", "timestamp": datetime.now().isoformat()},
    }


def get_builtin_tools():
    """Get all built-in tools."""
    return [
        get_current_directory,
        list_files,
        read_file,
        write_file,
        run_command,
        get_datetime,
        parse_json,
        format_json,
        fetch_data,
        # Intelligence tools
        find_definition,
        analyze_code,
        get_dependencies,
        code_stats,
        find_pattern,
    ]
