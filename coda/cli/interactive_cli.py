"""Interactive CLI with prompt-toolkit for enhanced user experience."""

import asyncio
from collections.abc import Callable
from threading import Event

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from rich.console import Console

from coda.session import SessionCommands

from ..constants import (
    HISTORY_FILE_PATH,
)
from .completers import EnhancedCompleter
from .shared import CommandHandler, CommandResult, DeveloperMode


class SlashCommand:
    """Represents a slash command with its handler and help text."""

    def __init__(self, name: str, handler: Callable, help_text: str, aliases: list[str] = None):
        self.name = name
        self.handler = handler
        self.help_text = help_text
        self.aliases = aliases or []
        self._autocomplete_options = None

    def get_autocomplete_options(self) -> list[str]:
        """Get autocomplete options for this command."""
        if self._autocomplete_options is None:
            # Load options from command registry
            from coda.cli.command_registry import CommandRegistry

            options = CommandRegistry.get_autocomplete_options()
            self._autocomplete_options = [opt[0] for opt in options.get(self.name, [])]
        return self._autocomplete_options


class InteractiveCLI(CommandHandler):
    """Interactive CLI with advanced prompt features using prompt-toolkit."""

    def __init__(self, console: Console = None):
        if console:
            super().__init__(console)
        else:
            from ..themes import get_themed_console

            super().__init__(get_themed_console())
        self.session = None
        self.config = None  # Will be set by interactive.py
        self.commands = self._init_commands()
        self.style = self._create_style()

        # For interrupt handling
        self.interrupt_event = Event()
        self.last_escape_time = 0
        self.escape_count = 0
        self.last_ctrl_c_time = 0
        self.ctrl_c_count = 0

        # Initialize session management
        self.session_commands = SessionCommands()

        # Track terminal dimensions
        self._last_terminal_width = None

        # Initialize session with all features
        self._init_session()

    def _get_current_provider(self):
        """Get current provider for model completion."""
        if hasattr(self, "config") and self.config:
            return self.config.get_provider()
        return None

    def _get_available_themes(self):
        """Get available theme names."""
        from coda.themes import THEMES

        return THEMES

    def _get_available_models(self):
        """Get available model names from current provider."""
        provider = self._get_current_provider()
        if not provider:
            return []
        try:
            return provider.list_models()
        except Exception:
            return []

    def _init_commands(self) -> dict[str, SlashCommand]:
        """Initialize slash commands from the command registry."""
        from coda.cli.command_registry import CommandRegistry

        # Map command names to their handlers
        handler_map = {
            "help": self._cmd_help,
            "model": self._cmd_model,
            "provider": self._cmd_provider,
            "mode": self._cmd_mode,
            "session": self._cmd_session,
            "export": self._cmd_export,
            "theme": self._cmd_theme,
            "clear": self._cmd_clear,
            "exit": self._cmd_exit,
        }

        # Add handlers for commands not yet implemented
        placeholder_handlers = {
            "tools": self._cmd_tools,
        }
        handler_map.update(placeholder_handlers)

        commands = {}
        for cmd_def in CommandRegistry.COMMANDS:
            if cmd_def.name in handler_map:
                commands[cmd_def.name] = SlashCommand(
                    name=cmd_def.name,
                    handler=handler_map[cmd_def.name],
                    help_text=cmd_def.description,
                    aliases=cmd_def.aliases,
                )

        return commands

    def _create_style(self) -> Style:
        """Create custom style for the prompt."""
        # Get theme-based style and extend it with additional styles
        from coda.themes import get_theme_manager

        theme_manager = get_theme_manager()
        theme_style = theme_manager.current_theme.prompt.to_prompt_toolkit_style()

        # Get the base style dictionary and add custom styles
        combined_styles = {}

        # Add theme styles (if they have a style_dict attribute)
        if hasattr(theme_style, "style_dict"):
            combined_styles.update(theme_style.style_dict)

        # Add custom additions
        combined_styles.update(
            {
                # Additional prompt-specific styles
                "prompt.mode": "#888888",
                # Completion menu enhancements
                "completion-menu": "bg:#2c2c2c #ffffff",
                "completion-menu.completion": "bg:#2c2c2c #ffffff",
                "completion-menu.completion.current": "bg:#005588 #ffffff bold",
                "completion-menu.meta.completion": "bg:#2c2c2c #888888",
                "completion-menu.meta.completion.current": "bg:#005588 #aaaaaa",
                # Scrollbar
                "scrollbar.background": "bg:#2c2c2c",
                "scrollbar.button": "bg:#888888",
            }
        )

        return Style.from_dict(combined_styles)

    def _init_session(self):
        """Initialize the prompt session with all features."""
        # Create history directory if it doesn't exist
        HISTORY_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

        # Create key bindings
        kb = KeyBindings()

        # Note: We handle interrupts via signal handler during AI responses
        # Double escape is not reliable with prompt-toolkit during streaming

        # Create enhanced completer with all features
        completer = EnhancedCompleter(
            slash_commands=self.commands,
            get_provider_func=self._get_current_provider,
            session_commands=self.session_commands,
            get_themes_func=self._get_available_themes,
        )

        self.session = PromptSession(
            history=FileHistory(str(HISTORY_FILE_PATH)),
            auto_suggest=None,  # Disable auto-suggestions from history
            completer=completer,
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

    def _get_mode_panel_config(self) -> dict:
        """Get mode-specific panel configuration with title and styling."""
        mode_configs = {
            DeveloperMode.GENERAL: {
                "title": "💬 General Chat",
                "border_style": "white",
                "title_style": "bold white",
            },
            DeveloperMode.CODE: {
                "title": "⚡ Code Mode",
                "border_style": "green",
                "title_style": "bold green",
            },
            DeveloperMode.DEBUG: {
                "title": "🔍 Debug Mode",
                "border_style": "yellow",
                "title_style": "bold yellow",
            },
            DeveloperMode.EXPLAIN: {
                "title": "📚 Explain Mode",
                "border_style": "blue",
                "title_style": "bold blue",
            },
            DeveloperMode.REVIEW: {
                "title": "🔎 Review Mode",
                "border_style": "magenta",
                "title_style": "bold magenta",
            },
            DeveloperMode.REFACTOR: {
                "title": "🔄 Refactor Mode",
                "border_style": "cyan",
                "title_style": "bold cyan",
            },
            DeveloperMode.PLAN: {
                "title": "📋 Plan Mode",
                "border_style": "red",
                "title_style": "bold red",
            },
        }
        return mode_configs.get(self.current_mode, mode_configs[DeveloperMode.GENERAL])

    def _get_safe_terminal_width(self) -> int:
        """Get terminal width with minimum constraint to prevent squashing."""
        min_width = 40  # Minimum width to prevent ugly squashing
        max_width = 60  # Reduced max width for cleaner look

        try:
            width = self.console.size.width
            # Clamp between min and max
            return max(min_width, min(width, max_width))
        except Exception:
            # Fallback if console size detection fails
            return 60

    def _render_input_separator(self) -> None:
        """Render just the mode title without separator lines."""
        config = self._get_mode_panel_config()

        # Just print the mode title without any lines
        title = config["title"]

        # Print the title with mode-specific color
        self.console.print(f"[{config['title_style']}]{title}[/{config['title_style']}]")

    def _render_bottom_separator(self) -> None:
        """Render a minimal bottom separator line after input."""
        config = self._get_mode_panel_config()

        # Just print a simple, short separator line
        # This provides a subtle visual break without being too prominent
        separator = "─" * 30  # Fixed 30 character width, left-aligned

        # Left-align the separator (no padding)
        self.console.print(f"[{config['border_style']}]{separator}[/{config['border_style']}]")

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

        # Simple colored prompt arrow
        return HTML(f"<ansi{mode_color}>❯</ansi{mode_color}> ")

    async def get_input(self, multiline: bool = False) -> str:
        """Get input from user with rich features."""
        # Render top separator with mode title
        self._render_input_separator()

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

            # Render bottom separator
            self._render_bottom_separator()

            return text.strip()
        except EOFError:
            # Still render bottom separator on EOF
            self._render_bottom_separator()
            return "/exit"
        except KeyboardInterrupt:
            # Handle Ctrl+C gracefully
            # Still render bottom separator
            self._render_bottom_separator()
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

    async def _cmd_mode(self, args: str):
        """Change developer mode."""
        if not args:
            # Show interactive mode selector
            from .generic_selector import ModeSelector
            
            selector = ModeSelector(self.console)
            mode_choice = await selector.select_option_interactive()
            
            if mode_choice:
                self.switch_mode(mode_choice)
            else:
                # Show current mode if cancelled
                self.console.print(f"[yellow]Current mode: {self.current_mode.value}[/yellow]")
        else:
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

    async def _cmd_session(self, args: str):
        """Manage sessions."""
        if not args:
            # Show interactive session command selector
            from .generic_selector import SessionCommandSelector
            
            selector = SessionCommandSelector(self.console)
            cmd_choice = await selector.select_option_interactive()
            
            if cmd_choice:
                # Execute selected command
                result = self.session_commands.handle_session_command([cmd_choice])
                if result:
                    self.console.print(result)
            else:
                # Show available commands if cancelled
                self.console.print("[yellow]Session command cancelled[/yellow]")
        else:
            # Pass the arguments to session commands handler
            result = self.session_commands.handle_session_command(args.split() if args else [])
            if result:
                self.console.print(result)

    async def _cmd_theme(self, args: str):
        """Change UI theme."""
        from ..configuration import save_config
        from ..themes import THEMES, get_theme_manager

        theme_manager = get_theme_manager()

        if not args:
            # Show interactive theme selector
            from .theme_selector import ThemeSelector

            selector = ThemeSelector(self.console)
            new_theme = await selector.select_theme_interactive()

            if new_theme:
                # Set the theme using the same logic as when args are provided
                try:
                    # Update theme manager
                    theme_manager.set_theme(new_theme)

                    # Update configuration and save
                    if self.config:
                        self.config.ui["theme"] = new_theme
                        save_config()

                    # Update console theme
                    from ..themes import get_themed_console

                    new_console = get_themed_console()
                    self.console = new_console

                    # Recreate the prompt style with new theme
                    self.style = self._create_style()

                    # Update the prompt session style
                    if hasattr(self, "session") and self.session:
                        self.session.style = self.style

                    self.console.print(f"[green]✓[/] Theme changed to '[cyan]{new_theme}[/]'")
                    if self.config:
                        self.console.print("[dim]Theme preference saved to configuration[/]")

                except ValueError as e:
                    self.console.print(f"[red]Error:[/] {e}")
            else:
                # Show current theme if no selection was made
                self.console.print(
                    f"\n[yellow]Current theme:[/] {theme_manager.current_theme_name}"
                )
            return

        # Handle subcommands
        if args == "list":
            self.console.print("\n[bold]Available themes:[/]")
            for theme_name, theme in THEMES.items():
                status = (
                    "[green]●[/]" if theme_name == theme_manager.current_theme_name else "[dim]○[/]"
                )
                self.console.print(f"  {status} [cyan]{theme_name}[/] - {theme.description}")
            return

        elif args == "current":
            self.console.print(f"\n[bold]Current theme:[/] {theme_manager.current_theme_name}")
            self.console.print(f"[bold]Description:[/] {theme_manager.current_theme.description}")
            return

        elif args == "reset":
            # Reset to default theme
            from ..constants import THEME_DEFAULT

            args = THEME_DEFAULT

        # Set the theme
        try:
            # Update theme manager
            theme_manager.set_theme(args)

            # Update configuration and save
            if self.config:
                self.config.ui["theme"] = args
                save_config()

            # Update console theme
            from ..themes import get_themed_console

            new_console = get_themed_console()
            self.console = new_console

            # Recreate the prompt style with new theme
            self.style = self._create_style()

            # Update the prompt session style
            if hasattr(self, "session") and self.session:
                self.session.style = self.style

            self.console.print(f"[green]✓[/] Theme changed to '[cyan]{args}[/]'")
            if self.config:
                self.console.print("[dim]Theme preference saved to configuration[/]")

        except ValueError as e:
            self.console.print(f"[red]Error:[/] {e}")

    async def _cmd_export(self, args: str):
        """Export conversation."""
        if not args:
            # Show interactive export format selector
            from .generic_selector import ExportSelector
            
            selector = ExportSelector(self.console)
            format_choice = await selector.select_option_interactive()
            
            if format_choice:
                # Export with selected format
                result = self.session_commands.handle_export_command([format_choice])
                if result:
                    self.console.print(result)
            else:
                self.console.print("[yellow]Export cancelled[/yellow]")
        else:
            # Pass the arguments to session commands handler for export
            result = self.session_commands.handle_export_command(args.split() if args else [])
            if result:
                self.console.print(result)

    def _cmd_tools(self, args: str):
        """Manage MCP tools."""
        # Use the shared command handler
        result = self.handle_tools_command(args)
        return result

    def _cmd_clear(self, args: str):
        """Clear conversation."""
        # Clear session manager's conversation
        self.session_commands.clear_conversation()
        self.console.print("[green]Conversation cleared[/green]")
        # Note: Actual clearing is handled by the caller

    def _cmd_exit(self, args: str):
        """Exit the application."""
        self.console.print("[dim]Goodbye![/dim]")
        raise SystemExit(0)

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
