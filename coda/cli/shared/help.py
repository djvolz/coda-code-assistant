"""Shared help content and formatting for CLI modes."""

from rich.console import Console

from .modes import DeveloperMode, get_mode_description


def print_command_help(console: Console, mode: str = ""):
    """Print the command help section."""
    # Try to use command registry
    try:
        from coda.cli.command_registry import CommandRegistry
        help_text = CommandRegistry.get_command_help(mode=mode)
        console.print(help_text)
        return
    except ImportError:
        pass
    
    # Fallback to hardcoded help
    mode_suffix = f" ({mode})" if mode else ""
    console.print(f"\n[bold]Available Commands{mode_suffix}[/bold]\n")

    console.print("[bold]AI Settings:[/bold]")
    console.print("  [cyan]/model[/cyan] (/m) - Switch AI model")
    console.print("  [cyan]/provider[/cyan] (/p) - Switch provider")
    console.print("  [cyan]/mode[/cyan] - Change developer mode")
    console.print()

    console.print("[bold]Session Management:[/bold]")
    console.print("  [cyan]/session[/cyan] (/s) - Save/load/manage conversations")
    console.print("  [cyan]/export[/cyan] (/e) - Export conversation to file")
    console.print()

    console.print("[bold]Tools:[/bold]")
    console.print("  [cyan]/tools[/cyan] (/t) - Manage MCP tools")
    console.print()

    console.print("[bold]System:[/bold]")
    console.print("  [cyan]/clear[/cyan] (/cls) - Clear conversation")
    console.print("  [cyan]/help[/cyan] (/h, /?) - Show this help")
    console.print("  [cyan]/exit[/cyan] (/quit, /q) - Exit the application")
    console.print()


def print_developer_modes(console: Console):
    """Print the developer modes section."""
    console.print("[bold]Developer Modes:[/bold]")
    for mode in DeveloperMode:
        desc = get_mode_description(mode)
        console.print(f"  [cyan]{mode.value}[/cyan] - {desc}")
    console.print()


def print_basic_keyboard_shortcuts(console: Console):
    """Print basic keyboard shortcuts available in basic mode."""
    console.print("[bold]Keyboard Shortcuts:[/bold]")
    console.print("  [cyan]Ctrl+C[/cyan] - Clear input line (during input) / Interrupt AI response")
    console.print("  [cyan]Ctrl+D[/cyan] - Exit the application (EOF)")
    console.print()
    console.print("[dim]Note: Basic mode has limited keyboard shortcuts.[/dim]")
    console.print("[dim]For command history, tab completion, and advanced editing,[/dim]")
    console.print("[dim]run without the --basic flag to use interactive mode.[/dim]")
    console.print()


def print_interactive_keyboard_shortcuts(console: Console):
    """Print enhanced keyboard shortcuts for interactive mode."""
    console.print("[bold]Keyboard Shortcuts:[/bold] [dim](Interactive mode features)[/dim]")
    console.print("  [cyan]Ctrl+C[/cyan] - Clear input line / Interrupt AI response")
    console.print("  [cyan]Ctrl+D[/cyan] - Exit the application")
    console.print("  [cyan]Ctrl+R[/cyan] - Reverse search through command history")
    console.print("  [cyan]Tab[/cyan] - Auto-complete commands and file paths")
    console.print("  [cyan]↑/↓[/cyan] - Navigate command history")
    console.print("  [cyan]Ctrl+A/E[/cyan] - Jump to beginning/end of line")
    console.print("  [cyan]Ctrl+K[/cyan] - Delete from cursor to end of line")
    console.print("  [cyan]Ctrl+U[/cyan] - Delete from cursor to beginning of line")
    console.print("  [cyan]Ctrl+W[/cyan] - Delete word before cursor")
    console.print(r"  [cyan]\\[/cyan] at line end - Continue input on next line")
    console.print()


def print_interactive_only_commands(console: Console):
    """Print commands that are only available in interactive mode."""
    console.print("[bold]Session:[/bold] [dim](Interactive mode only)[/dim]")
    console.print("  [cyan]/session[/cyan] (/s) - Save/load/manage conversations")
    console.print("  [cyan]/export[/cyan] (/e) - Export conversation to file")
    console.print()

    console.print("[bold]Advanced:[/bold] [dim](Interactive mode only)[/dim]")
    console.print("  [cyan]/theme[/cyan] - Change UI theme [yellow](Coming soon)[/yellow]")
    console.print()
