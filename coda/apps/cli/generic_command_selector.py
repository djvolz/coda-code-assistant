"""Generic command selector that works with the command registry."""

from rich.console import Console

from coda.apps.cli.command_registry import CommandDefinition, CommandType
from coda.apps.cli.completion_selector import CompletionSelector


class GenericCommandSelector(CompletionSelector):
    """Generic selector for any command with subcommands or options."""

    def __init__(
        self, command_def: CommandDefinition, console: Console = None, enable_search: bool = True
    ):
        """
        Initialize selector from a command definition.

        Args:
            command_def: The command definition with subcommands/options
            console: Rich console for output
            enable_search: Whether to enable search (auto-determined by option count)
        """
        # Convert subcommands/options to selector format
        options = []

        # Get all subcommands or options
        items = command_def.subcommands
        if not items:
            # Check if this is a command that has predefined options
            if command_def.name == "mode":
                from .command_registry import CommandRegistry

                items = CommandRegistry.MODE_OPTIONS
            elif command_def.name == "provider":
                from .command_registry import CommandRegistry

                items = CommandRegistry.PROVIDER_OPTIONS
            elif command_def.name == "theme":
                # For theme, get dynamic options
                from .command_registry import _get_theme_options

                items = _get_theme_options()
                # Filter out subcommands for selection
                items = [item for item in items if item.type == CommandType.OPTION]

        # Convert to option tuples
        for item in items:
            metadata = {}
            if item.examples:
                metadata["example"] = item.examples[0]
            if item.aliases:
                metadata["aliases"] = ", ".join(item.aliases)

            options.append((item.name, item.description, metadata if metadata else None))

        # Determine if search should be enabled
        if enable_search is True and len(options) < 8:
            # Disable search for small lists
            enable_search = False

        # Create title
        title = f"Select {command_def.name.capitalize()} Option"
        if command_def.name == "export":
            title = "Select Export Format"
        elif command_def.name == "session":
            title = "Select Session Command"
        elif command_def.name == "mode":
            title = "Select Developer Mode"

        # Initialize parent
        super().__init__(
            title=title,
            options=options,
            console=console,
            prompt_text="> ",
            instruction_text="Select an option (arrow keys to navigate, Enter to select)",
        )

        self.command_def = command_def
        self.enable_search_override = enable_search


def create_command_selector(
    command_name: str, registry_commands: list[CommandDefinition], console: Console = None
) -> GenericCommandSelector | None:
    """
    Create a selector for a command if it has subcommands/options.

    Args:
        command_name: The command name to create selector for
        registry_commands: List of command definitions from registry
        console: Rich console

    Returns:
        GenericCommandSelector if command has options, None otherwise
    """
    # Find the command definition
    command_def = None
    for cmd in registry_commands:
        if command_name in cmd.get_all_names():
            command_def = cmd
            break

    if not command_def:
        return None

    # Check if it has subcommands or is a known command with options
    if command_def.subcommands or command_name in [
        "mode",
        "provider",
        "theme",
        "export",
        "session",
    ]:
        return GenericCommandSelector(command_def, console)

    return None
