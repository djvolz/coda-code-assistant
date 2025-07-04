import sys

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

try:
    from ..__version__ import __version__
except ImportError:
    # Fallback for when package structure isn't available
    __version__ = "dev"

from coda.configuration import get_config
from coda.providers import Message, ProviderFactory, Role

from .basic_commands import BasicCommandProcessor

console = Console()


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
@click.version_option(version=__version__, prog_name="coda")
def main(provider: str, model: str, debug: bool, one_shot: str, basic: bool, mode: str):
    """Coda - A multi-provider code assistant"""

    # Load configuration
    config = get_config()

    # Apply debug override
    if debug:
        config.debug = True

    # Use default provider if not specified
    if not provider:
        provider = config.default_provider

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
            )
            return
        except ImportError:
            # Fall back to basic mode if prompt-toolkit is not available
            console.print("[yellow]Note: Interactive mode not available, using basic mode[/yellow]")

    # Basic mode
    welcome_text = Text.from_markup(
        "[bold cyan]Coda[/bold cyan] - Code Assistant\n"
        f"[dim]Multi-provider AI coding companion v{__version__}[/dim]\n"
        f"[dim]{'Basic mode' if basic else 'One-shot mode' if one_shot else 'Basic mode (TTY not detected)'}[/dim]"
    )

    console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

    # Create provider using factory
    factory = ProviderFactory(config.to_dict())

    try:
        console.print(f"\n[green]Provider:[/green] {provider}")
        console.print(f"[yellow]Initializing {provider}...[/yellow]")

        # Create provider instance
        provider_instance = factory.create(provider)
        console.print(f"[green]✓ Connected to {provider}[/green]")

        # List models
        models = provider_instance.list_models()
        console.print(f"[green]✓ Found {len(models)} available models[/green]")

        # Select model
        if not model:
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

            if one_shot:
                # For one-shot, use the first available chat model
                model = unique_models[0].id
                console.print(f"[green]Auto-selected model:[/green] {model}")
            else:
                # Use basic model selector for basic mode
                from .model_selector import ModelSelector

                selector = ModelSelector(unique_models, console)
                model = selector.select_model_basic()

        console.print(f"[green]Model:[/green] {model}")

        # Handle one-shot or interactive
        if one_shot:
            # One-shot execution with mode support
            cmd_processor = BasicCommandProcessor(console)
            cmd_processor.set_provider_info(
                provider, provider_instance, factory, model, unique_models
            )
            # Set initial mode from CLI argument
            from .basic_commands import DeveloperMode

            cmd_processor.current_mode = DeveloperMode(mode)

            console.print(f"\n[bold cyan]User:[/bold cyan] {one_shot}")
            console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

            # Get system prompt based on mode (default to general)
            system_prompt = cmd_processor.get_system_prompt()

            messages = []
            if system_prompt:
                messages.append(Message(role=Role.SYSTEM, content=system_prompt))
            messages.append(Message(role=Role.USER, content=one_shot))

            # Get generation parameters from config
            temperature = config.to_dict().get("temperature", 0.7)
            max_tokens = config.to_dict().get("max_tokens", 2000)

            for chunk in provider_instance.chat_stream(
                messages=messages, model=model, temperature=temperature, max_tokens=max_tokens
            ):
                console.print(chunk.content, end="")
            console.print("\n")
        else:
            # Interactive chat with slash command support
            console.print("\n[dim]Type /help for commands, /exit to quit[/dim]\n")
            messages = []

            # Initialize command processor
            cmd_processor = BasicCommandProcessor(console)
            cmd_processor.set_provider_info(
                provider, provider_instance, factory, model, unique_models
            )
            # Set initial mode from CLI argument
            from .basic_commands import DeveloperMode

            cmd_processor.current_mode = DeveloperMode(mode)

            while True:
                # Get user input
                user_input = Prompt.ask("[bold]You[/bold]")

                # Process potential slash commands
                cmd_result = cmd_processor.process_command(user_input)

                if cmd_result == "exit":
                    break
                elif cmd_result == "clear":
                    messages = []
                    console.print("[yellow]Conversation cleared[/yellow]\n")
                    continue
                elif cmd_result == "continue":
                    # Command was handled, continue to next iteration
                    continue
                elif cmd_result is not None:
                    # Unknown command result
                    continue

                # Skip empty input
                if not user_input.strip():
                    continue

                # Get system prompt based on mode
                system_prompt = cmd_processor.get_system_prompt()

                # Prepare messages with system prompt
                chat_messages = []
                if system_prompt:
                    chat_messages.append(Message(role=Role.SYSTEM, content=system_prompt))

                # Add conversation history and new message
                chat_messages.extend(messages)
                chat_messages.append(Message(role=Role.USER, content=user_input))

                # Get AI response
                console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

                full_response = ""
                try:
                    # Get generation parameters from config
                    temperature = config.to_dict().get("temperature", 0.7)
                    max_tokens = config.to_dict().get("max_tokens", 2000)

                    for chunk in provider_instance.chat_stream(
                        messages=chat_messages,
                        model=cmd_processor.current_model or model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    ):
                        console.print(chunk.content, end="")
                        full_response += chunk.content
                except KeyboardInterrupt:
                    console.print("\n\n[yellow]Response interrupted[/yellow]")
                    full_response += " [interrupted]"

                # Add messages to history
                messages.append(Message(role=Role.USER, content=user_input))
                messages.append(Message(role=Role.ASSISTANT, content=full_response))
                console.print("\n")

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
    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        if debug:
            import traceback

            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
