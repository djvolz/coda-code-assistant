import sys

import click
from rich.panel import Panel
from rich.text import Text

try:
    from ..__version__ import __version__
except ImportError:
    # Fallback for when package structure isn't available
    __version__ = "dev"

# Create themed console that respects user's theme configuration
from coda.base.theme import get_console_theme, get_themed_console
from coda.configuration import get_config

from .chat_session import ChatSession
from .error_handler import CLIErrorHandler
from .provider_manager import ProviderManager

console = get_themed_console()
theme = get_console_theme()


@click.command()
@click.option("--provider", "-p", help="LLM provider to use (oci_genai, ollama, litellm)")
@click.option("--model", "-m", help="Model to use")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--one-shot", help="Execute a single prompt and exit")
@click.option("--basic", is_flag=True, help="Use basic CLI mode (no prompt-toolkit)")
@click.option(
    "--mode",
    type=click.Choice(["general", "code", "debug", "explain", "review", "refactor", "plan"]),
    default="general",
    help="Initial developer mode (basic mode only)",
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

    # Check if we should use interactive mode
    if not basic and not one_shot and sys.stdin.isatty():
        # Import and run the interactive mode with prompt-toolkit
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
            return
        except ImportError:
            # Fall back to basic mode if prompt-toolkit is not available
            console.print(
                f"[{theme.warning}]Note: Interactive mode not available, using basic mode[/{theme.warning}]"
            )

    # Basic mode
    run_basic_mode(provider, model, config, one_shot, mode, error_handler)


def run_basic_mode(
    provider_name: str, model: str, config, one_shot: str, mode: str, error_handler: CLIErrorHandler
):
    """Run the CLI in basic mode (no prompt-toolkit)."""
    # Show welcome banner
    show_welcome_banner(one_shot)

    # Initialize provider manager
    provider_manager = ProviderManager(config, console)

    try:
        # Initialize provider
        provider = provider_manager.initialize_provider(provider_name)

        # Get available models
        all_models, unique_models = provider_manager.get_chat_models(provider)

        # Select model
        selected_model = provider_manager.select_model(unique_models, model, bool(one_shot))
        console.print(f"[{theme.success}]Model:[/{theme.success}] {selected_model}")

        # Create chat session
        session = ChatSession(
            provider=provider,
            model=selected_model,
            config=config,
            console=console,
            provider_name=provider_name or config.default_provider,
            factory=provider_manager.factory,
            unique_models=unique_models,
        )

        # Set initial mode
        session.set_mode(mode)

        # Run one-shot or interactive
        if one_shot:
            session.run_one_shot(one_shot)
        else:
            session.run_interactive()

    except ValueError as e:
        error_handler.handle_provider_error(
            e, provider_name or config.default_provider, provider_manager.factory
        )
    except Exception as e:
        error_handler.handle_general_error(e)


def show_welcome_banner(one_shot: str):
    """Display the welcome banner."""
    mode_text = "One-shot mode" if one_shot else "Basic mode"
    if not one_shot and not sys.stdin.isatty():
        mode_text = "Basic mode (TTY not detected)"

    welcome_text = Text.from_markup(
        f"[{theme.info}][{theme.bold}]Coda[/{theme.bold}][/{theme.info}] - Code Assistant\n"
        f"[{theme.dim}]Multi-provider AI coding companion v{__version__}[/{theme.dim}]\n"
        f"[{theme.dim}]{mode_text}[/{theme.dim}]"
    )

    console.print(Panel(welcome_text, title="Welcome", border_style=theme.panel_border))


if __name__ == "__main__":
    main()
