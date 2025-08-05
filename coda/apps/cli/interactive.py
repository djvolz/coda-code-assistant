"""Interactive CLI module with rich features using prompt-toolkit."""

import asyncio
import sys
import time
from typing import TYPE_CHECKING

import click
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.spinner import Spinner

if TYPE_CHECKING:
    from ..providers import ProviderFactory

from .agent_chat import AgentChatHandler
from .interactive_cli import DeveloperMode, InteractiveCLI

try:
    from coda.__version__ import __version__
except ImportError:
    __version__ = "dev"

# Create themed console that respects user's theme configuration
from coda.services.config import get_config_service

config_service = get_config_service()
console = config_service.theme_manager.get_console()
theme = config_service.theme_manager.get_console_theme()


async def _check_first_run(console: Console, auto_save_enabled: bool):
    """Check if this is the first run and show auto-save notification."""
    import os
    from pathlib import Path

    # Check for first-run marker in XDG data directory
    data_dir = Path(os.path.expanduser("~/.local/share/coda"))
    first_run_marker = data_dir / ".first_run_complete"

    if not first_run_marker.exists():
        # This is the first run
        data_dir.mkdir(parents=True, exist_ok=True)

        # Show notification
        from rich.panel import Panel

        if auto_save_enabled:
            notification = """[info][bold]Welcome to Coda![/]

[warning]Auto-Save is ENABLED[/] 💾

Your conversations will be automatically saved when you start chatting.
This helps you resume conversations and search through history.

[dim]To disable auto-save:[/]
• Use [info]--no-save[/] flag when starting Coda
• Set [info]autosave = false[/] in ~/.config/coda/config.toml
• Delete sessions with [info]/session delete-all[/]

[dim]Your privacy matters - sessions are stored locally only.[/]"""
        else:
            notification = """[info][bold]Welcome to Coda![/]

[warning]Auto-Save is DISABLED[/] 🔒

Your conversations will NOT be saved automatically.

[dim]To enable auto-save for future sessions:[/]
• Remove [info]--no-save[/] flag when starting Coda
• Set [info]autosave = true[/] in ~/.config/coda/config.toml"""

        console.print("\n")
        console.print(Panel(notification, title="First Run", border_style=theme.panel_border))
        console.print("\n")

        # Create marker file
        try:
            first_run_marker.touch()
        except Exception:
            # Don't fail if we can't create the marker
            pass


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
    try:
        models = provider_instance.list_models()
        console.print(f"[green]✓ Found {len(models)} available models[/green]")
    except Exception:
        # Re-raise the exception to be handled by the caller
        raise

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
        from .completion_selector import CompletionModelSelector

        selector = CompletionModelSelector(unique_models, console)

        # Use interactive selector
        model = await selector.select_interactive()

        if not model:
            console.print("\n[yellow]No model selected. Exiting.[/yellow]")
            return None

    console.print(f"[{theme.success}]Model:[/{theme.success}] {model}")

    console.print(f"[dim]Found {len(unique_models)} unique models available[/dim]")
    console.print("\n[dim]Type /help for commands, /exit or Ctrl+D to quit[/dim]")
    console.print("[dim]Press Ctrl+C to clear input or interrupt AI response[/dim]")
    console.print("[dim]Press Ctrl+R to search command history[/dim]\n")

    return model


async def _setup_provider_and_models(
    provider: str, model: str, debug: bool, console: Console, for_one_shot: bool = False
):
    """Common setup for provider and model selection."""
    from coda.base.providers import ProviderFactory
    from coda.services.config import get_config_service

    config = get_config_service()

    # Apply debug override
    if debug:
        config.set("debug", True)

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

        # Handle model selection differently for one-shot vs interactive
        if for_one_shot:
            # For one-shot, auto-select first model if none specified
            if not model:
                if unique_models:
                    model = unique_models[0].id
                    console.print(f"[dim]No model specified, using: {model}[/dim]")
                else:
                    console.print("[red]No models available[/red]")
                    return None, None, None

            # Validate model exists
            if not any(m.id == model for m in unique_models):
                console.print(f"[red]Model not found: {model}[/red]")
                console.print(f"Available models: {', '.join(m.id for m in unique_models[:5])}")
                return None, None, None

            # Show model info
            console.print(f"\n[{theme.success}]Model:[/{theme.success}] {model}")
        else:
            # For interactive, use the existing selection process
            model = await _select_model(unique_models, model, console)
            if not model:
                return None, None, None

        return provider_instance, unique_models, model

    except ValueError as e:
        _handle_provider_error(e, provider, debug, factory)
    except Exception as e:
        _handle_provider_error(e, provider, debug)


