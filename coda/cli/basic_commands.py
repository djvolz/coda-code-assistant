"""Basic mode slash command handling."""

from enum import Enum
from typing import Any

from rich.console import Console

from coda.providers import ProviderFactory


class DeveloperMode(Enum):
    """Available developer modes with different AI personalities."""

    GENERAL = "general"
    CODE = "code"
    DEBUG = "debug"
    EXPLAIN = "explain"
    REVIEW = "review"
    REFACTOR = "refactor"
    PLAN = "plan"


class BasicCommandProcessor:
    """Process slash commands in basic CLI mode."""

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

    def process_command(self, user_input: str) -> str | None:
        """
        Process a slash command.
        Returns:
        - None: Continue normal chat
        - "continue": Skip this iteration (command was handled)
        - "exit": Exit the application
        - "clear": Clear conversation
        """
        if not user_input.startswith("/"):
            return None

        parts = user_input[1:].split(maxsplit=1)
        if not parts:
            return None

        cmd = parts[0].lower()
        args = parts[1] if len(parts) > 1 else ""

        # Map commands to handlers
        commands = {
            "help": self._cmd_help,
            "h": self._cmd_help,
            "?": self._cmd_help,
            "model": self._cmd_model,
            "m": self._cmd_model,
            "provider": self._cmd_provider,
            "p": self._cmd_provider,
            "mode": self._cmd_mode,
            "clear": self._cmd_clear,
            "cls": self._cmd_clear,
            "exit": self._cmd_exit,
            "quit": self._cmd_exit,
            "q": self._cmd_exit,
        }

        if cmd in commands:
            return commands[cmd](args)
        else:
            self.console.print(f"[red]Unknown command: /{cmd}[/red]")
            self.console.print("Type /help for available commands")
            return "continue"

    def _cmd_help(self, args: str) -> str:
        """Show help for commands."""
        self.console.print("\n[bold]Available Commands (Basic Mode)[/bold]\n")

        self.console.print("[bold]AI Settings:[/bold]")
        self.console.print("  [cyan]/model[/cyan] (/m) - Switch AI model")
        self.console.print("  [cyan]/provider[/cyan] (/p) - Switch provider")
        self.console.print("  [cyan]/mode[/cyan] - Change developer mode")
        self.console.print()

        self.console.print("[bold]System:[/bold]")
        self.console.print("  [cyan]/clear[/cyan] (/cls) - Clear conversation")
        self.console.print("  [cyan]/help[/cyan] (/h, /?) - Show this help")
        self.console.print("  [cyan]/exit[/cyan] (/quit, /q) - Exit the application")
        self.console.print()

        self.console.print("[bold]Developer Modes:[/bold]")
        for mode in DeveloperMode:
            desc = self._get_mode_description(mode)
            self.console.print(f"  [cyan]{mode.value}[/cyan] - {desc}")
        self.console.print()

        return "continue"

    def _cmd_model(self, args: str) -> str:
        """Switch AI model."""
        if not self.available_models:
            self.console.print("[yellow]No models available.[/yellow]")
            return "continue"

        if not args:
            # Show current model and available models
            self.console.print(f"\n[yellow]Current model:[/yellow] {self.current_model}")
            self.console.print("\n[bold]Available models:[/bold]")

            # Show top 10 models
            for i, model in enumerate(self.available_models[:10]):
                self.console.print(f"  {i+1}. [cyan]{model.id}[/cyan]")

            if len(self.available_models) > 10:
                self.console.print(f"  [dim]... and {len(self.available_models) - 10} more[/dim]")

            self.console.print("\n[dim]Usage: /model <model_name>[/dim]")
        else:
            # Try to switch to the specified model
            matching_models = [m for m in self.available_models if args.lower() in m.id.lower()]
            if matching_models:
                self.current_model = matching_models[0].id
                self.console.print(f"[green]Switched to model: {self.current_model}[/green]")
            else:
                self.console.print(f"[red]Model not found: {args}[/red]")

        return "continue"

    def _cmd_provider(self, args: str) -> str:
        """Switch provider."""
        if not args:
            self.console.print(f"\n[yellow]Current provider:[/yellow] {self.provider_name}")
            self.console.print("\n[bold]Available providers:[/bold]")

            if self.factory:
                for provider in self.factory.list_available():
                    if provider == self.provider_name:
                        self.console.print(f"  [green]▶ {provider}[/green]")
                    else:
                        self.console.print(f"  [cyan]{provider}[/cyan]")
            self.console.print("\n[dim]Note: Provider switching requires restart[/dim]")
        else:
            self.console.print(
                "[yellow]Provider switching not supported in basic mode. "
                "Please restart with --provider option.[/yellow]"
            )

        return "continue"

    def _cmd_mode(self, args: str) -> str:
        """Change developer mode."""
        if not args:
            self.console.print(f"\n[yellow]Current mode:[/yellow] {self.current_mode.value}")
            self.console.print(f"[dim]{self._get_mode_description(self.current_mode)}[/dim]\n")

            self.console.print("[bold]Available modes:[/bold]")
            for mode in DeveloperMode:
                if mode == self.current_mode:
                    self.console.print(
                        f"  [green]▶ {mode.value}[/green] - {self._get_mode_description(mode)}"
                    )
                else:
                    self.console.print(
                        f"  [cyan]{mode.value}[/cyan] - {self._get_mode_description(mode)}"
                    )

            self.console.print("\n[dim]Usage: /mode <mode_name>[/dim]")
        else:
            try:
                self.current_mode = DeveloperMode(args.lower())
                self.console.print(f"[green]Switched to {self.current_mode.value} mode[/green]")
                self.console.print(f"[dim]{self._get_mode_description(self.current_mode)}[/dim]")
            except ValueError:
                self.console.print(f"[red]Invalid mode: {args}[/red]")
                valid_modes = ", ".join(m.value for m in DeveloperMode)
                self.console.print(f"Valid modes: {valid_modes}")

        return "continue"

    def _cmd_clear(self, args: str) -> str:
        """Clear conversation."""
        return "clear"

    def _cmd_exit(self, args: str) -> str:
        """Exit the application."""
        return "exit"

    def _get_mode_description(self, mode: DeveloperMode) -> str:
        """Get description for a specific mode."""
        descriptions = {
            DeveloperMode.GENERAL: "General conversation and assistance",
            DeveloperMode.CODE: "Optimized for writing new code with best practices",
            DeveloperMode.DEBUG: "Focus on error analysis and debugging assistance",
            DeveloperMode.EXPLAIN: "Detailed code explanations and documentation",
            DeveloperMode.REVIEW: "Security and code quality review",
            DeveloperMode.REFACTOR: "Code improvement and optimization suggestions",
            DeveloperMode.PLAN: "Architecture planning and system design",
        }
        return descriptions.get(mode, "")

    def get_system_prompt(self) -> str:
        """Get system prompt based on current mode."""
        prompts = {
            DeveloperMode.GENERAL: "You are a helpful AI assistant. Provide clear, accurate, and useful responses to any questions or requests.",
            DeveloperMode.CODE: "You are a helpful coding assistant. Focus on writing clean, efficient, and well-documented code following best practices.",
            DeveloperMode.DEBUG: "You are a debugging expert. Focus on identifying issues, analyzing error messages, and providing clear solutions with explanations.",
            DeveloperMode.EXPLAIN: "You are a patient teacher. Provide detailed explanations of code, concepts, and implementations in a clear and educational manner.",
            DeveloperMode.REVIEW: "You are a code reviewer. Focus on security, performance, best practices, and potential improvements in the code.",
            DeveloperMode.REFACTOR: "You are a refactoring specialist. Suggest improvements for code clarity, performance, and maintainability while preserving functionality.",
            DeveloperMode.PLAN: "You are a software architect. Help with system design, architecture planning, technology choices, and breaking down complex problems into manageable components.",
        }
        return prompts.get(self.current_mode, "")
