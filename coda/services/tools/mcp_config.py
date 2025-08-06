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
        """Create config from dictionary data with validation."""
        import os

        if not isinstance(data, dict):
            raise ValueError(f"Server '{name}' configuration must be a dictionary")

        # Validate that we have either command or url
        command = data.get("command")
        url = data.get("url")

        if not command and not url:
            raise ValueError(f"Server '{name}' must specify either 'command' or 'url'")

        if command and url:
            logger.warning(
                f"Server '{name}' has both command and url, using command for subprocess"
            )

        # Process args to expand template variables
        args = data.get("args", [])
        if not isinstance(args, list):
            raise ValueError(f"Server '{name}' args must be a list")

        expanded_args = []
        for arg in args:
            if isinstance(arg, str):
                # Expand {cwd} to current working directory
                arg = arg.replace("{cwd}", os.getcwd())
            expanded_args.append(str(arg))  # Ensure all args are strings

        # Validate env is a dict
        env = data.get("env", {})
        if not isinstance(env, dict):
            raise ValueError(f"Server '{name}' env must be a dictionary")

        return cls(
            name=name,
            command=command,
            args=expanded_args,
            env=env,
            url=url,
            auth_token=data.get("auth_token"),
            enabled=bool(data.get("enabled", True)),
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
    Load MCP configuration from mcp.json files using base config management.

    Searches for mcp.json in the following order:
    1. Current working directory
    2. Project directory (if provided)
    3. User config directory (~/.config/coda/)

    Args:
        project_dir: Optional project directory to search

    Returns:
        MCPConfig object with loaded server configurations
    """
    from coda.base.config.manager import ConfigManager
    from coda.base.config.models import ConfigFormat, ConfigPath

    # Build config paths for MCP files
    config_paths = []

    # Current working directory
    config_paths.append(ConfigPath(Path.cwd() / "mcp.json", ConfigFormat.JSON, required=False))

    # Project directory
    if project_dir:
        config_paths.append(ConfigPath(project_dir / "mcp.json", ConfigFormat.JSON, required=False))

    # User config directory - let ConfigManager handle XDG paths
    try:
        config_manager = ConfigManager(app_name="coda")
        user_config_path = config_manager.get_config_dir() / "mcp.json"
        config_paths.append(ConfigPath(user_config_path, ConfigFormat.JSON, required=False))
    except Exception as e:
        logger.warning(f"Could not determine user config directory: {e}")

    # Load first available config file
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path.path) as f:
                    data = json.load(f)

                logger.info(f"Loaded MCP config from {config_path.path}")
                return MCPConfig.from_dict(data)

            except Exception as e:
                logger.error(f"Error loading MCP config from {config_path.path}: {e}")
                continue

    # Return empty config if no files found
    logger.info("No MCP configuration files found, using empty config")
    return MCPConfig()