def _handle_provider_error(e: Exception, provider: str, debug: bool, factory=None):
    """Common error handler for provider setup errors."""
    import sys
    import traceback

    if "compartment_id is required" in str(e):
        console.print("\n[red]Error:[/red] OCI compartment ID not configured")
        console.print("\nPlease set it via one of these methods:")
        console.print(
            "1. Environment variable: [cyan]export OCI_COMPARTMENT_ID='your-compartment-id'[/cyan]"
        )
        console.print("2. Coda config file: [cyan]~/.config/coda/config.toml[/cyan]")
    elif "Unknown provider" in str(e):
        console.print(f"\n[red]Error:[/red] Provider '{provider}' not found")
        if factory:
            console.print(f"\nAvailable providers: {', '.join(factory.list_available())}")
    else:
        error_msg = str(e)
        if "OCI GenAI authorization failed" in error_msg:
            # Show the formatted error message from the provider
            console.print(f"\n[red]Error:[/red] {error_msg}")
        else:
            console.print(f"\n[red]Error:[/red] {e}")

    if debug:
        traceback.print_exc()

    sys.exit(1)


async def _handle_chat_interaction(
    provider_instance, cli, messages, console: Console, config=None, use_tools=True
):
    """Handle a single chat interaction including streaming response."""
    from coda.base.providers import Message, Role

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
                # Check if session was loaded and restore conversation history
                loaded_messages = cli.session_commands.get_loaded_messages_for_cli()
                if loaded_messages:
                    # Replace current messages with loaded session messages
                    messages.clear()
                    messages.extend(loaded_messages)
                    console.print(
                        f"[dim]Restored {len(loaded_messages)} messages to conversation history[/dim]"
                    )

                # Check if conversation was cleared
                if cli.session_commands.was_conversation_cleared():
                    messages.clear()
                    console.print("[dim]Cleared conversation history[/dim]")

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

    # Track message in session manager
    cli.session_commands.add_message(
        role="user",
        content=user_input,
        metadata={
            "mode": cli.current_mode.value,
            "provider": provider_instance.name if hasattr(provider_instance, "name") else "unknown",
            "model": cli.current_model,
        },
    )

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
        # Get generation parameters from config or defaults
        if not config:
            from coda.services.config import get_config_service

            config = get_config_service()
        temperature = config.get("temperature", 0.7)
        max_tokens = config.get("max_tokens", 2000)

        if use_tools:
            # Use agent-based chat with timer
            start_time = time.time()

            with Live(
                Spinner("dots", text=f"[bold cyan]{thinking_msg}... 0.0s[/bold cyan]"),
                console=console,
                refresh_per_second=10,
                transient=True,
            ) as live:
                agent_handler = AgentChatHandler(provider_instance, cli, console)

                # Get system prompt from mode
                system_prompt_for_agent = _get_system_prompt_for_mode(cli.current_mode)

                # Create a wrapper to make Live compatible with status interface
                class LiveStatusWrapper:
                    def __init__(self, live_obj, start_time):
                        self.live = live_obj
                        self.start_time = start_time

                    def update(self, text):
                        # Keep the timer format but allow status updates
                        elapsed = time.time() - self.start_time
                        self.live.update(
                            Spinner(
                                "dots",
                                text=f"[bold cyan]{thinking_msg}... {elapsed:.1f}s[/bold cyan]",
                            )
                        )

                    def stop(self):
                        # Stop the live display
                        self.live.stop()

                status_wrapper = LiveStatusWrapper(live, start_time)

                # Create a task to update the timer
                async def update_timer():
                    while True:
                        elapsed = time.time() - start_time
                        live.update(
                            Spinner(
                                "dots",
                                text=f"[bold cyan]{thinking_msg}... {elapsed:.1f}s[/bold cyan]",
                            )
                        )
                        await asyncio.sleep(0.1)

                timer_task = asyncio.create_task(update_timer())

                try:
                    # Execute with agent
                    full_response, updated_messages = await agent_handler.chat_with_agent(
                        messages.copy(),  # Pass a copy to avoid modifying original
                        cli.current_model,
                        temperature,
                        max_tokens,
                        system_prompt_for_agent,
                        status=status_wrapper,  # Pass wrapper that maintains timer
                    )
                finally:
                    # Cancel timer task
                    timer_task.cancel()
                    try:
                        await timer_task
                    except asyncio.CancelledError:
                        pass

                # Update messages to match what happened
                messages.clear()
                messages.extend(updated_messages)

                # Save all messages from the agent interaction to session
                from coda.base.session.tool_storage import format_tool_calls_for_storage

                # Find and save new messages (after the user message which was already saved)
                # Skip the first message (user) since it was already saved above
                for msg in updated_messages[1:]:
                    tool_calls_data = None
                    if hasattr(msg, "tool_calls") and msg.tool_calls:
                        tool_calls_data = format_tool_calls_for_storage(msg.tool_calls)

                    metadata = {
                        "mode": cli.current_mode.value,
                        "provider": (
                            provider_instance.name
                            if hasattr(provider_instance, "name")
                            else "unknown"
                        ),
                        "model": cli.current_model,
                        "tool_call_id": getattr(msg, "tool_call_id", None),
                    }
                    # Add tool_calls to metadata if present
                    if tool_calls_data:
                        metadata["tool_calls"] = tool_calls_data

                    cli.session_commands.add_message(
                        role=msg.role.value if hasattr(msg.role, "value") else str(msg.role),
                        content=msg.content,
                        metadata=metadata,
                    )
        else:
            # Use regular streaming with timer
            start_time = time.time()

            with Live(
                Spinner("dots", text=f"[bold cyan]{thinking_msg}... 0.0s[/bold cyan]"),
                console=console,
                refresh_per_second=10,
                transient=True,
            ) as live:
                # Create timer update task
                async def update_timer():
                    while True:
                        elapsed = time.time() - start_time
                        live.update(
                            Spinner(
                                "dots",
                                text=f"[bold cyan]{thinking_msg}... {elapsed:.1f}s[/bold cyan]",
                            )
                        )
                        await asyncio.sleep(0.1)

                timer_task = asyncio.create_task(update_timer())

                try:
                    stream = provider_instance.chat_stream(
                        messages=chat_messages,
                        model=cli.current_model,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )

                    # Get first chunk to stop spinner
                    for chunk in stream:
                        if first_chunk:
                            # Stop the timer and live display when we get the first chunk
                            timer_task.cancel()
                            try:
                                await timer_task
                            except asyncio.CancelledError:
                                pass
                            live.stop()
                            # Just print the assistant label
                            console.print(
                                f"\n[{theme.info} bold]Assistant:[/{theme.info} bold] ", end=""
                            )
                            first_chunk = False

                        # Check for interrupt
                        if cli.interrupt_event.is_set():
                            interrupted = True
                            console.print("\n\n[yellow]Response interrupted by user[/yellow]")
                            break

                        # Stream the response as plain text
                        console.print(chunk.content, end="")
                        full_response += chunk.content
                finally:
                    # Ensure timer is cancelled if we exit early
                    if not timer_task.done():
                        timer_task.cancel()
                        try:
                            await timer_task
                        except asyncio.CancelledError:
                            pass

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

    # Add assistant message to history (even if interrupted) - only for non-tool path
    if (full_response or interrupted) and not use_tools:
        messages.append(Message(role=Role.ASSISTANT, content=full_response))

        # Track assistant message in session manager
        cli.session_commands.add_message(
            role="assistant",
            content=full_response,
            metadata={
                "mode": cli.current_mode.value,
                "provider": (
                    provider_instance.name if hasattr(provider_instance, "name") else "unknown"
                ),
                "model": cli.current_model,
                "interrupted": interrupted,
            },
        )
    console.print("\n")  # Add spacing after response

    return True  # Continue loop


