"""Interactive CLI with prompt-toolkit for enhanced user experience."""

import asyncio
from collections.abc import Callable
from pathlib import Path
from threading import Event

import yaml
from prompt_toolkit import PromptSession
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from .shared import CommandHandler, CommandResult, DeveloperMode


class SlashCommand:
    """Represents a slash command with its handler and help text."""

    def __init__(self, name: str, handler: Callable, help_text: str, aliases: list[str] = None):
        self.name = name
        self.handler = handler
        self.help_text = help_text
        self.aliases = aliases or []


class SlashCommandCompleter(Completer):
    """Custom completer for slash commands."""

    def __init__(self, commands: dict[str, SlashCommand]):
        self.commands = commands
        self.command_options = self._load_command_options()

    def _load_command_options(self) -> dict[str, list[tuple[str, str]]]:
        """Load command options from configuration file."""
        config_path = Path(__file__).parent / "commands_config.yaml"

        # Fallback to hardcoded options if config file not found
        default_options = {
            "mode": [
                ("general", "General conversation and assistance"),
                ("code", "Optimized for writing new code"),
                ("debug", "Focus on error analysis"),
                ("explain", "Detailed code explanations"),
                ("review", "Security and code quality review"),
                ("refactor", "Code improvement suggestions"),
                ("plan", "Architecture planning and system design"),
            ],
            "provider": [
                ("oci_genai", "Oracle Cloud Infrastructure GenAI"),
                ("ollama", "Local models via Ollama (coming soon)"),
                ("openai", "OpenAI GPT models (coming soon)"),
                ("litellm", "100+ providers via LiteLLM (coming soon)"),
            ],
            "session": [
                ("save", "Save current conversation"),
                ("load", "Load a saved conversation"),
                ("list", "List all saved sessions"),
                ("branch", "Create a branch from current conversation"),
                ("delete", "Delete a saved session"),
            ],
            "theme": [
                ("default", "Default color scheme"),
                ("dark", "Dark mode optimized"),
                ("light", "Light terminal theme"),
                ("minimal", "Minimal colors"),
                ("vibrant", "High contrast colors"),
            ],
            "export": [
                ("markdown", "Export as Markdown file"),
                ("json", "Export as JSON with metadata"),
                ("txt", "Export as plain text"),
                ("html", "Export as HTML with syntax highlighting"),
            ],
            "tools": [
                ("list", "List all available tools"),
                ("info", "Show detailed tool information"),
                ("categories", "Show all tool categories"),
                ("stats", "Show tool statistics"),
                ("help", "Show detailed tools help"),
            ],
        }

        try:
            if config_path.exists():
                with open(config_path) as f:
                    config = yaml.safe_load(f)

                options = {}
                for cmd_name, cmd_data in config.get("commands", {}).items():
                    options[cmd_name] = [
                        (opt["name"], opt["description"]) for opt in cmd_data.get("options", [])
                    ]
                return options
        except Exception:
            # If anything fails, use defaults
            pass

        return default_options

    def get_completions(self, document, complete_event):
        # Get the current text
        text = document.text_before_cursor

        # If we just typed '/', show all commands immediately
        if text == "/":
            yield from self._complete_all_commands()
        elif text.startswith("/"):
            # Check if we have a complete command with a space
            parts = text.split(" ", 1)

            if len(parts) == 2:  # We have a command and possibly partial argument
                yield from self._complete_command_arguments(parts[0][1:], parts[1])
            else:
                # Complete the command itself
                yield from self._complete_command_names(text)

    def _complete_all_commands(self):
        """Yield completions for all available commands."""
        for cmd_name, cmd in self.commands.items():
            yield Completion(
                "/" + cmd_name,  # Include the slash
                start_position=-1,  # Replace just the '/'
                display_meta=cmd.help_text,
            )

    def _complete_command_arguments(self, cmd_part: str, arg_part: str):
        """Yield completions for command arguments."""
        if cmd_part not in self.command_options:
            return

        options = self.command_options[cmd_part]

        if not arg_part:  # Just typed space, show all options
            for option, description in options:
                yield Completion(option, start_position=0, display_meta=description)
        else:  # Partial argument typed
            for option, description in options:
                if option.startswith(arg_part):
                    yield Completion(
                        option, start_position=-len(arg_part), display_meta=description
                    )

    def _complete_command_names(self, text: str):
        """Yield completions for command names and aliases."""
        word = text[1:]  # Get the part after '/'

        for cmd_name, cmd in self.commands.items():
            if cmd_name.startswith(word):
                yield Completion(
                    "/" + cmd_name,  # Include the slash in completion
                    start_position=-len(text),  # Replace entire text including '/'
                    display_meta=cmd.help_text,
                )
            # Also complete aliases
            for alias in cmd.aliases:
                if alias.startswith(word):
                    yield Completion(
                        "/" + alias,  # Include the slash in completion
                        start_position=-len(text),  # Replace entire text including '/'
                        display_meta=f"Alias for /{cmd_name}",
                    )


