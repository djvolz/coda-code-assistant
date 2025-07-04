"""Interactive CLI module with rich features using prompt-toolkit."""

import asyncio
import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.status import Status
from rich.text import Text

from .interactive_cli import DeveloperMode, InteractiveCLI

try:
    from ..__version__ import __version__
except ImportError:
    __version__ = "dev"

console = Console()


async def _initialize_provider(factory: "ProviderFactory", provider: str, console: Console):
    """Initialize and connect to the provider."""
    console.print(f"\n[green]Provider:[/green] {provider}")
    console.print(f"[yellow]Initializing {provider}...[/yellow]")

    # Create provider instance
    provider_instance = factory.create(provider)
    console.print(f"[green]✓ Connected to {provider}[/green]")

    return provider_instance


async def _get_chat_models(provider_instance, console: Console):
    """Get and filter available chat models from the provider."""
    # List models
    models = provider_instance.list_models()
    console.print(f"[green]✓ Found {len(models)} available models[/green]")

    # Filter for chat models - different providers use different indicators
    chat_models = [
        m
        for m in models
        if "CHAT" in m.metadata.get("capabilities", [])  # OCI GenAI
        or m.provider in ["ollama", "litellm"]  # These providers only list chat models
    ]

    # If no chat models found, use all models
    if not chat_models:
        chat_models = models

    # Deduplicate models by ID
    seen = set()
    unique_models = []
    for m in chat_models:
        if m.id not in seen:
            seen.add(m.id)
            unique_models.append(m)

    return unique_models


async def _select_model(unique_models, model: str, console: Console):
    """Handle model selection with interactive UI if needed."""
    if not model:
        from .model_selector import ModelSelector

        selector = ModelSelector(unique_models, console)

        # Use interactive selector
        model = await selector.select_model_interactive()

        if not model:
            console.print("\n[yellow]No model selected. Exiting.[/yellow]")
            return None

    console.print(f"[green]Model:[/green] {model}")
    console.print(f"[dim]Found {len(unique_models)} unique models available[/dim]")
    console.print("\n[dim]Type /help for commands, /exit or Ctrl+D to quit[/dim]")
    console.print("[dim]Press Ctrl+C to clear input or interrupt AI response[/dim]\n")

    return model


async def _handle_chat_interaction(provider_instance, cli, messages, console: Console, config=None):
    """Handle a single chat interaction including streaming response."""
    from coda.providers import Message, Role

    # Get user input with enhanced features
    try:
        user_input = await cli.get_input()
    except (KeyboardInterrupt, EOFError) as e:
        console.print(f"[red]Input interrupted: {e}[/red]")
        return True  # Continue loop
    except Exception as e:
        console.print(f"[red]Unexpected error getting input: {e}[/red]")
        return True  # Continue loop

    # Skip empty input (from Ctrl+C)
    if not user_input:
        return True

    # Handle slash commands
    if user_input.startswith("/"):
        try:
            if await cli.process_slash_command(user_input):
                return True
        except (ValueError, AttributeError) as e:
            console.print(f"[red]Invalid command: {e}[/red]")
            return True
        except Exception as e:
            console.print(f"[red]Error processing command: {e}[/red]")
            return True

    # Check for multiline indicator
    if user_input.endswith("\\\\"):
        # Get multiline input
        user_input = user_input[:-1] + "\n" + await cli.get_input(multiline=True)

    # Validate input - skip if only whitespace
    if not user_input.strip():
        return True

    # Add system prompt based on mode
    system_prompt = _get_system_prompt_for_mode(cli.current_mode)

    # Add user message
    messages.append(Message(role=Role.USER, content=user_input))

    # Choose thinking message based on mode
    thinking_messages = {
        DeveloperMode.GENERAL: "Thinking",
        DeveloperMode.CODE: "Generating code",
        DeveloperMode.DEBUG: "Analyzing",
        DeveloperMode.EXPLAIN: "Preparing explanation",
        DeveloperMode.REVIEW: "Reviewing",
        DeveloperMode.REFACTOR: "Analyzing code structure",
        DeveloperMode.PLAN: "Planning",
    }
    thinking_msg = thinking_messages.get(cli.current_mode, "Thinking")

    # Prepare messages with system prompt
    chat_messages = []
    if system_prompt:
        chat_messages.append(Message(role=Role.SYSTEM, content=system_prompt))
    chat_messages.extend(messages)

    # Clear interrupt event before starting
    cli.reset_interrupt()

    # Start listening for interrupts
    cli.start_interrupt_listener()

    full_response = ""
    interrupted = False
    first_chunk = True

    try:
        # Create a status spinner for thinking animation
        # Using "dots" spinner style - other options: "line", "star", "bouncingBar", "arrow3"
        with console.status(f"[bold cyan]{thinking_msg}...[/bold cyan]", spinner="dots") as status:
            # Get generation parameters from config or defaults
            if not config:
                from coda.configuration import get_config

                config = get_config()
            temperature = config.to_dict().get("temperature", 0.7)
            max_tokens = config.to_dict().get("max_tokens", 2000)

            stream = provider_instance.chat_stream(
                messages=chat_messages,
                model=cli.current_model,  # Use current model from CLI
                temperature=temperature,
                max_tokens=max_tokens,
            )

            # Get first chunk to stop spinner
            for chunk in stream:
                if first_chunk:
                    # Stop the spinner when we get the first chunk
                    status.stop()
                    # Just print the assistant label
                    console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")
                    first_chunk = False

                # Check for interrupt
                if cli.interrupt_event.is_set():
                    interrupted = True
                    console.print("\n\n[yellow]Response interrupted by user[/yellow]")
                    break

                # Stream the response as plain text
                console.print(chunk.content, end="")
                full_response += chunk.content

        # Add newline after streaming
        if full_response:
            console.print()  # Ensure we end on a new line
    except (ConnectionError, TimeoutError) as e:
        console.print(f"\n\n[red]Network error during streaming: {e}[/red]")
        return True  # Continue loop
    except Exception:
        if cli.interrupt_event.is_set():
            interrupted = True
            console.print("\n\n[yellow]Response interrupted by user[/yellow]")
        else:
            raise
    finally:
        # Stop the interrupt listener
        cli.stop_interrupt_listener()

    # Add assistant message to history (even if interrupted)
    if full_response or interrupted:
        messages.append(Message(role=Role.ASSISTANT, content=full_response))
    console.print("\n")  # Add spacing after response

    return True  # Continue loop