async def run_interactive_session(
    provider: str, model: str, debug: bool, no_save: bool, resume: bool
):
    """Run the enhanced interactive session."""
    # Initialize interactive CLI
    cli = InteractiveCLI(console)

    # Load configuration
    from coda.services.config import get_config_service

    config = get_config_service()

    # Set auto-save based on config and CLI flag
    # CLI flag takes precedence over config
    if no_save:
        cli.session_commands.auto_save_enabled = False
    else:
        # Use config value, defaulting to True if not specified
        cli.session_commands.auto_save_enabled = config.get("session.autosave", True)

    # Check for first run and show auto-save notification
    await _check_first_run(console, cli.session_commands.auto_save_enabled)

    # Load last session if requested
    if resume:
        console.print("\n[cyan]Resuming last session...[/cyan]")
        result = cli.session_commands._load_last_session()
        if result:  # Error message
            console.print(f"[yellow]{result}[/yellow]")
        else:
            # Successfully loaded, show a separator
            console.print("\n[dim]─" * 50 + "[/dim]\n")

    # Setup provider and models using common function
    provider_instance, unique_models, model = await _setup_provider_and_models(
        provider, model, debug, console, for_one_shot=False
    )
    if not provider_instance:
        return

    # Set model info in CLI for /model command
    cli.current_model = model
    cli.available_models = unique_models
    cli.provider = provider_instance

    try:
        # Interactive chat loop
        # Initialize messages - use loaded messages if available
        if (
            resume
            and hasattr(cli.session_commands, "_messages_loaded")
            and cli.session_commands._messages_loaded
        ):
            # Import Message and Role for conversion
            from coda.base.providers import Message, Role

            # Convert loaded messages to Message objects
            messages = []
            for msg in cli.session_commands.current_messages:
                messages.append(
                    Message(
                        role=Role.USER if msg["role"] == "user" else Role.ASSISTANT,
                        content=msg["content"],
                    )
                )
            # Reset the flag
            cli.session_commands._messages_loaded = False
        else:
            messages = []

        while True:
            continue_chat = await _handle_chat_interaction(
                provider_instance, cli, messages, console, config
            )
            if not continue_chat:
                break

    except SystemExit:
        # Clean exit from /exit command
        pass
    except KeyboardInterrupt:
        # Handle Ctrl+C gracefully - just exit cleanly
        console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
        sys.exit(0)
    except Exception as e:
        _handle_provider_error(e, provider, debug)


