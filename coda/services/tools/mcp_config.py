"""
MCP server configuration module.

This module handles loading and managing MCP server configurations from mcp.json files.
"""

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class MCPServerConfig:
    """Configuration for an MCP server."""

    name: str
    command: str | None = None
    args: list[str] = field(default_factory=list)
    env: dict[str, str] = field(default_factory=dict)
    url: str | None = None
    auth_token: str | None = None
    enabled: bool = True

    @classmethod
    def from_dict(cls, name: str, data: dict[str, Any]) -> "MCPServerConfig":
        """Create config from dictionary data."""
        import os

        # Process args to expand template variables
        args = data.get("args", [])
        expanded_args = []
        for arg in args:
            if isinstance(arg, str):
                # Expand {cwd} to current working directory
                arg = arg.replace("{cwd}", os.getcwd())
            expanded_args.append(arg)

        return cls(
            name=name,
            command=data.get("command"),
            args=expanded_args,
            env=data.get("env", {}),
            url=data.get("url"),
            auth_token=data.get("auth_token"),
            enabled=data.get("enabled", True),
        )


@dataclass
class MCPConfig:
    """Complete MCP configuration containing all servers."""

    servers: dict[str, MCPServerConfig] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MCPConfig":
        """Create config from dictionary data."""
        servers = {}
        for server_name, server_data in data.get("mcpServers", {}).items():
            servers[server_name] = MCPServerConfig.from_dict(server_name, server_data)

        return cls(servers=servers)


def load_mcp_config(project_dir: Path | None = None) -> MCPConfig:
    """
    Load MCP configuration from mcp.json files.

    Searches for mcp.json in the following order:
    1. Current working directory
    2. Project directory (if provided)
    3. User config directory (~/.config/coda/)

    Args:
        project_dir: Optional project directory to search

    Returns:
        MCPConfig object with loaded server configurations
    """
    config_files = []

    # Current working directory
    config_files.append(Path.cwd() / "mcp.json")

    # Project directory
    if project_dir:
        config_files.append(project_dir / "mcp.json")

    # User config directory
    try:
        import os

        # XDG config directory or fallback
        config_dir = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        config_files.append(config_dir / "coda" / "mcp.json")
    except Exception:
        pass

    # Load first available config file
    for config_file in config_files:
        if config_file.exists():
            try:
                with open(config_file) as f:
                    data = json.load(f)

                logger.info(f"Loaded MCP config from {config_file}")
                return MCPConfig.from_dict(data)

            except Exception as e:
                logger.error(f"Error loading MCP config from {config_file}: {e}")
                continue

    # Return empty config if no files found
    logger.info("No MCP configuration files found, using empty config")
    return MCPConfig()
