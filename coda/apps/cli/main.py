import sys

import click
from rich.console import Console

try:
    from ..__version__ import __version__
except ImportError:
    # Fallback for when package structure isn't available
    __version__ = "dev"

from coda.base.config.compat import get_config

# Create themed console that respects user's theme configuration
from coda.base.theme.compat import get_console_theme, get_themed_console
from .error_handler import CLIErrorHandler

console = get_themed_console()
theme = get_console_theme()


@click.command()
@click.option("--provider", "-p", help="LLM provider to use (oci_genai, ollama, litellm)")
@click.option("--model", "-m", help="Model to use")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--one-shot", help="Execute a single prompt and exit")
@click.option("--basic", is_flag=True, help="[DEPRECATED] Basic mode is no longer supported", hidden=True)
@click.option(
    "--mode",
    type=click.Choice(["general", "code", "debug", "explain", "review", "refactor", "plan"]),
    default="general",
    help="Initial developer mode",
)
@click.option("--no-save", is_flag=True, help="Disable auto-saving of conversations")
@click.option("--resume", is_flag=True, help="Resume the most recent session")
@click.version_option(version=__version__, prog_name="coda")
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
    """Coda - A multi-provider code assistant"""

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
        from .interactive import interactive_main

        # Pass control to the interactive CLI
        ctx = click.get_current_context()
        ctx.invoke(
            interactive_main,
            provider=provider,
            model=model,
            debug=debug,
            one_shot=one_shot,
            mode=mode,
            no_save=no_save,
            resume=resume,
        )
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


if __name__ == "__main__":
    main()