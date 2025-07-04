"""Interactive CLI with prompt-toolkit for enhanced user experience."""

import asyncio
from collections.abc import Callable
from enum import Enum
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.filters import Condition
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
        # Get the current text
        text = document.text_before_cursor
        
        # If we just typed '/', show all commands immediately
        if text == '/':
            for cmd_name, cmd in self.commands.items():
                yield Completion(
                    '/' + cmd_name,  # Include the slash
                    start_position=-1,  # Replace just the '/'
                    display_meta=cmd.help_text
                )
        elif text.startswith('/'):
            # Complete based on what's after the slash
            word = text[1:]  # Get the part after '/'
            for cmd_name, cmd in self.commands.items():
                if cmd_name.startswith(word):
                    yield Completion(
                        '/' + cmd_name,  # Include the slash in completion
                        start_position=-len(text),  # Replace entire text including '/'
                        display_meta=cmd.help_text
                    )
                # Also complete aliases
                for alias in cmd.aliases:
                    if alias.startswith(word):
                        yield Completion(
                            '/' + alias,  # Include the slash in completion
                            start_position=-len(text),  # Replace entire text including '/'
                            display_meta=f'Alias for /{cmd_name}'
                        )


class EnhancedCompleter(Completer):
    """Combined completer for slash commands, paths, and common words."""

    def __init__(self, slash_commands: dict[str, SlashCommand]):
        self.slash_completer = SlashCommandCompleter(slash_commands)
        self.path_completer = PathCompleter(expanduser=True)
        
        # Common starter phrases for AI interactions
        self.common_starters = [
            ("Can you help me", "Ask for assistance"),
            ("Explain", "Request explanation"),
            ("How do I", "Ask how to do something"),
            ("What is", "Ask for definition"),
            ("Debug this", "Request debugging help"),
            ("Review this code", "Request code review"),
            ("Refactor", "Request code refactoring"),
            ("Write a", "Request code generation"),
            ("Fix", "Request bug fix"),
            ("Improve", "Request improvements"),
        ]

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        
        # If line starts with /, use slash completer
        if text.startswith('/'):
            yield from self.slash_completer.get_completions(document, complete_event)
        # If empty or just whitespace, show both slash commands and common starters
        elif not text.strip():
            # Show all slash commands first
            for cmd_name, cmd in self.slash_completer.commands.items():
                yield Completion(
                    f'/{cmd_name}',
                    start_position=0,
                    display_meta=cmd.help_text,
                    style='fg:cyan',
                )
            
            # Then show common starter phrases
            for starter, description in self.common_starters:
                yield Completion(
                    starter,
                    start_position=0,
                    display_meta=description,
                    style='fg:gray',
                )
        else:
            # Check if we're typing a common starter
            lower_text = text.lower()
            for starter, description in self.common_starters:
                if starter.lower().startswith(lower_text):
                    yield Completion(
                        starter,
                        start_position=-len(text),
                        display_meta=description,
                        style='fg:gray',
                    )
            
            # Also use path completer
            yield from self.path_completer.get_completions(document, complete_event)


