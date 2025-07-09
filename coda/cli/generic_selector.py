"""Generic selector for CLI commands with options."""


from prompt_toolkit import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    Layout,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from rich.console import Console

from ..themes import get_console_theme


class GenericSelector:
    """Generic interactive selector for commands with options."""

    def __init__(self, title: str, options: list[tuple[str, str]], console: Console = None):
        """
        Initialize the selector.

        Args:
            title: Title to display (e.g., "Export Format", "Session Command")
            options: List of (value, description) tuples
            console: Rich console for output
        """
        self.title = title
        self.options = options
        self.console = console or Console()
        self.current_index = 0
        self.selected_option = None

        # Get theme colors
        self.theme = get_console_theme()

    def create_bindings(self) -> KeyBindings:
        """Create key bindings for the selector."""
        kb = KeyBindings()

        @kb.add("up", "k")
        def move_up(event):
            self.current_index = (self.current_index - 1) % len(self.options)

        @kb.add("down", "j")
        def move_down(event):
            self.current_index = (self.current_index + 1) % len(self.options)

        @kb.add("enter")
        def select_option(event):
            self.selected_option = self.options[self.current_index][0]
            event.app.exit()

        @kb.add("c-c", "escape", "q")
        def cancel(event):
            event.app.exit()

        @kb.add("?", "h")
        def show_help(event):
            # Toggle help display
            self.show_help = not self.show_help

        return kb

    def get_formatted_options(self) -> list:
        """Get formatted option list with current selection highlighted."""
        lines = []

        # Add title
        lines.append(("class:title", f"\n{self.title}\n"))

        for i, (value, description) in enumerate(self.options):
            if i == self.current_index:
                # Highlighted option
                prefix = "▶ "
                style = "class:selected"
            else:
                prefix = "  "
                style = "class:option"

            # Format as "value - description"
            lines.append((style, f"{prefix}{value:<15} {description}\n"))

        # Add help text
        lines.append(("class:help", "\n[↑/↓ or j/k: Navigate] [Enter: Select] [Esc/q: Cancel]"))

        return lines

    async def select_option_interactive(self) -> str | None:
        """Show interactive option selector and return selected value."""
        self.show_help = False

        # Create the layout
        content = Window(
            content=FormattedTextControl(
                text=lambda: self.get_formatted_options(),
                focusable=False,
            ),
            align=WindowAlign.LEFT,
        )

        layout = Layout(content)

        # Define custom style based on theme
        style = {
            "title": f"{self.theme.info} bold",
            "option": self.theme.dim,
            "selected": f"{self.theme.success} bold",
            "help": self.theme.dim,
        }

        # Create application
        app = Application(
            layout=layout,
            key_bindings=self.create_bindings(),
            style=style,
            mouse_support=False,
            full_screen=False,
        )

        # Run the selector
        await app.run_async()

        return self.selected_option


class ExportSelector(GenericSelector):
    """Selector specifically for export formats."""

    def __init__(self, console: Console = None):
        options = [
            ("json", "Export as JSON format"),
            ("markdown", "Export as Markdown (human-readable)"),
            ("txt", "Export as plain text"),
            ("html", "Export as HTML with syntax highlighting"),
        ]
        super().__init__("Select Export Format", options, console)


class SessionCommandSelector(GenericSelector):
    """Selector for session commands."""

    def __init__(self, console: Console = None):
        options = [
            ("save", "Save current conversation"),
            ("load", "Load a saved conversation"),
            ("list", "List all saved sessions"),
            ("delete", "Delete a saved session"),
            ("branch", "Create a branch from current conversation"),
            ("rename", "Rename a session"),
            ("info", "Show session details"),
            ("search", "Search sessions by content"),
        ]
        super().__init__("Select Session Command", options, console)


class ModeSelector(GenericSelector):
    """Selector for developer modes."""

    def __init__(self, console: Console = None):
        options = [
            ("general", "General conversational mode"),
            ("code", "Code writing mode"),
            ("debug", "Debugging mode"),
            ("explain", "Code explanation mode"),
            ("review", "Code review mode"),
            ("refactor", "Code refactoring mode"),
            ("plan", "Planning mode"),
        ]
        super().__init__("Select Developer Mode", options, console)


