try:
    from coda.__version__ import __version__
except ImportError:
    # Fallback for when package structure isn't available
    __version__ = "dev"

from coda.services.config import get_config_service

# Import error handler
from .error_handler import CLIErrorHandler

# Console and theme will be initialized after loading config
console = None
theme = None


def main(
    provider: str,
    model: str,
    debug: bool,
    one_shot: str,
    mode: str,
    no_save: bool,
    resume: bool,
    quiet: bool = False,
):
    """Coda - A code assistant main entry point."""

    # Validate quiet flag
    if quiet and not one_shot:
        import sys

        print("Error: --quiet flag can only be used with --one-shot", file=sys.stderr)
        sys.exit(1)

    # Load configuration
    config = get_config_service()

    # Apply debug override
    if debug:
        config.set("debug", True)

    # Enable quiet mode in theme manager if requested
    if quiet:
        config.theme_manager.set_quiet_mode(True)

    # Initialize console with theme from config (will be quiet if quiet mode enabled)
    global console, theme
    console = config.theme_manager.get_console()
    theme = config.theme_manager.get_console_theme()

    # Initialize error handler
    error_handler = CLIErrorHandler(console, debug or config.debug)

    # Always use interactive mode
    try:
        import asyncio

        from rich.panel import Panel

        from .banner import create_welcome_banner
        from .interactive import run_interactive_session, run_one_shot

        # Show welcome banner (will be suppressed if quiet mode is enabled)
        welcome_text = create_welcome_banner(theme)
        console.print(Panel(welcome_text, title="Welcome", border_style=theme.panel_border))

        if one_shot:
            # Handle one-shot mode
            asyncio.run(run_one_shot(provider, model, one_shot, mode, debug, no_save))
        else:
            # Run interactive session
            asyncio.run(run_interactive_session(provider, model, debug, no_save, resume))
    except ImportError as e:
        # If prompt-toolkit is not available, show error (will be suppressed if quiet)
        console.print(
            f"[{theme.error}]Error: Interactive mode requires prompt-toolkit[/{theme.error}]"
        )
        console.print(
            f"[{theme.info}]Please install with: pip install prompt-toolkit[/{theme.info}]"
        )
        console.print(f"[{theme.dim}]Error details: {e}[/{theme.dim}]")
        sys.exit(1)
    except Exception as e:
        if not theme.quiet:
            error_handler.handle_general_error(e)
        else:
            # In quiet mode, just print the error to stderr
            import sys

            sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)