async def run_interactive_session(provider: str, model: str, debug: bool):
    """Run the enhanced interactive session."""
    # Initialize interactive CLI
    cli = InteractiveCLI(console)

    # Load configuration
    from coda.configuration import get_config
    from coda.providers import Message, ProviderFactory, Role

    config = get_config()

    # Apply debug override
    if debug:
        config.debug = True

    # Use default provider if not specified
    if not provider:
        provider = config.default_provider

    # Create provider using factory
    factory = ProviderFactory(config.to_dict())

    try:
        # Initialize provider
        provider_instance = await _initialize_provider(factory, provider, console)

        # Get available models
        unique_models = await _get_chat_models(provider_instance, console)

        # Select model
        model = await _select_model(unique_models, model, console)
        if not model:
            return

        # Set model info in CLI for /model command
        cli.current_model = model
        cli.available_models = unique_models

        # Interactive chat loop
        messages = []

        while True:
            continue_chat = await _handle_chat_interaction(
                provider_instance, cli, messages, console, config
            )
            if not continue_chat:
                break

    except ValueError as e:
        if "compartment_id is required" in str(e):
            console.print("\n[red]Error:[/red] OCI compartment ID not configured")
            console.print("\nPlease set it via one of these methods:")
            console.print(
                "1. Environment variable: [cyan]export OCI_COMPARTMENT_ID='your-compartment-id'[/cyan]"
            )
            console.print("2. Coda config file: [cyan]~/.config/coda/config.toml[/cyan]")
        elif "Unknown provider" in str(e):
            console.print(f"\n[red]Error:[/red] Provider '{provider}' not found")
            console.print(f"\nAvailable providers: {', '.join(factory.list_available())}")
        else:
            console.print(f"\n[red]Error:[/red] {e}")
        if debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)
    except SystemExit:
        # Clean exit from /exit command
        pass
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully - just exit cleanly
        console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
        sys.exit(0)
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


def _get_system_prompt_for_mode(mode: DeveloperMode) -> str:
    """Get system prompt based on developer mode."""
    from coda.cli.shared import get_system_prompt

    return get_system_prompt(mode)


@click.command()
@click.option("--provider", "-p", default="oci_genai", help="LLM provider to use")
@click.option("--model", "-m", help="Model to use")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--one-shot", help="Execute a single prompt and exit")
@click.option(
    "--mode",
    type=click.Choice([m.value for m in DeveloperMode]),
    default=DeveloperMode.GENERAL.value,
    help="Initial developer mode",
)
@click.version_option(version=__version__, prog_name="coda")
def interactive_main(provider: str, model: str, debug: bool, one_shot: str, mode: str):
    """Run Coda in interactive mode with rich CLI features"""

    welcome_text = Text.from_markup(
        "[bold cyan]Coda[/bold cyan] - Code Assistant\n"
        f"[dim]Multi-provider AI coding companion v{__version__}[/dim]\n"
        "[dim]Interactive mode with prompt-toolkit[/dim]"
    )

    console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

    if one_shot:
        # Handle one-shot mode (simplified for now)
        console.print("[yellow]One-shot mode not yet updated for enhanced CLI[/yellow]")
        console.print(f"Would execute: {one_shot}")
    else:
        # Run interactive session
        asyncio.run(run_interactive_session(provider, model, debug))


if __name__ == "__main__":
    try:
        interactive_main()
    except KeyboardInterrupt:
        # Handle Ctrl+C at the top level
        console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
        sys.exit(0)
