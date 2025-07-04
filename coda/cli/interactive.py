"""Interactive CLI module with rich features using prompt-toolkit."""

import asyncio
import sys
import time
from threading import Event

import click
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
from rich.spinner import Spinner
from rich.table import Table
from rich.box import ROUNDED

from .interactive_cli import DeveloperMode, InteractiveCLI

try:
    from ..__version__ import __version__
except ImportError:
    __version__ = "dev"

console = Console()


async def run_interactive_session(provider: str, model: str, debug: bool):
    """Run the enhanced interactive session."""
    # Initialize interactive CLI
    cli = InteractiveCLI(console)

    # Handle OCI GenAI provider
    if provider == "oci_genai":
        try:
            from coda.providers import Message, OCIGenAIProvider, Role

            console.print(f"\n[green]Provider:[/green] {provider}")
            console.print("[yellow]Initializing OCI GenAI...[/yellow]")

            oci_provider = OCIGenAIProvider()
            console.print("[green]✓ Connected to OCI GenAI[/green]")

            # List models
            models = oci_provider.list_models()
            console.print(f"[green]✓ Found {len(models)} available models[/green]")

            # Select model if not specified
            if not model:
                from .model_selector import ModelSelector
                
                chat_models = [m for m in models if 'CHAT' in m.metadata.get('capabilities', [])]
                
                # Deduplicate models by ID
                seen = set()
                unique_models = []
                for m in chat_models:
                    if m.id not in seen:
                        seen.add(m.id)
                        unique_models.append(m)
                
                selector = ModelSelector(unique_models, console)
                
                # Use interactive selector
                model = await selector.select_model_interactive()
                
                if not model:
                    console.print("\n[yellow]No model selected. Exiting.[/yellow]")
                    return

            console.print(f"[green]Model:[/green] {model}")
            console.print(f"[dim]Found {len(unique_models)} unique models available[/dim]")
            console.print("\n[dim]Type /help for commands, /exit or Ctrl+D to quit[/dim]")
            console.print("[dim]Press Ctrl+C to clear input or interrupt AI response[/dim]\n")
            
            # Set model info in CLI for /model command
            cli.current_model = model
            cli.available_models = unique_models

            # Interactive chat loop
            messages = []

            while True:
                # Get user input with enhanced features
                user_input = await cli.get_input()
                
                # Skip empty input (from Ctrl+C)
                if not user_input:
                    continue

                # Handle slash commands
                if user_input.startswith('/'):
                    if await cli.process_slash_command(user_input):
                        continue

                # Check for multiline indicator
                if user_input.endswith('\\'):
                    # Get multiline input
                    user_input = user_input[:-1] + '\n' + await cli.get_input(multiline=True)
                
                # Validate input - skip if only whitespace
                if not user_input.strip():
                    continue

                # Add system prompt based on mode
                system_prompt = _get_system_prompt_for_mode(cli.current_mode)

                # Add user message
                messages.append(Message(role=Role.USER, content=user_input))
                
                # Display user prompt in a nice box
                user_panel = Panel(
                    user_input,
                    title=f"[bold cyan]You[/bold cyan] [dim]({cli.current_mode.value} mode)[/dim]",
                    title_align="left",
                    border_style="cyan",
                    box=ROUNDED,
                    padding=(0, 1),
                )
                console.print("\n", user_panel)

                # Show thinking indicator
                console.print()  # New line after user panel
                
                # Choose spinner and message based on mode
                spinner_style = {
                    DeveloperMode.GENERAL: ("dots", "Thinking"),
                    DeveloperMode.CODE: ("dots2", "Generating code"),
                    DeveloperMode.DEBUG: ("line", "Analyzing"),
                    DeveloperMode.EXPLAIN: ("dots3", "Preparing explanation"),
                    DeveloperMode.REVIEW: ("arc", "Reviewing"),
                    DeveloperMode.REFACTOR: ("bouncingBar", "Analyzing code structure"),
                    DeveloperMode.PLAN: ("circleHalves", "Planning"),
                }.get(cli.current_mode, ("dots", "Thinking"))
                
                # Create a table for the thinking indicator
                thinking_table = Table.grid(padding=0)
                thinking_table.add_column(style="cyan", justify="left")
                thinking_table.add_column()
                thinking_table.add_row(
                    Spinner(spinner_style[0], style="cyan"),
                    f"[dim]{spinner_style[1]}...[/dim]"
                )

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
                    # Show thinking spinner until first chunk arrives
                    with Live(thinking_table, console=console, refresh_per_second=10, transient=True) as live:
                        stream = oci_provider.chat_stream(
                            messages=chat_messages,
                            model=cli.current_model,  # Use current model from CLI
                            temperature=0.7,
                            max_tokens=2000
                        )
                        
                        for chunk in stream:
                            # Stop spinner on first chunk
                            if first_chunk:
                                live.stop()
                                # Clear the thinking line and show response
                                console.print("\r" + " " * 50 + "\r", end="")  # Clear line
                                console.print("[bold cyan]Assistant:[/bold cyan] ", end="")
                                first_chunk = False
                            
                            # Check for interrupt
                            if cli.interrupt_event.is_set():
                                interrupted = True
                                console.print("\n\n[yellow]Response interrupted by user[/yellow]")
                                break
                                
                            console.print(chunk.content, end="")
                            full_response += chunk.content
                except Exception as e:
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

        except ValueError as e:
            if "compartment_id is required" in str(e):
                console.print("\n[red]Error:[/red] OCI compartment ID not configured")
                console.print("\nPlease set it via one of these methods:")
                console.print("1. Environment variable: [cyan]export OCI_COMPARTMENT_ID='your-compartment-id'[/cyan]")
                console.print("2. Coda config file: [cyan]~/.config/coda/config.toml[/cyan]")
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
    else:
        console.print(f"\n[yellow]Provider '{provider}' not implemented yet.[/yellow]")
        console.print("Currently supported: oci_genai")


def _get_system_prompt_for_mode(mode: DeveloperMode) -> str:
    """Get system prompt based on developer mode."""
    prompts = {
        DeveloperMode.GENERAL: "You are a helpful AI assistant. Provide clear, accurate, and useful responses to any questions or requests.",
        DeveloperMode.CODE: "You are a helpful coding assistant. Focus on writing clean, efficient, and well-documented code following best practices.",
        DeveloperMode.DEBUG: "You are a debugging expert. Focus on identifying issues, analyzing error messages, and providing clear solutions with explanations.",
        DeveloperMode.EXPLAIN: "You are a patient teacher. Provide detailed explanations of code, concepts, and implementations in a clear and educational manner.",
        DeveloperMode.REVIEW: "You are a code reviewer. Focus on security, performance, best practices, and potential improvements in the code.",
        DeveloperMode.REFACTOR: "You are a refactoring specialist. Suggest improvements for code clarity, performance, and maintainability while preserving functionality.",
        DeveloperMode.PLAN: "You are a software architect. Help with system design, architecture planning, technology choices, and breaking down complex problems into manageable components.",
    }
    return prompts.get(mode, "")


@click.command()
@click.option('--provider', '-p', default='oci_genai', help='LLM provider to use')
@click.option('--model', '-m', help='Model to use')
@click.option('--debug', is_flag=True, help='Enable debug output')
@click.option('--one-shot', help='Execute a single prompt and exit')
@click.option('--mode', type=click.Choice([m.value for m in DeveloperMode]),
              default=DeveloperMode.GENERAL.value, help='Initial developer mode')
@click.version_option(version=__version__, prog_name='coda')
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