def _get_system_prompt_for_mode(mode: DeveloperMode) -> str:
    """Get system prompt based on developer mode."""
    from coda.apps.cli.shared import get_system_prompt

    return get_system_prompt(mode)


async def run_one_shot(
    provider: str, model: str, prompt: str, mode: str, debug: bool, no_save: bool
):
    """Run a single prompt and exit."""
    from coda.base.providers import Message, Role
    from coda.services.config import get_config_service

    config = get_config_service()

    # Setup provider and models using common function
    provider_instance, unique_models, model = await _setup_provider_and_models(
        provider, model, debug, console, for_one_shot=True
    )
    if not provider_instance:
        return

    try:
        # Convert mode string to enum
        developer_mode = DeveloperMode(mode.lower())

        # Get system prompt for mode
        system_prompt = _get_system_prompt_for_mode(developer_mode)

        # Create messages
        messages = []
        if system_prompt:
            messages.append(Message(role=Role.SYSTEM, content=system_prompt))
        messages.append(Message(role=Role.USER, content=prompt))

        # Get response
        console.print(f"\n[{theme.user_message} bold]You:[/{theme.user_message} bold] {prompt}")

        # Use appropriate handler based on tool support
        if developer_mode != DeveloperMode.GENERAL:
            # Use agent for tool-enabled models in non-general modes
            from .agent_chat import AgentChatHandler

            agent_handler = AgentChatHandler(provider_instance, None, console)
            response_content, _ = await agent_handler.chat_with_agent(
                [Message(role=Role.USER, content=prompt)],
                model,
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2000),
                system_prompt=system_prompt,
            )
        else:
            # Use simple chat without tools
            response = provider_instance.chat(
                messages=messages,
                model=model,
                temperature=config.get("temperature", 0.7),
                max_tokens=config.get("max_tokens", 2000),
            )
            response_content = response.content

        # Display response
        console.print(f"\n[{theme.info} bold]Assistant:[/{theme.info} bold] {response_content}")

        # Save to session if auto-save is enabled
        if not no_save:
            from .session_commands import SessionCommands

            session_commands = SessionCommands()
            session_commands.auto_save_enabled = not no_save

            # Add messages to session
            session_commands.add_message(
                role="user",
                content=prompt,
                metadata={
                    "mode": developer_mode.value,
                    "provider": provider,
                    "model": model,
                    "one_shot": True,
                },
            )
            session_commands.add_message(
                role="assistant",
                content=response_content,
                metadata={
                    "mode": developer_mode.value,
                    "provider": provider,
                    "model": model,
                    "one_shot": True,
                },
            )

    except Exception as e:
        _handle_provider_error(e, provider, debug)


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
@click.option("--no-save", is_flag=True, help="Disable auto-saving of conversations")
@click.option("--resume", is_flag=True, help="Resume the most recent session")
@click.version_option(version=__version__, prog_name="coda")
def interactive_main(
    provider: str, model: str, debug: bool, one_shot: str, mode: str, no_save: bool, resume: bool
):
    """Run Coda in interactive mode with rich CLI features"""
    from .banner import create_welcome_banner

    welcome_text = create_welcome_banner(theme)

    console.print(Panel(welcome_text, title="Welcome", border_style=theme.panel_border))

    if one_shot:
        # Handle one-shot mode
        asyncio.run(run_one_shot(provider, model, one_shot, mode, debug, no_save))
    else:
        # Run interactive session
        asyncio.run(run_interactive_session(provider, model, debug, no_save, resume))


if __name__ == "__main__":
    try:
        interactive_main()
    except KeyboardInterrupt:
        # Handle Ctrl+C at the top level
        console.print("\n\n[dim]Interrupted. Goodbye![/dim]")
        sys.exit(0)