class InteractiveCLI:
    """Interactive CLI with advanced prompt features using prompt-toolkit."""

    def __init__(self, console: Console = None):
        self.console = console or Console()
        self.current_mode = DeveloperMode.CODE
        self.current_model = None
        self.available_models = []
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

            # Completion colors - more visible
            'completion-menu': 'bg:#2c2c2c #ffffff',
            'completion-menu.completion': 'bg:#2c2c2c #ffffff',
            'completion-menu.completion.current': 'bg:#005588 #ffffff bold',
            'completion-menu.meta.completion': 'bg:#2c2c2c #888888',
            'completion-menu.meta.completion.current': 'bg:#005588 #aaaaaa',
            
            # Scrollbar
            'scrollbar.background': 'bg:#2c2c2c',
            'scrollbar.button': 'bg:#888888',

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
            complete_in_thread=True,  # Better performance
            complete_style='MULTI_COLUMN',  # Show completions in columns
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

    async def process_slash_command(self, command_text: str) -> bool:
        """Process a slash command. Returns True if handled, False otherwise."""
        parts = command_text[1:].split(maxsplit=1)
        if not parts:
            return False

        cmd_name = parts[0]
        args = parts[1] if len(parts) > 1 else ''

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
    def _cmd_help(self, args: str):
        """Show help for commands."""
        self.console.print("\n[bold]Available Commands[/bold]\n")
        
        # Group commands by category
        categories = {
            "AI Settings": ["model", "provider", "mode"],
            "Session": ["session", "export", "clear"],
            "System": ["tools", "theme", "help", "exit"],
        }
        
        for category, cmd_names in categories.items():
            self.console.print(f"[bold]{category}:[/bold]")
            for cmd_name in cmd_names:
                if cmd_name in self.commands:
                    cmd = self.commands[cmd_name]
                    aliases_str = f" (/{'/'.join(cmd.aliases)})" if cmd.aliases else ""
                    self.console.print(f"  [cyan]/{cmd_name}[/cyan]{aliases_str} - {cmd.help_text}")
            self.console.print()
        
        self.console.print("[dim]Type any command without arguments to see its options[/dim]")

    async def _cmd_model(self, args: str):
        """Switch AI model."""
        if not self.available_models:
            self.console.print("[yellow]No models available. Please connect to a provider first.[/yellow]")
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
            # Direct model switch
            # Check if the model exists
            matching_models = [m for m in self.available_models if args.lower() in m.id.lower()]
            if matching_models:
                self.current_model = matching_models[0].id
                self.console.print(f"[green]Switched to model: {self.current_model}[/green]")
            else:
                self.console.print(f"[red]Model not found: {args}[/red]")
                self.console.print("Use /model without arguments to see available models.")

    def _cmd_provider(self, args: str):
        """Switch provider."""
        if not args:
            self.console.print("\n[bold]Provider Management[/bold]")
            self.console.print("[yellow]Current provider:[/yellow] oci_genai\n")
            
            self.console.print("[bold]Available providers:[/bold]")
            self.console.print("  [green]▶ oci_genai[/green] - Oracle Cloud Infrastructure GenAI")
            self.console.print("  [cyan]ollama[/cyan] - Local models via Ollama [yellow](Coming soon)[/yellow]")
            self.console.print("  [cyan]openai[/cyan] - OpenAI GPT models [yellow](Coming soon)[/yellow]")
            self.console.print("  [cyan]litellm[/cyan] - 100+ providers via LiteLLM [yellow](Coming soon)[/yellow]")
            self.console.print("\n[dim]Usage: /provider <provider_name>[/dim]")
        else:
            if args.lower() == "oci_genai":
                self.console.print("[green]Already using oci_genai provider[/green]")
            else:
                self.console.print(f"[yellow]Provider '{args}' not implemented yet[/yellow]")
                self.console.print("Currently supported: oci_genai")

    def _cmd_mode(self, args: str):
        """Change developer mode."""
        if not args:
            self.console.print(f"\n[yellow]Current mode:[/yellow] {self.current_mode.value}")
            self.console.print(f"[dim]{self._get_mode_description(self.current_mode)}[/dim]\n")
            
            self.console.print("[bold]Available modes:[/bold]")
            for mode in DeveloperMode:
                if mode == self.current_mode:
                    self.console.print(f"  [green]▶ {mode.value}[/green] - {self._get_mode_description(mode)}")
                else:
                    self.console.print(f"  [cyan]{mode.value}[/cyan] - {self._get_mode_description(mode)}")
            
            self.console.print("\n[dim]Usage: /mode <mode_name>[/dim]")
            return

        try:
            self.current_mode = DeveloperMode(args.lower())
            self.console.print(f"[green]Switched to {self.current_mode.value} mode[/green]")
            self._show_mode_description()
        except ValueError:
            self.console.print(f"[red]Invalid mode: {args}[/red]")
            self.console.print("Valid modes: " + ", ".join(f"[cyan]{m.value}[/cyan]" for m in DeveloperMode))

    def _get_mode_description(self, mode: DeveloperMode) -> str:
        """Get description for a specific mode."""
        descriptions = {
            DeveloperMode.CODE: "Optimized for writing new code with best practices",
            DeveloperMode.DEBUG: "Focus on error analysis and debugging assistance",
            DeveloperMode.EXPLAIN: "Detailed code explanations and documentation",
            DeveloperMode.REVIEW: "Security and code quality review",
            DeveloperMode.REFACTOR: "Code improvement and optimization suggestions",
        }
        return descriptions.get(mode, "")
    
    def _show_mode_description(self):
        """Show description for current mode."""
        self.console.print(f"[dim]{self._get_mode_description(self.current_mode)}[/dim]")

    def _cmd_session(self, args: str):
        """Manage sessions."""
        if not args:
            self.console.print("\n[bold]Session Management[/bold] [yellow](Coming soon)[/yellow]")
            self.console.print("\n[bold]Planned subcommands:[/bold]")
            self.console.print("  [cyan]save[/cyan] - Save current conversation")
            self.console.print("  [cyan]load[/cyan] - Load a saved conversation")
            self.console.print("  [cyan]list[/cyan] - List all saved sessions")
            self.console.print("  [cyan]branch[/cyan] - Create a branch from current conversation")
            self.console.print("  [cyan]delete[/cyan] - Delete a saved session")
            self.console.print("\n[dim]Usage: /session <subcommand>[/dim]")
        else:
            self.console.print(f"[yellow]Session command '{args}' not implemented yet[/yellow]")

    def _cmd_theme(self, args: str):
        """Change UI theme."""
        if not args:
            self.console.print("\n[bold]Theme Settings[/bold] [yellow](Coming soon)[/yellow]")
            self.console.print("\n[bold]Planned themes:[/bold]")
            self.console.print("  [cyan]default[/cyan] - Default color scheme")
            self.console.print("  [cyan]dark[/cyan] - Dark mode optimized")
            self.console.print("  [cyan]light[/cyan] - Light terminal theme")
            self.console.print("  [cyan]minimal[/cyan] - Minimal colors")
            self.console.print("  [cyan]vibrant[/cyan] - High contrast colors")
            self.console.print("\n[dim]Usage: /theme <theme_name>[/dim]")
        else:
            self.console.print(f"[yellow]Theme '{args}' not implemented yet[/yellow]")

    def _cmd_export(self, args: str):
        """Export conversation."""
        if not args:
            self.console.print("\n[bold]Export Options[/bold] [yellow](Coming soon)[/yellow]")
            self.console.print("\n[bold]Planned formats:[/bold]")
            self.console.print("  [cyan]markdown[/cyan] - Export as Markdown file")
            self.console.print("  [cyan]json[/cyan] - Export as JSON with metadata")
            self.console.print("  [cyan]txt[/cyan] - Export as plain text")
            self.console.print("  [cyan]html[/cyan] - Export as HTML with syntax highlighting")
            self.console.print("\n[dim]Usage: /export <format> [filename][/dim]")
        else:
            self.console.print(f"[yellow]Export format '{args}' not implemented yet[/yellow]")

    def _cmd_tools(self, args: str):
        """Manage MCP tools."""
        if not args:
            self.console.print("\n[bold]MCP Tools Management[/bold] [yellow](Coming soon)[/yellow]")
            self.console.print("\n[bold]Planned subcommands:[/bold]")
            self.console.print("  [cyan]list[/cyan] - List available MCP tools")
            self.console.print("  [cyan]enable[/cyan] - Enable specific tools")
            self.console.print("  [cyan]disable[/cyan] - Disable specific tools")
            self.console.print("  [cyan]config[/cyan] - Configure tool settings")
            self.console.print("  [cyan]status[/cyan] - Show tool status")
            self.console.print("\n[dim]Usage: /tools <subcommand>[/dim]")
        else:
            self.console.print(f"[yellow]Tools command '{args}' not implemented yet[/yellow]")

    def _cmd_clear(self, args: str):
        """Clear conversation."""
        self.console.print("[yellow]Conversation cleared (placeholder)[/yellow]")

    def _cmd_exit(self, args: str):
        """Exit the application."""
        self.console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)
