"""Basic mode slash command handling."""


from coda.cli.shared import CommandHandler, CommandResult, get_system_prompt


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
        from coda.cli.shared import (
            print_basic_keyboard_shortcuts,
            print_command_help,
            print_developer_modes,
        )

        print_command_help(self.console, "Basic Mode")
        print_developer_modes(self.console)
        print_basic_keyboard_shortcuts(self.console)

        self.console.print("[dim]Type any command without arguments to see its options[/dim]")

        return CommandResult.HANDLED

    def get_system_prompt(self) -> str:
        """Get system prompt based on current mode."""
        return get_system_prompt(self.current_mode)
