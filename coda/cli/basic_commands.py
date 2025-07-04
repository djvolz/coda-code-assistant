"""Basic mode slash command handling."""

from rich.console import Console

from coda.cli.shared import CommandHandler, CommandResult, DeveloperMode, get_system_prompt


class BasicCommandProcessor(CommandHandler):
    """Process slash commands in basic CLI mode."""

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
            "help": lambda: self.show_help(),
            "h": lambda: self.show_help(),
            "?": lambda: self.show_help(),
            "model": lambda: self.switch_model(args),
            "m": lambda: self.switch_model(args),
            "provider": lambda: self.show_provider_info(args),
            "p": lambda: self.show_provider_info(args),
            "mode": lambda: self.switch_mode(args),
            "clear": lambda: self.clear_conversation(),
            "cls": lambda: self.clear_conversation(),
            "exit": lambda: self.exit_application(),
            "quit": lambda: self.exit_application(),
            "q": lambda: self.exit_application(),
        }

        if cmd in commands:
            result = commands[cmd]()
            # Convert CommandResult to string for backward compatibility
            if result == CommandResult.HANDLED:
                return "continue"
            elif result == CommandResult.EXIT:
                return "exit"
            elif result == CommandResult.CLEAR:
                return "clear"
            elif result == CommandResult.CONTINUE:
                return "continue"
            return "continue"
        else:
            self.console.print(f"[red]Unknown command: /{cmd}[/red]")
            self.console.print("Type /help for available commands")
            return "continue"

    def show_help(self) -> CommandResult:
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
            from coda.cli.shared import get_mode_description

            desc = get_mode_description(mode)
            self.console.print(f"  [cyan]{mode.value}[/cyan] - {desc}")
        self.console.print()

        return CommandResult.HANDLED

    def get_system_prompt(self) -> str:
        """Get system prompt based on current mode."""
        return get_system_prompt(self.current_mode)