class EnhancedCompleter(Completer):
    """Combined completer for slash commands and file paths."""

    def __init__(self, slash_commands: dict[str, SlashCommand]):
        self.slash_completer = SlashCommandCompleter(slash_commands)
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor

        # If line starts with /, use slash completer
        if text.startswith("/"):
            yield from self.slash_completer.get_completions(document, complete_event)
        # If empty or just whitespace, show available slash commands
        elif not text.strip():
            # Show all slash commands
            for cmd_name, cmd in self.slash_completer.commands.items():
                yield Completion(
                    f"/{cmd_name}",
                    start_position=0,
                    display_meta=cmd.help_text,
                    style="fg:cyan",
                )
        # Only show path completions if text contains / or ~ (indicating a path)
        elif "/" in text or text.startswith("~"):
            yield from self.path_completer.get_completions(document, complete_event)
        # Otherwise, no completions for regular text
        else:
            # Explicitly return nothing - no completions for regular text
            return


class InteractiveCLI(CommandHandler):
    """Interactive CLI with advanced prompt features using prompt-toolkit."""

    def __init__(self, console: Console = None):
        super().__init__(console or Console())
        self.session = None
        self.commands = self._init_commands()
        self.style = self._create_style()

        # For interrupt handling
        self.interrupt_event = Event()
        self.last_escape_time = 0
        self.escape_count = 0
        self.last_ctrl_c_time = 0
        self.ctrl_c_count = 0

        # Initialize session with all features
        self._init_session()

    def _init_commands(self) -> dict[str, SlashCommand]:
        """Initialize slash commands."""
        return {
            "help": SlashCommand("help", self._cmd_help, "Show available commands", ["h", "?"]),
            "model": SlashCommand("model", self._cmd_model, "Switch AI model", ["m"]),
            "provider": SlashCommand("provider", self._cmd_provider, "Switch provider", ["p"]),
            "mode": SlashCommand("mode", self._cmd_mode, "Change developer mode"),
            "session": SlashCommand("session", self._cmd_session, "Manage sessions", ["s"]),
            "theme": SlashCommand("theme", self._cmd_theme, "Change UI theme"),
            "export": SlashCommand("export", self._cmd_export, "Export conversation", ["e"]),
            "tools": SlashCommand("tools", self._cmd_tools, "Manage MCP tools", ["t"]),
            "clear": SlashCommand("clear", self._cmd_clear, "Clear conversation", ["cls"]),
            "exit": SlashCommand("exit", self._cmd_exit, "Exit the application", ["quit", "q"]),
        }

    def _create_style(self) -> Style:
        """Create custom style for the prompt."""
        return Style.from_dict(
            {
                # Prompt colors
                "prompt": "#00aa00 bold",
                "prompt.mode": "#888888",
                # Completion colors - more visible
                "completion-menu": "bg:#2c2c2c #ffffff",
                "completion-menu.completion": "bg:#2c2c2c #ffffff",
                "completion-menu.completion.current": "bg:#005588 #ffffff bold",
                "completion-menu.meta.completion": "bg:#2c2c2c #888888",
                "completion-menu.meta.completion.current": "bg:#005588 #aaaaaa",
                # Scrollbar
                "scrollbar.background": "bg:#2c2c2c",
                "scrollbar.button": "bg:#888888",
                # Status bar
                "status-bar": "bg:#444444 #ffffff",
            }
        )

    def _init_session(self):
        """Initialize the prompt session with all features."""
        # Create history directory if it doesn't exist
        history_dir = Path.home() / ".local" / "share" / "coda"
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / "history.txt"

        # Create key bindings
        kb = KeyBindings()

        # Note: We handle interrupts via signal handler during AI responses
        # Double escape is not reliable with prompt-toolkit during streaming

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=None,  # Disable auto-suggestions from history
            completer=EnhancedCompleter(self.commands),
            style=self.style,
            multiline=False,  # We'll handle multiline manually
            enable_history_search=True,
            vi_mode=False,  # Can be toggled later
            mouse_support=False,  # Disable to preserve terminal scrollback
            complete_while_typing=False,  # Only show completions on Tab
            complete_in_thread=True,  # Better performance
            complete_style="MULTI_COLUMN",  # Show completions in columns
            wrap_lines=True,
            key_bindings=kb,
        )

    def _get_prompt(self) -> HTML:
        """Generate the prompt with mode indicator."""
        mode_color = {
            DeveloperMode.GENERAL: "white",
            DeveloperMode.CODE: "green",
            DeveloperMode.DEBUG: "yellow",
            DeveloperMode.EXPLAIN: "blue",
            DeveloperMode.REVIEW: "magenta",
            DeveloperMode.REFACTOR: "cyan",
            DeveloperMode.PLAN: "red",
        }.get(self.current_mode, "white")

        # Simple prompt
        return HTML(
            f"<prompt>[<prompt.mode>{self.current_mode.value}</prompt.mode>]</prompt> "
            f"<b><ansi{mode_color}>You</ansi{mode_color}></b> "
        )

    async def get_input(self, multiline: bool = False) -> str:
        """Get input from user with rich features."""
        if multiline:
            self.console.print(
                "[dim]Enter multiple lines. Press [Meta+Enter] or [Esc] followed by [Enter] to submit.[/dim]"
            )
            # Temporarily enable multiline mode
            self.session.default_buffer.multiline = True

        try:
            text = await self.session.prompt_async(
                self._get_prompt(),
                multiline=multiline,
            )
            # Reset Ctrl+C count on successful input
            self.ctrl_c_count = 0
            return text.strip()
        except EOFError:
            return "/exit"
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            # Clear the current line and return empty string
            # The main loop will skip empty input
            self.console.print()  # New line for cleaner display
            return ""
        finally:
            # Reset multiline mode
            if multiline:
                self.session.default_buffer.multiline = False

    async def process_slash_command(self, command_text: str) -> bool:
        """Process a slash command. Returns True if handled, False otherwise."""
        parts = command_text[1:].split(maxsplit=1)
        if not parts:
            return False

        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # Check direct command match
        if cmd_name in self.commands:
            handler = self.commands[cmd_name].handler
            # Check if handler is async
            if asyncio.iscoroutinefunction(handler):
                await handler(args)
            else:
                handler(args)
            return True

        # Check aliases
        for _name, cmd in self.commands.items():
            if cmd_name in cmd.aliases:
                handler = cmd.handler
                if asyncio.iscoroutinefunction(handler):
                    await handler(args)
                else:
                    handler(args)
                return True

        self.console.print(f"[red]Unknown command: /{cmd_name}[/red]")
        self.console.print("Type /help for available commands")
        return True

    # Command handlers
    def show_help(self) -> CommandResult:
        """Show help for commands - interactive mode specific."""
        from coda.cli.shared import (
            print_command_help,
            print_developer_modes,
            print_interactive_keyboard_shortcuts,
            print_interactive_only_commands,
        )

        print_command_help(self.console, "Interactive Mode")
        print_interactive_only_commands(self.console)
        print_developer_modes(self.console)
        print_interactive_keyboard_shortcuts(self.console)

        self.console.print("[dim]Type any command without arguments to see its options[/dim]")
        return CommandResult.HANDLED

    def _cmd_help(self, args: str):
        """Wrapper for show_help to maintain compatibility."""
        self.show_help()

    async def _cmd_model(self, args: str):
        """Switch AI model - enhanced for interactive mode."""
        if not self.available_models:
            self.console.print(
                "[yellow]No models available. Please connect to a provider first.[/yellow]"
            )
            return

        if not args:
            # Show interactive model selector
            from .model_selector import ModelSelector

            selector = ModelSelector(self.available_models, self.console)

            new_model = await selector.select_model_interactive()
            if new_model:
                self.current_model = new_model
                self.console.print(f"\n[green]Switched to model: {new_model}[/green]")
            else:
                self.console.print(f"\n[yellow]Current model: {self.current_model}[/yellow]")
        else:
            # Use the shared model switching logic
            self.switch_model(args)

    def _cmd_provider(self, args: str):
        """Switch provider."""
        self.show_provider_info(args)

    def _cmd_mode(self, args: str):
        """Change developer mode."""
        self.switch_mode(args)

    def _show_coming_soon_command(
        self, command_name: str, title: str, options: list[tuple[str, str]], usage: str
    ):
        """Helper to show coming soon commands with consistent formatting."""
        self.console.print(f"\n[bold]{title}[/bold] [yellow](Coming soon)[/yellow]")
        self.console.print(
            f"\n[bold]Planned {('subcommands' if 'subcommand' in usage else 'options')}:[/bold]"
        )
        for option, description in options:
            self.console.print(f"  [cyan]{option}[/cyan] - {description}")
        self.console.print(f"\n[dim]Usage: {usage}[/dim]")

    def _cmd_session(self, args: str):
        """Manage sessions."""
        if not args:
            options = self.session.completer.slash_completer.command_options.get("session", [])
            self._show_coming_soon_command(
                "session", "Session Management", options, "/session <subcommand>"
            )
        else:
            self.console.print(f"[yellow]Session command '{args}' not implemented yet[/yellow]")

    def _cmd_theme(self, args: str):
        """Change UI theme."""
        if not args:
            options = self.session.completer.slash_completer.command_options.get("theme", [])
            self._show_coming_soon_command(
                "theme", "Theme Settings", options, "/theme <theme_name>"
            )
        else:
            self.console.print(f"[yellow]Theme '{args}' not implemented yet[/yellow]")

    def _cmd_export(self, args: str):
        """Export conversation."""
        if not args:
            options = self.session.completer.slash_completer.command_options.get("export", [])
            self._show_coming_soon_command(
                "export", "Export Options", options, "/export <format> [filename]"
            )
        else:
            self.console.print(f"[yellow]Export format '{args}' not implemented yet[/yellow]")

    def _cmd_tools(self, args: str):
        """Manage MCP tools."""
        # Use the shared command handler
        result = self.handle_tools_command(args)
        return result

    def _cmd_clear(self, args: str):
        """Clear conversation."""
        self.console.print("[yellow]Conversation cleared (placeholder)[/yellow]")
        # Note: Actual clearing is handled by the caller

    def _cmd_exit(self, args: str):
        """Exit the application."""
        self.console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)

    def get_system_prompt(self) -> str:
        """Get system prompt based on current mode."""
        from .shared import get_system_prompt

        return get_system_prompt(self.current_mode)

    def reset_interrupt(self):
        """Reset the interrupt state."""
        self.interrupt_event.clear()
        self.escape_count = 0
        self.ctrl_c_count = 0

    def start_interrupt_listener(self):
        """Start signal handler for Ctrl+C during AI response."""
        import signal

        def interrupt_handler(signum, frame):
            """Handle Ctrl+C during AI response."""
            self.interrupt_event.set()

        # Store the old handler
        self.old_sigint_handler = signal.signal(signal.SIGINT, interrupt_handler)

    def stop_interrupt_listener(self):
        """Restore original signal handler."""
        import signal

        if hasattr(self, "old_sigint_handler"):
            signal.signal(signal.SIGINT, self.old_sigint_handler)
