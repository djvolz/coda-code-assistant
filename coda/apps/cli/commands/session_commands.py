"""Session management command definitions."""

from ..command_registry import CommandDefinition, CommandType


def get_session_commands() -> list[CommandDefinition]:
    """Get session subcommand definitions."""
    return [
        CommandDefinition(
            name="save",
            description="Save current conversation",
            aliases=["s"],
            type=CommandType.SUBCOMMAND,
            examples=["/session save", "/session save my_session"],
        ),
        CommandDefinition(
            name="load",
            description="Load a saved conversation",
            aliases=["l"],
            type=CommandType.SUBCOMMAND,
            examples=["/session load my_session", "/session load abc123"],
            completion_type="session_name",
        ),
        CommandDefinition(
            name="last",
            description="Load the most recent session",
            type=CommandType.SUBCOMMAND,
            examples=["/session last"],
        ),
        CommandDefinition(
            name="list",
            description="List all saved sessions",
            aliases=["ls"],
            type=CommandType.SUBCOMMAND,
            examples=["/session list"],
        ),
        CommandDefinition(
            name="branch",
            description="Create a branch from current conversation",
            aliases=["b"],
            type=CommandType.SUBCOMMAND,
            examples=["/session branch", "/session branch new_branch"],
            completion_type="session_name",
        ),
        CommandDefinition(
            name="delete",
            description="Delete a saved session",
            aliases=["d", "rm"],
            type=CommandType.SUBCOMMAND,
            examples=["/session delete my_session", "/session delete abc123"],
            completion_type="session_name",
        ),
        CommandDefinition(
            name="delete-all",
            description="Delete all sessions (use --auto-only for just auto-saved)",
            type=CommandType.SUBCOMMAND,
            examples=["/session delete-all", "/session delete-all --auto-only"],
        ),
        CommandDefinition(
            name="rename",
            description="Rename a session",
            aliases=["r"],
            type=CommandType.SUBCOMMAND,
            examples=["/session rename new_name", "/session rename abc123 new_name"],
            completion_type="session_name",
        ),
        CommandDefinition(
            name="info",
            description="Show session details",
            aliases=["i"],
            type=CommandType.SUBCOMMAND,
            examples=["/session info", "/session info abc123"],
            completion_type="session_name",
        ),
        CommandDefinition(
            name="search",
            description="Search sessions",
            type=CommandType.SUBCOMMAND,
            examples=["/session search python", "/session search 'error handling'"],
        ),
    ]
