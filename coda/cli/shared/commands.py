"""Shared command handling logic for CLI modes."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Optional

from rich.console import Console

from coda.providers import ProviderFactory

from .modes import DeveloperMode, get_mode_description


class CommandResult(Enum):
    """Result types for command processing."""

    CONTINUE = "continue"  # Command handled, continue to next iteration
    EXIT = "exit"  # Exit the application
    CLEAR = "clear"  # Clear conversation
    HANDLED = "handled"  # Command handled successfully


class CommandHandler(ABC):
    """Base class for command handling with shared logic."""

    def __init__(self, console: Console):
        self.console = console
        self.current_mode = DeveloperMode.GENERAL
        self.current_model = None
        self.available_models = []
        self.provider_name = None
        self.provider_instance = None
        self.factory = None

    def set_provider_info(
        self,
        provider_name: str,
        provider_instance: Any,
        factory: ProviderFactory,
        model: str,
        models: list,
    ):
        """Set provider information for command processing."""
        self.provider_name = provider_name
        self.provider_instance = provider_instance
        self.factory = factory
        self.current_model = model
        self.available_models = models

    @abstractmethod
    def show_help(self) -> CommandResult:
        """Show help information. Must be implemented by subclasses."""
        pass

    def switch_mode(self, mode_str: str) -> CommandResult:
        """Switch to a different developer mode."""
        if not mode_str:
            # Show current mode and available modes
            self.console.print(f"\n[yellow]Current mode:[/yellow] {self.current_mode.value}")
            self.console.print(f"[dim]{get_mode_description(self.current_mode)}[/dim]\n")

            self.console.print("[bold]Available modes:[/bold]")
            for mode in DeveloperMode:
                if mode == self.current_mode:
                    self.console.print(
                        f"  [green]▶ {mode.value}[/green] - {get_mode_description(mode)}"
                    )
                else:
                    self.console.print(
                        f"  [cyan]{mode.value}[/cyan] - {get_mode_description(mode)}"
                    )

            self.console.print("\n[dim]Usage: /mode <mode_name>[/dim]")
            return CommandResult.HANDLED

        try:
            self.current_mode = DeveloperMode(mode_str.lower())
            self.console.print(f"[green]Switched to {self.current_mode.value} mode[/green]")
            self.console.print(f"[dim]{get_mode_description(self.current_mode)}[/dim]")
            return CommandResult.HANDLED
        except ValueError:
            self.console.print(f"[red]Invalid mode: {mode_str}[/red]")
            valid_modes = ", ".join(m.value for m in DeveloperMode)
            self.console.print(f"Valid modes: {valid_modes}")
            return CommandResult.HANDLED

    def switch_model(self, model_name: str) -> CommandResult:
        """Switch to a different model."""
        if not self.available_models:
            self.console.print("[yellow]No models available.[/yellow]")
            return CommandResult.HANDLED

        if not model_name:
            # Show current model and available models
            self.console.print(f"\n[yellow]Current model:[/yellow] {self.current_model}")
            self.console.print("\n[bold]Available models:[/bold]")

            # Show top 10 models
            for i, model in enumerate(self.available_models[:10]):
                self.console.print(f"  {i+1}. [cyan]{model.id}[/cyan]")

            if len(self.available_models) > 10:
                self.console.print(f"  [dim]... and {len(self.available_models) - 10} more[/dim]")

            self.console.print("\n[dim]Usage: /model <model_name>[/dim]")
            return CommandResult.HANDLED

        # Try to switch to the specified model
        matching_models = [m for m in self.available_models if model_name.lower() in m.id.lower()]
        if matching_models:
            self.current_model = matching_models[0].id
            self.console.print(f"[green]Switched to model: {self.current_model}[/green]")
        else:
            self.console.print(f"[red]Model not found: {model_name}[/red]")

        return CommandResult.HANDLED

    def show_provider_info(self, args: str) -> CommandResult:
        """Show provider information."""
        if not args:
            self.console.print("\n[bold]Provider Management[/bold]")
            self.console.print(f"[yellow]Current provider:[/yellow] {self.provider_name}\n")

            self.console.print("[bold]Available providers:[/bold]")

            # Show all known providers with status
            if self.factory:
                available = self.factory.list_available()
                for provider in available:
                    if provider == self.provider_name:
                        self.console.print(f"  [green]▶ {provider}[/green]")
                    else:
                        self.console.print(f"  [cyan]{provider}[/cyan]")
            else:
                # Default list when factory is not available
                providers = [
                    ("oci_genai", "Oracle Cloud Infrastructure GenAI"),
                    ("ollama", "Local models via Ollama"),
                    ("litellm", "100+ providers via LiteLLM"),
                ]
                for provider_id, desc in providers:
                    if provider_id == self.provider_name:
                        self.console.print(f"  [green]▶ {provider_id}[/green] - {desc}")
                    else:
                        self.console.print(f"  [cyan]{provider_id}[/cyan] - {desc}")

            self.console.print("\n[dim]Note: Provider switching requires restart[/dim]")
        else:
            if self.provider_name and args.lower() == self.provider_name.lower():
                self.console.print(f"[green]Already using {self.provider_name} provider[/green]")
            else:
                self.console.print(
                    "[yellow]Provider switching not supported in current mode. "
                    "Please restart with --provider option.[/yellow]"
                )

        return CommandResult.HANDLED

    def clear_conversation(self) -> CommandResult:
        """Clear the conversation."""
        return CommandResult.CLEAR

    def exit_application(self) -> CommandResult:
        """Exit the application."""
        return CommandResult.EXIT
