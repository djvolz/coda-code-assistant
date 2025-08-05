"""MCP-related command definitions."""

from ..command_registry import CommandDefinition, CommandType


def get_mcp_commands() -> list[CommandDefinition]:
    """Get MCP subcommand definitions."""
    return [
        CommandDefinition(
            name="list",
            description="List configured MCP servers",
            type=CommandType.SUBCOMMAND,
            examples=["/mcp list", "/mcp ls"],
            aliases=["ls"],
        ),
        CommandDefinition(
            name="status",
            description="Show status of MCP servers",
            type=CommandType.SUBCOMMAND,
            examples=["/mcp status", "/mcp status serena"],
        ),
        CommandDefinition(
            name="start",
            description="Start an MCP server",
            type=CommandType.SUBCOMMAND,
            examples=["/mcp start serena", "/mcp start all"],
        ),
        CommandDefinition(
            name="stop",
            description="Stop an MCP server",
            type=CommandType.SUBCOMMAND,
            examples=["/mcp stop serena", "/mcp stop all"],
        ),
        CommandDefinition(
            name="restart",
            description="Restart an MCP server",
            type=CommandType.SUBCOMMAND,
            examples=["/mcp restart serena", "/mcp restart all"],
        ),
        CommandDefinition(
            name="config",
            description="Show MCP configuration",
            type=CommandType.SUBCOMMAND,
            examples=["/mcp config", "/mcp config serena"],
        ),
    ]
