import sys

from rich.console import Console

try:
    from coda.__version__ import __version__
except ImportError:
    # Fallback for when package structure isn't available
    __version__ = "dev"

from coda.base.config.compat import get_config

# Create themed console that respects user's theme configuration
from coda.base.theme.compat import get_console_theme, get_themed_console
from .error_handler import CLIErrorHandler

console = get_themed_console()
theme = get_console_theme()


def main(
    provider: str,
    model: str,
    debug: bool,
    one_shot: str,
    basic: bool,
    mode: str,
    no_save: bool,
    resume: bool,
):
    """Coda - A multi-provider code assistant main entry point."""

    # Load configuration
    config = get_config()

    # Apply debug override
    if debug:
        config.debug = True

    # Initialize error handler
    error_handler = CLIErrorHandler(console, debug)

    # Show deprecation message if --basic was used
    if basic:
        console.print(
            f"[{theme.warning}]Warning: --basic flag is deprecated. "
            f"Using interactive mode instead.[/{theme.warning}]"
        )

    # Always use interactive mode
    try:
        from .interactive import run_interactive_session
        import asyncio
        from rich.panel import Panel
        from rich.text import Text

        # Show welcome banner
        welcome_text = Text.from_markup(
            f"[bold cyan]Coda[/bold cyan] - Code Assistant\n"
            f"[dim]Multi-provider AI coding companion v{__version__}[/dim]\n"
            f"[dim]Interactive mode with prompt-toolkit[/dim]"
        )
        
        console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

        if one_shot:
            # Handle one-shot mode
            console.print("[yellow]One-shot mode not yet updated for enhanced CLI[/yellow]")
            console.print(f"Would execute: {one_shot}")
        else:
            # Run interactive session
            asyncio.run(run_interactive_session(provider, model, debug, no_save, resume))
    except ImportError as e:
        # If prompt-toolkit is not available, show error
        console.print(
            f"[{theme.error}]Error: Interactive mode requires prompt-toolkit[/{theme.error}]"
        )
        console.print(f"[{theme.info}]Please install with: pip install prompt-toolkit[/{theme.info}]")
        console.print(f"[{theme.dim}]Error details: {e}[/{theme.dim}]")
        sys.exit(1)
    except Exception as e:
        error_handler.handle_general_error(e)
        sys.exit(1)