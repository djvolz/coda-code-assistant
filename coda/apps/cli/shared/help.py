"""Shared help content and formatting for CLI modes."""

from rich.console import Console

from coda.services.config import get_config_service

from .modes import DeveloperMode, get_mode_description


def print_command_help(console: Console, mode: str = ""):
    """Print the command help section."""
    config_service = get_config_service()
    theme = config_service.theme_manager.get_console_theme()

    # Try to use command registry
    try:
        from ..command_registry import CommandRegistry

        help_text = CommandRegistry.get_command_help(mode=mode)
        console.print(help_text)
        return
    except ImportError:
        pass

    # Fallback to hardcoded help
    mode_suffix = f" ({mode})" if mode else ""
    console.print(f"\n[{theme.bold}]Available Commands{mode_suffix}[/{theme.bold}]\n")

    console.print(f"[{theme.bold}]AI Settings:[/{theme.bold}]")
    console.print(f"  [{theme.command}]/model[/{theme.command}] (/m) - Switch AI model")
    console.print(
        f"  [{theme.command}]/provider[/{theme.command}] (/p) - Show provider information"
    )
    console.print(f"  [{theme.command}]/mode[/{theme.command}] - Change developer mode")
    console.print()

    console.print(f"[{theme.bold}]Session Management:[/{theme.bold}]")
    console.print(
        f"  [{theme.command}]/session[/{theme.command}] (/s) - Save/load/manage conversations"
    )
    console.print(
        f"  [{theme.command}]/export[/{theme.command}] (/e) - Export conversation to file"
    )
    console.print()

    console.print(f"[{theme.bold}]Tools:[/{theme.bold}]")
    console.print(f"  [{theme.command}]/tools[/{theme.command}] (/t) - Manage MCP tools")
    console.print()

    console.print(f"[{theme.bold}]System:[/{theme.bold}]")
    console.print(f"  [{theme.command}]/clear[/{theme.command}] (/cls) - Clear conversation")
    console.print(f"  [{theme.command}]/help[/{theme.command}] (/h, /?) - Show this help")
    console.print(f"  [{theme.command}]/exit[/{theme.command}] (/quit, /q) - Exit the application")
    console.print()


def print_developer_modes(console: Console):
    """Print the developer modes section."""
    config_service = get_config_service()
    theme = config_service.theme_manager.get_console_theme()

    console.print(f"[{theme.bold}]Developer Modes:[/{theme.bold}]")
    for mode in DeveloperMode:
        desc = get_mode_description(mode)
        console.print(f"  [{theme.command}]{mode.value}[/{theme.command}] - {desc}")
    console.print()


def print_interactive_keyboard_shortcuts(console: Console):
    """Print enhanced keyboard shortcuts for interactive mode."""
    config_service = get_config_service()
    theme = config_service.theme_manager.get_console_theme()

    console.print(
        f"[{theme.bold}]Keyboard Shortcuts:[/{theme.bold}] [{theme.dim}](Interactive mode features)[/{theme.dim}]"
    )
    console.print(
        f"  [{theme.command}]Ctrl+C[/{theme.command}] - Clear input line / Interrupt AI response"
    )
    console.print(f"  [{theme.command}]Ctrl+D[/{theme.command}] - Exit the application")
    console.print(
        f"  [{theme.command}]Ctrl+R[/{theme.command}] - Reverse search through command history"
    )
    console.print(
        f"  [{theme.command}]Tab[/{theme.command}] - Auto-complete commands and file paths"
    )
    console.print(f"  [{theme.command}]↑/↓[/{theme.command}] - Navigate command history")
    console.print(f"  [{theme.command}]Ctrl+A/E[/{theme.command}] - Jump to beginning/end of line")
    console.print(
        f"  [{theme.command}]Ctrl+K[/{theme.command}] - Delete from cursor to end of line"
    )
    console.print(
        f"  [{theme.command}]Ctrl+U[/{theme.command}] - Delete from cursor to beginning of line"
    )
    console.print(f"  [{theme.command}]Ctrl+W[/{theme.command}] - Delete word before cursor")
    console.print(
        rf"  [{theme.command}]\\[/{theme.command}] at line end - Continue input on next line"
    )
    console.print()


def print_interactive_only_commands(console: Console):
    """Print commands that are only available in interactive mode."""
    config_service = get_config_service()
    theme = config_service.theme_manager.get_console_theme()

    console.print(
        f"[{theme.bold}]Session:[/{theme.bold}] [{theme.dim}](Interactive mode only)[/{theme.dim}]"
    )
    console.print(
        f"  [{theme.command}]/session[/{theme.command}] (/s) - Save/load/manage conversations"
    )
    console.print(
        f"  [{theme.command}]/export[/{theme.command}] (/e) - Export conversation to file"
    )
    console.print()

    console.print(
        f"[{theme.bold}]Advanced:[/{theme.bold}] [{theme.dim}](Interactive mode only)[/{theme.dim}]"
    )
    console.print(f"  [{theme.command}]/tools[/{theme.command}] (/t) - Manage MCP tools")
    console.print(f"  [{theme.command}]/theme[/{theme.command}] - Change UI theme")
    console.print()
