"""Centralized command registry for CLI commands and subcommands."""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


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
    aliases: List[str] = field(default_factory=list)
    subcommands: List['CommandDefinition'] = field(default_factory=list)
    examples: List[str] = field(default_factory=list)
    type: CommandType = CommandType.MAIN
    
    def get_all_names(self) -> List[str]:
        """Get all names including aliases."""
        return [self.name] + self.aliases
    
    def get_subcommand(self, name: str) -> Optional['CommandDefinition']:
        """Get subcommand by name or alias."""
        for sub in self.subcommands:
            if name in sub.get_all_names():
                return sub
        return None
    
    def to_autocomplete_tuple(self) -> tuple[str, str]:
        """Convert to tuple format for autocomplete."""
        return (self.name, self.description)


class CommandRegistry:
    """Registry of all CLI commands."""
    
    # Session subcommands
    SESSION_SUBCOMMANDS = [
        CommandDefinition(
            name="save",
            description="Save current conversation",
            aliases=["s"],
            type=CommandType.SUBCOMMAND,
            examples=["/session save", "/session save my_session"]
        ),
        CommandDefinition(
            name="load",
            description="Load a saved conversation",
            aliases=["l"],
            type=CommandType.SUBCOMMAND,
            examples=["/session load my_session", "/session load abc123"]
        ),
        CommandDefinition(
            name="last",
            description="Load the most recent session",
            type=CommandType.SUBCOMMAND,
            examples=["/session last"]
        ),
        CommandDefinition(
            name="list",
            description="List all saved sessions",
            aliases=["ls"],
            type=CommandType.SUBCOMMAND,
            examples=["/session list"]
        ),
        CommandDefinition(
            name="branch",
            description="Create a branch from current conversation",
            aliases=["b"],
            type=CommandType.SUBCOMMAND,
            examples=["/session branch", "/session branch new_branch"]
        ),
        CommandDefinition(
            name="delete",
            description="Delete a saved session",
            aliases=["d", "rm"],
            type=CommandType.SUBCOMMAND,
            examples=["/session delete my_session", "/session delete abc123"]
        ),
        CommandDefinition(
            name="delete-all",
            description="Delete all sessions (use --auto-only for just auto-saved)",
            type=CommandType.SUBCOMMAND,
            examples=["/session delete-all", "/session delete-all --auto-only"]
        ),
        CommandDefinition(
            name="rename",
            description="Rename a session",
            aliases=["r"],
            type=CommandType.SUBCOMMAND,
            examples=["/session rename new_name", "/session rename abc123 new_name"]
        ),
        CommandDefinition(
            name="info",
            description="Show session details",
            aliases=["i"],
            type=CommandType.SUBCOMMAND,
            examples=["/session info", "/session info abc123"]
        ),
        CommandDefinition(
            name="search",
            description="Search sessions",
            type=CommandType.SUBCOMMAND,
            examples=["/session search python", "/session search 'error handling'"]
        ),
    ]
    
    # Export subcommands
    EXPORT_SUBCOMMANDS = [
        CommandDefinition(
            name="json",
            description="Export as JSON",
            type=CommandType.SUBCOMMAND,
            examples=["/export json", "/export json my_session"]
        ),
        CommandDefinition(
            name="markdown",
            description="Export as Markdown",
            aliases=["md"],
            type=CommandType.SUBCOMMAND,
            examples=["/export markdown", "/export md my_session"]
        ),
        CommandDefinition(
            name="txt",
            description="Export as plain text",
            aliases=["text"],
            type=CommandType.SUBCOMMAND,
            examples=["/export txt", "/export text my_session"]
        ),
        CommandDefinition(
            name="html",
            description="Export as HTML",
            type=CommandType.SUBCOMMAND,
            examples=["/export html", "/export html my_session"]
        ),
    ]
    
    # Mode options
    MODE_OPTIONS = [
        CommandDefinition(
            name="general",
            description="General conversational mode",
            type=CommandType.OPTION
        ),
        CommandDefinition(
            name="code",
            description="Code writing mode",
            type=CommandType.OPTION
        ),
        CommandDefinition(
            name="debug",
            description="Debugging mode",
            type=CommandType.OPTION
        ),
        CommandDefinition(
            name="explain",
            description="Code explanation mode",
            type=CommandType.OPTION
        ),
        CommandDefinition(
            name="review",
            description="Code review mode",
            type=CommandType.OPTION
        ),
        CommandDefinition(
            name="refactor",
            description="Code refactoring mode",
            type=CommandType.OPTION
        ),
        CommandDefinition(
            name="plan",
            description="Planning mode",
            type=CommandType.OPTION
        ),
    ]
    
    # Main commands
    COMMANDS = [
        CommandDefinition(
            name="help",
            description="Show available commands",
            aliases=["h", "?"],
            examples=["/help", "/?"]
        ),
        CommandDefinition(
            name="exit",
            description="Exit the application",
            aliases=["quit", "q"],
            examples=["/exit", "/quit", "/q"]
        ),
        CommandDefinition(
            name="clear",
            description="Clear conversation history",
            aliases=["cls"],
            examples=["/clear", "/cls"]
        ),
        CommandDefinition(
            name="model",
            description="Select a different model",
            aliases=["m"],
            examples=["/model", "/model gpt-4"]
        ),
        CommandDefinition(
            name="provider",
            description="Switch provider",
            aliases=["p"],
            examples=["/provider", "/provider ollama"]
        ),
        CommandDefinition(
            name="mode",
            description="Change developer mode",
            subcommands=MODE_OPTIONS,
            examples=["/mode", "/mode code", "/mode debug"]
        ),
        CommandDefinition(
            name="session",
            description="Manage sessions",
            aliases=["s"],
            subcommands=SESSION_SUBCOMMANDS,
            examples=["/session save", "/session list", "/s last"]
        ),
        CommandDefinition(
            name="export",
            description="Export conversation",
            aliases=["e"],
            subcommands=EXPORT_SUBCOMMANDS,
            examples=["/export json", "/export markdown", "/e html"]
        ),
        CommandDefinition(
            name="theme",
            description="Change UI theme",
            examples=["/theme", "/theme dark"]
        ),
        CommandDefinition(
            name="tools",
            description="Manage MCP tools",
            aliases=["t"],
            examples=["/tools", "/tools list"]
        ),
    ]
    
    @classmethod
    def get_command(cls, name: str) -> Optional[CommandDefinition]:
        """Get command by name or alias."""
        for cmd in cls.COMMANDS:
            if name in cmd.get_all_names():
                return cmd
        return None
    
    @classmethod
    def get_autocomplete_options(cls) -> Dict[str, List[tuple[str, str]]]:
        """Get autocomplete options in the format expected by SlashCommandCompleter."""
        options = {}
        
        for cmd in cls.COMMANDS:
            if cmd.subcommands:
                options[cmd.name] = [sub.to_autocomplete_tuple() for sub in cmd.subcommands]
        
        return options
    
    @classmethod
    def get_command_help(cls, command_name: Optional[str] = None, mode: str = "") -> str:
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