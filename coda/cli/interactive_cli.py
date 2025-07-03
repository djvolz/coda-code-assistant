"""Interactive CLI with prompt-toolkit for enhanced user experience."""

from collections.abc import Callable
from enum import Enum
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style
from rich.console import Console


class DeveloperMode(Enum):
    """Available developer modes with different AI personalities."""
    CODE = "code"
    DEBUG = "debug"
    EXPLAIN = "explain"
    REVIEW = "review"
    REFACTOR = "refactor"


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

    def get_completions(self, document, complete_event):
        word = document.get_word_before_cursor()

        if document.text.startswith('/'):
            # Complete slash commands
            for cmd_name, cmd in self.commands.items():
                if cmd_name.startswith(word[1:] if word.startswith('/') else word):
                    yield Completion(
                        f'/{cmd_name}',
                        start_position=-len(word),
                        display_meta=cmd.help_text
                    )
                # Also complete aliases
                for alias in cmd.aliases:
                    if alias.startswith(word[1:] if word.startswith('/') else word):
                        yield Completion(
                            f'/{alias}',
                            start_position=-len(word),
                            display_meta=f'Alias for /{cmd_name}'
                        )


class EnhancedCompleter(Completer):
    """Combined completer for slash commands, paths, and common words."""

    def __init__(self, slash_commands: dict[str, SlashCommand]):
        self.slash_completer = SlashCommandCompleter(slash_commands)
        self.path_completer = PathCompleter(expanduser=True)

    def get_completions(self, document, complete_event):
        # If line starts with /, use slash completer
        if document.text.startswith('/'):
            yield from self.slash_completer.get_completions(document, complete_event)
        else:
            # Otherwise use path completer
            yield from self.path_completer.get_completions(document, complete_event)


