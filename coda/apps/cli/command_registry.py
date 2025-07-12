"""Centralized command registry for CLI commands and subcommands."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class CommandType(Enum):
    """Type of command or subcommand."""

    MAIN = "main"
    SUBCOMMAND = "subcommand"
    OPTION = "option"


@dataclass
class CommandDefinition:
    """Definition of a command or subcommand."""

    name: str
    description: str
    aliases: list[str] = field(default_factory=list)
    subcommands: list["CommandDefinition"] = field(default_factory=list)
    examples: list[str] = field(default_factory=list)
    type: CommandType = CommandType.MAIN
    completion_type: str | None = None  # e.g., "session_name", "model_name", "theme_name"

    def get_all_names(self) -> list[str]:
        """Get all names including aliases."""
        return [self.name] + self.aliases

    def get_subcommand(self, name: str) -> Optional["CommandDefinition"]:
        """Get subcommand by name or alias."""
        for sub in self.subcommands:
            if name in sub.get_all_names():
                return sub
        return None

    def to_autocomplete_tuple(self) -> tuple[str, str]:
        """Convert to tuple format for autocomplete."""
        return (self.name, self.description)


def _get_theme_options():
    """Get theme options dynamically from available themes."""
    from coda.base.theme import THEMES

    return [
        CommandDefinition(name=theme_name, description=theme.description, type=CommandType.OPTION)
        for theme_name, theme in THEMES.items()
    ] + [
        # Add subcommands
        CommandDefinition(
            name="list", description="List all available themes", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="current", description="Show current theme", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="reset", description="Reset to default theme", type=CommandType.SUBCOMMAND
        ),
    ]


class CommandRegistry:
    """Registry of all CLI commands."""

    # Session subcommands
    SESSION_SUBCOMMANDS = [
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

    # Export subcommands
    EXPORT_SUBCOMMANDS = [
        CommandDefinition(
            name="json",
            description="Export as JSON",
            type=CommandType.SUBCOMMAND,
            examples=["/export json", "/export json my_session"],
        ),
        CommandDefinition(
            name="markdown",
            description="Export as Markdown",
            aliases=["md"],
            type=CommandType.SUBCOMMAND,
            examples=["/export markdown", "/export md my_session"],
        ),
        CommandDefinition(
            name="txt",
            description="Export as plain text",
            aliases=["text"],
            type=CommandType.SUBCOMMAND,
            examples=["/export txt", "/export text my_session"],
        ),
        CommandDefinition(
            name="html",
            description="Export as HTML",
            type=CommandType.SUBCOMMAND,
            examples=["/export html", "/export html my_session"],
        ),
    ]

    # Mode options
    MODE_OPTIONS = [
        CommandDefinition(
            name="general", description="General conversational mode", type=CommandType.OPTION
        ),
        CommandDefinition(name="code", description="Code writing mode", type=CommandType.OPTION),
        CommandDefinition(name="debug", description="Debugging mode", type=CommandType.OPTION),
        CommandDefinition(
            name="explain", description="Code explanation mode", type=CommandType.OPTION
        ),
        CommandDefinition(name="review", description="Code review mode", type=CommandType.OPTION),
        CommandDefinition(
            name="refactor", description="Code refactoring mode", type=CommandType.OPTION
        ),
        CommandDefinition(name="plan", description="Planning mode", type=CommandType.OPTION),
    ]

    # Provider options
    PROVIDER_OPTIONS = [
        CommandDefinition(
            name="oci_genai",
            description="Oracle Cloud Infrastructure GenAI",
            type=CommandType.OPTION,
        ),
        CommandDefinition(
            name="ollama", description="Local models via Ollama", type=CommandType.OPTION
        ),
        CommandDefinition(
            name="openai", description="OpenAI GPT models (coming soon)", type=CommandType.OPTION
        ),
        CommandDefinition(
            name="litellm", description="100+ providers via LiteLLM", type=CommandType.OPTION
        ),
    ]

    # Tools subcommands
    TOOLS_SUBCOMMANDS = [
        CommandDefinition(
            name="list", description="List available MCP tools", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="enable", description="Enable specific tools", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="disable", description="Disable specific tools", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="config", description="Configure tool settings", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="status", description="Show tool status", type=CommandType.SUBCOMMAND
        ),
    ]

    # Intelligence subcommands
    INTELLIGENCE_SUBCOMMANDS = [
        CommandDefinition(
            name="analyze", description="Analyze a single file", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="map", description="Map repository structure", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="scan", description="Scan directory for code files", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="stats", description="Show language statistics", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="find", description="Find definitions by name", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="deps", description="Show file dependencies", type=CommandType.SUBCOMMAND
        ),
        CommandDefinition(
            name="graph", description="Generate dependency graph", type=CommandType.SUBCOMMAND
        ),
    ]

    # Search subcommands
    SEARCH_SUBCOMMANDS = [
        CommandDefinition(
            name="semantic",
            description="Semantic search through indexed content",
            type=CommandType.SUBCOMMAND,
            examples=["/search semantic 'web development'", "/search semantic 'error handling'"],
        ),
        CommandDefinition(
            name="code",
            description="Semantic search through code files",
            type=CommandType.SUBCOMMAND,
            examples=["/search code 'async function'", "/search code 'database query'"],
        ),
        CommandDefinition(
            name="index",
            description="Index files for semantic search",
            type=CommandType.SUBCOMMAND,
            examples=["/search index", "/search index src/", "/search index demo"],
        ),
        CommandDefinition(
            name="status",
            description="Show semantic search index status",
            type=CommandType.SUBCOMMAND,
            examples=["/search status"],
        ),
        CommandDefinition(
            name="reset",
            description="Reset search manager and clear index",
            type=CommandType.SUBCOMMAND,
            examples=["/search reset"],
        ),
    ]

    # Observability subcommands
    OBSERVABILITY_SUBCOMMANDS = [
        CommandDefinition(
            name="status",
            description="Show observability status",
            type=CommandType.SUBCOMMAND,
            examples=["/obs status"],
        ),
        CommandDefinition(
            name="metrics",
            description="Show metrics summary",
            type=CommandType.SUBCOMMAND,
            examples=["/obs metrics", "/obs metrics --detailed"],
        ),
        CommandDefinition(
            name="health",
            description="Show health status",
            type=CommandType.SUBCOMMAND,
            examples=["/obs health", "/obs health database"],
        ),
        CommandDefinition(
            name="traces",
            description="Show recent traces",
            type=CommandType.SUBCOMMAND,
            examples=["/obs traces", "/obs traces --limit 20"],
        ),
        CommandDefinition(
            name="export",
            description="Export observability data",
            type=CommandType.SUBCOMMAND,
            examples=["/obs export", "/obs export --format json --output data.json"],
        ),
        CommandDefinition(
            name="errors",
            description="Show error analysis and recent errors",
            type=CommandType.SUBCOMMAND,
            examples=["/obs errors", "/obs errors --limit 50 --days 7"],
        ),
        CommandDefinition(
            name="performance",
            description="Show performance profiling data",
            type=CommandType.SUBCOMMAND,
            examples=["/obs performance", "/obs performance --limit 30"],
        ),
    ]

    # Main commands
    COMMANDS = [
        CommandDefinition(
            name="help",
            description="Show available commands",
            aliases=["h", "?"],
            examples=["/help", "/?"],
        ),
        CommandDefinition(
            name="exit",
            description="Exit the application",
            aliases=["quit", "q"],
            examples=["/exit", "/quit", "/q"],
        ),
        CommandDefinition(
            name="clear",
            description="Clear conversation history",
            aliases=["cls"],
            examples=["/clear", "/cls"],
        ),
        CommandDefinition(
            name="model",
            description="Select a different model",
            aliases=["m"],
            examples=["/model", "/model gpt-4"],
            completion_type="model_name",
        ),
        CommandDefinition(
            name="provider",
            description="Show provider information",
            aliases=["p"],
            subcommands=PROVIDER_OPTIONS,
            examples=["/provider"],
        ),
        CommandDefinition(
            name="mode",
            description="Change developer mode",
            subcommands=MODE_OPTIONS,
            examples=["/mode", "/mode code", "/mode debug"],
        ),
        CommandDefinition(
            name="session",
            description="Manage sessions",
            aliases=["s"],
            subcommands=SESSION_SUBCOMMANDS,
            examples=["/session save", "/session list", "/s last"],
        ),
        CommandDefinition(
            name="export",
            description="Export conversation",
            aliases=["e"],
            subcommands=EXPORT_SUBCOMMANDS,
            examples=["/export json", "/export markdown", "/e html"],
        ),
        CommandDefinition(
            name="theme",
            description="Change UI theme",
            subcommands=_get_theme_options(),
            examples=["/theme", "/theme dark"],
        ),
        CommandDefinition(
            name="tools",
            description="Manage MCP tools",
            aliases=["t"],
            subcommands=TOOLS_SUBCOMMANDS,
            examples=["/tools", "/tools list"],
        ),
        CommandDefinition(
            name="map",
            description="Codebase intelligence and analysis",
            aliases=["intelligence", "code", "intel"],
            subcommands=INTELLIGENCE_SUBCOMMANDS,
            examples=["/map analyze file.py", "/map scan src/", "/map stats"],
        ),
        CommandDefinition(
            name="search",
            description="Semantic search commands",
            subcommands=SEARCH_SUBCOMMANDS,
            examples=["/search semantic 'query'", "/search code 'function'", "/search status"],
        ),
        CommandDefinition(
            name="observability",
            description="View observability data",
            aliases=["obs", "telemetry"],
            subcommands=OBSERVABILITY_SUBCOMMANDS,
            examples=["/obs", "/obs status", "/obs metrics"],
        ),
    ]

    @classmethod
    def get_command(cls, name: str) -> CommandDefinition | None:
        """Get command by name or alias."""
        for cmd in cls.COMMANDS:
            if name in cmd.get_all_names():
                return cmd
        return None

    @classmethod
    def get_autocomplete_options(cls) -> dict[str, list[tuple[str, str]]]:
        """Get autocomplete options in the format expected by SlashCommandCompleter."""
        options = {}

        for cmd in cls.COMMANDS:
            if cmd.subcommands:
                subcommand_tuples = [sub.to_autocomplete_tuple() for sub in cmd.subcommands]
                # Add options for the main command name
                options[cmd.name] = subcommand_tuples
                # Also add options for each alias
                for alias in cmd.aliases:
                    options[alias] = subcommand_tuples

        return options

    @classmethod
    def get_command_help(cls, command_name: str | None = None, mode: str = "") -> str:
        """Get formatted help text for a command or all commands."""
        if command_name:
            cmd = cls.get_command(command_name)
            if not cmd:
                return f"Unknown command: {command_name}"

            help_text = f"[bold]{cmd.name}[/bold]"
            if cmd.aliases:
                help_text += f" (aliases: {', '.join(cmd.aliases)})"
            help_text += f"\n{cmd.description}\n"

            if cmd.subcommands:
                help_text += "\n[bold]Subcommands:[/bold]\n"
                for sub in cmd.subcommands:
                    help_text += f"  [cyan]{sub.name}[/cyan]"
                    if sub.aliases:
                        help_text += f" ({', '.join(sub.aliases)})"
                    help_text += f" - {sub.description}\n"

            if cmd.examples:
                help_text += "\n[bold]Examples:[/bold]\n"
                for example in cmd.examples:
                    help_text += f"  {example}\n"

            return help_text
        else:
            # Return help for all commands
            mode_suffix = f" ({mode})" if mode else ""
            help_text = f"[bold]Available Commands{mode_suffix}:[/bold]\n\n"
            for cmd in cls.COMMANDS:
                help_text += f"[cyan]/{cmd.name}[/cyan]"
                if cmd.aliases:
                    help_text += f" (/{', /'.join(cmd.aliases)})"
                help_text += f" - {cmd.description}\n"
            return help_text
