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

console = Console()


@click.command()
@click.option('--provider', '-p', default='oci_genai', help='LLM provider to use (oci_genai, ollama, openai)')
@click.option('--model', '-m', help='Model to use')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.option('--one-shot', help='Execute a single prompt and exit')
@click.option('--basic', is_flag=True, help='Use basic CLI mode (no prompt-toolkit)')
@click.version_option(version=__version__, prog_name='coda')
def main(provider: str, model: str, debug: bool, one_shot: str, basic: bool):
    """Coda - A multi-provider code assistant"""

    # Check if we should use interactive mode
    if not basic and not one_shot and sys.stdin.isatty():
        # Import and run the interactive mode with prompt-toolkit
        try:
            from .interactive import interactive_main
            # Pass control to the interactive CLI
            ctx = click.get_current_context()
            ctx.invoke(interactive_main, provider=provider, model=model, debug=debug,
                      one_shot=one_shot, mode='code')
            return
        except ImportError:
            # Fall back to basic mode if prompt-toolkit is not available
            console.print("[yellow]Note: Interactive mode not available, using basic mode[/yellow]")

    # Basic mode welcome
    welcome_text = Text.from_markup(
        "[bold cyan]Coda[/bold cyan] - Code Assistant\n"
        f"[dim]Multi-provider AI coding companion v{__version__}[/dim]\n"
        f"[dim]{'Basic mode' if basic else 'One-shot mode' if one_shot else 'Basic mode (TTY not detected)'}[/dim]"
    )

    console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

    # Handle OCI GenAI provider
    if provider == "oci_genai":
        try:
            from coda.providers import Message, OCIGenAIProvider, Role

            console.print(f"\n[green]Provider:[/green] {provider}")
            console.print("[yellow]Initializing OCI GenAI...[/yellow]")

            # Initialize provider (compartment ID from env var or config)
            oci_provider = OCIGenAIProvider()
            console.print("[green]✓ Connected to OCI GenAI[/green]")

            # List models
            models = oci_provider.list_models()
            console.print(f"[green]✓ Found {len(models)} available models[/green]")

            # Select model
            if not model:
                chat_models = [m for m in models if 'CHAT' in m.metadata.get('capabilities', [])]

                if one_shot:
                    # For one-shot, use the first available chat model
                    model = chat_models[0].id
                    console.print(f"[green]Auto-selected model:[/green] {model}")
                else:
                    # Show available models for interactive mode
                    console.print("\n[bold]Available models:[/bold]")
                    for i, m in enumerate(chat_models[:10], 1):  # Show first 10
                        console.print(f"{i:2d}. {m.id} ({m.provider})")

                    if len(chat_models) > 10:
                        console.print(f"    ... and {len(chat_models) - 10} more")

                    # Let user choose
                    choice = Prompt.ask(
                        "\nSelect model number",
                        default="1",
                        choices=[str(i) for i in range(1, min(len(chat_models) + 1, 11))]
                    )
                    model = chat_models[int(choice) - 1].id

            console.print(f"[green]Model:[/green] {model}")

            # Handle one-shot or interactive
            if one_shot:
                # One-shot execution
                console.print(f"\n[bold cyan]User:[/bold cyan] {one_shot}")
                console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

                messages = [Message(role=Role.USER, content=one_shot)]
                for chunk in oci_provider.chat_stream(
                    messages=messages,
                    model=model,
                    temperature=0.7,
                    max_tokens=500
                ):
                    console.print(chunk.content, end="")
                console.print("\n")
            else:
                # Interactive chat
                console.print("\n[dim]Type 'exit' to quit, 'clear' to reset conversation[/dim]\n")
                messages = []

                while True:
                    # Get user input
                    user_input = Prompt.ask("[bold]You[/bold]")

                    if user_input.lower() == "exit":
                        break
                    elif user_input.lower() == "clear":
                        messages = []
                        console.print("[yellow]Conversation cleared[/yellow]\n")
                        continue

                    # Add user message
                    messages.append(Message(role=Role.USER, content=user_input))

                    # Get AI response
                    console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

                    full_response = ""
                    for chunk in oci_provider.chat_stream(
                        messages=messages,
                        model=model,
                        temperature=0.7,
                        max_tokens=500
                    ):
                        console.print(chunk.content, end="")
                        full_response += chunk.content

                    # Add assistant message to history
                    messages.append(Message(role=Role.ASSISTANT, content=full_response))
                    console.print("\n")

        except ValueError as e:
            if "compartment_id is required" in str(e):
                console.print("\n[red]Error:[/red] OCI compartment ID not configured")
                console.print("\nPlease set it via one of these methods:")
                console.print("1. Environment variable: [cyan]export OCI_COMPARTMENT_ID='your-compartment-id'[/cyan]")
                console.print("2. Coda config file: [cyan]~/.config/coda/config.toml[/cyan]")
                console.print("3. Command parameter: [cyan]coda --compartment-id 'your-compartment-id'[/cyan]")
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

    else:
        # Other providers not implemented yet
        console.print(f"\n[green]Provider:[/green] {provider}")
        if model:
            console.print(f"[green]Model:[/green] {model}")

        console.print(f"\n[yellow]Note:[/yellow] Provider '{provider}' not implemented yet.")
        console.print("Currently supported: oci_genai")
        console.print("\nTry: [cyan]coda --provider oci_genai[/cyan]")


if __name__ == "__main__":
    main()