class InteractiveCLI:
    """Interactive CLI with advanced prompt features using prompt-toolkit."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.current_mode = DeveloperMode.CODE
        self.session = None
        self.commands = self._init_commands()
        self.style = self._create_style()

        # Initialize session with all features
        self._init_session()

    def _init_commands(self) -> dict[str, SlashCommand]:
        """Initialize slash commands."""
        return {
            'help': SlashCommand('help', self._cmd_help, 'Show available commands', ['h', '?']),
            'model': SlashCommand('model', self._cmd_model, 'Switch AI model', ['m']),
            'provider': SlashCommand('provider', self._cmd_provider, 'Switch provider', ['p']),
            'mode': SlashCommand('mode', self._cmd_mode, 'Change developer mode'),
            'session': SlashCommand('session', self._cmd_session, 'Manage sessions', ['s']),
            'theme': SlashCommand('theme', self._cmd_theme, 'Change UI theme'),
            'export': SlashCommand('export', self._cmd_export, 'Export conversation', ['e']),
            'tools': SlashCommand('tools', self._cmd_tools, 'Manage MCP tools', ['t']),
            'clear': SlashCommand('clear', self._cmd_clear, 'Clear conversation', ['cls']),
            'exit': SlashCommand('exit', self._cmd_exit, 'Exit the application', ['quit', 'q']),
        }

    def _create_style(self) -> Style:
        """Create custom style for the prompt."""
        return Style.from_dict({
            # Prompt colors
            'prompt': '#00aa00 bold',
            'prompt.mode': '#888888',

            # Completion colors
            'completion-menu': 'bg:#008888 #ffffff',
            'completion-menu.completion': 'bg:#008888 #ffffff',
            'completion-menu.completion.current': 'bg:#00aaaa #000000',
            'completion-menu.meta.completion': 'bg:#008888 #aaaaaa',
            'completion-menu.meta.completion.current': 'bg:#00aaaa #ffffff',

            # Status bar
            'status-bar': 'bg:#444444 #ffffff',
        })

    def _init_session(self):
        """Initialize the prompt session with all features."""
        # Create history directory if it doesn't exist
        history_dir = Path.home() / '.local' / 'share' / 'coda'
        history_dir.mkdir(parents=True, exist_ok=True)
        history_file = history_dir / 'history.txt'

        self.session = PromptSession(
            history=FileHistory(str(history_file)),
            auto_suggest=AutoSuggestFromHistory(),
            completer=EnhancedCompleter(self.commands),
            style=self.style,
            multiline=False,  # We'll handle multiline manually
            enable_history_search=True,
            vi_mode=False,  # Can be toggled later
            mouse_support=True,
            complete_while_typing=True,
            wrap_lines=True,
        )

    def _get_prompt(self) -> HTML:
        """Generate the prompt with mode indicator."""
        mode_color = {
            DeveloperMode.CODE: 'green',
            DeveloperMode.DEBUG: 'yellow',
            DeveloperMode.EXPLAIN: 'blue',
            DeveloperMode.REVIEW: 'magenta',
            DeveloperMode.REFACTOR: 'cyan',
        }.get(self.current_mode, 'white')

        return HTML(
            f'<prompt>[<prompt.mode>{self.current_mode.value}</prompt.mode>]</prompt> '
            f'<b><ansi{mode_color}>You</ansi{mode_color}></b> '
        )

    async def get_input(self, multiline: bool = False) -> str:
        """Get input from user with rich features."""
        if multiline:
            self.console.print("[dim]Enter multiple lines. Press [Meta+Enter] or [Esc] followed by [Enter] to submit.[/dim]")
            # Temporarily enable multiline mode
            self.session.default_buffer.multiline = True

        try:
            text = await self.session.prompt_async(
                self._get_prompt(),
                multiline=multiline,
            )
            return text.strip()
        except (EOFError, KeyboardInterrupt):
            return '/exit'
        finally:
            # Reset multiline mode
            if multiline:
                self.session.default_buffer.multiline = False

    def process_slash_command(self, command_text: str) -> bool:
        """Process a slash command. Returns True if handled, False otherwise."""
        parts = command_text[1:].split(maxsplit=1)
        if not parts:
            return False

        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ''

        # Check direct command match
        if cmd_name in self.commands:
            self.commands[cmd_name].handler(args)
            return True

        # Check aliases
        for _name, cmd in self.commands.items():
            if cmd_name in cmd.aliases:
                cmd.handler(args)
                return True

        self.console.print(f"[red]Unknown command: /{cmd_name}[/red]")
        self.console.print("Type /help for available commands")
        return True

    # Command handlers
    def _cmd_help(self, args: str):
        """Show help for commands."""
        self.console.print("\n[bold]Available commands:[/bold]")
        for name, cmd in sorted(self.commands.items()):
            aliases_str = f" (aliases: {', '.join('/' + a for a in cmd.aliases)})" if cmd.aliases else ""
            self.console.print(f"  [cyan]/{name}[/cyan]{aliases_str} - {cmd.help_text}")
        self.console.print()

    def _cmd_model(self, args: str):
        """Switch AI model."""
        if not args:
            self.console.print("[yellow]Current model: Not implemented yet[/yellow]")
            self.console.print("Usage: /model <model-name>")
        else:
            self.console.print(f"[yellow]Switching to model: {args} (not implemented yet)[/yellow]")

    def _cmd_provider(self, args: str):
        """Switch provider."""
        if not args:
            self.console.print("[yellow]Current provider: Not implemented yet[/yellow]")
            self.console.print("Usage: /provider <provider-name>")
        else:
            self.console.print(f"[yellow]Switching to provider: {args} (not implemented yet)[/yellow]")

    def _cmd_mode(self, args: str):
        """Change developer mode."""
        if not args:
            self.console.print(f"[yellow]Current mode: {self.current_mode.value}[/yellow]")
            self.console.print("Available modes: " + ", ".join(m.value for m in DeveloperMode))
            return

        try:
            self.current_mode = DeveloperMode(args.lower())
            self.console.print(f"[green]Switched to {self.current_mode.value} mode[/green]")
            self._show_mode_description()
        except ValueError:
            self.console.print(f"[red]Invalid mode: {args}[/red]")
            self.console.print("Available modes: " + ", ".join(m.value for m in DeveloperMode))

    def _show_mode_description(self):
        """Show description for current mode."""
        descriptions = {
            DeveloperMode.CODE: "Optimized for writing new code with best practices",
            DeveloperMode.DEBUG: "Focus on error analysis and debugging assistance",
            DeveloperMode.EXPLAIN: "Detailed code explanations and documentation",
            DeveloperMode.REVIEW: "Security and code quality review",
            DeveloperMode.REFACTOR: "Code improvement and optimization suggestions",
        }
        self.console.print(f"[dim]{descriptions[self.current_mode]}[/dim]")

    def _cmd_session(self, args: str):
        """Manage sessions."""
        self.console.print("[yellow]Session management not implemented yet[/yellow]")

    def _cmd_theme(self, args: str):
        """Change UI theme."""
        self.console.print("[yellow]Theme switching not implemented yet[/yellow]")

    def _cmd_export(self, args: str):
        """Export conversation."""
        self.console.print("[yellow]Export functionality not implemented yet[/yellow]")

    def _cmd_tools(self, args: str):
        """Manage MCP tools."""
        self.console.print("[yellow]MCP tools management not implemented yet[/yellow]")

    def _cmd_clear(self, args: str):
        """Clear conversation."""
        self.console.print("[yellow]Conversation cleared (placeholder)[/yellow]")

    def _cmd_exit(self, args: str):
        """Exit the application."""
        self.console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)
