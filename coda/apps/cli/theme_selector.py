"""Interactive theme selection using prompt-toolkit."""

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
from prompt_toolkit.widgets import TextArea
from rich.console import Console

from coda.base.theme import THEMES


class ThemeSelector:
    """Interactive theme selector with search and navigation."""

    def __init__(self, console: Console = None):
        if console:
            self.console = console
        else:
            from coda.base.theme.compat import get_themed_console

            self.console = get_themed_console()

        # Get all available themes
        self.themes = list(THEMES.items())  # List of (name, theme) tuples
        self.filtered_themes = self.themes
        self.selected_index = 0
        self.search_text = ""
        # Get theme-based style
        from coda.base.theme import ThemeManager
        from prompt_toolkit.styles import Style
        
        theme_mgr = ThemeManager()
        theme_style_dict = theme_mgr.current_theme.prompt.to_dict()
        self.style = Style.from_dict(theme_style_dict)

    def create_theme_list_text(self) -> HTML:
        """Create formatted text for theme list."""
        lines = ["<title>Select a Theme</title>\n"]

        # Add search info
        if self.search_text:
            lines.append(f"<info>Filter: {self.search_text}</info>\n")

        # Add theme list
        for i, (theme_name, theme) in enumerate(self.filtered_themes):
            if i == self.selected_index:
                lines.append(f"<selected>▶ {theme_name}</selected>")
                lines.append(f"<selected>  {theme.description}</selected>")
            else:
                lines.append(f"  {theme_name}")
                lines.append(f"  <dim>{theme.description}</dim>")

        # Add instructions
        lines.append("\n<info>↑/↓ Navigate  Enter: Select  /: Search  Esc: Cancel</info>")

        return HTML("\n".join(lines))

    def filter_themes(self, search_text: str):
        """Filter themes based on search text."""
        if not search_text:
            self.filtered_themes = self.themes
        else:
            self.filtered_themes = [
                (name, theme)
                for name, theme in self.themes
                if search_text.lower() in name.lower()
                or search_text.lower() in theme.description.lower()
            ]

        # Reset selection if out of bounds
        if self.selected_index >= len(self.filtered_themes):
            self.selected_index = max(0, len(self.filtered_themes) - 1)

    async def select_theme_interactive(self) -> str | None:
        """Show interactive theme selector and return selected theme."""
        if not self.themes:
            self.console.print("[yellow]No themes available.[/yellow]")
            return None

        # Create the layout
        search_field = TextArea(
            height=1,
            prompt="Search: ",
            style="class:search-field",
            multiline=False,
            wrap_lines=False,
        )

        theme_list_control = FormattedTextControl(
            text=self.create_theme_list_text,
            style="class:theme-list",
        )

        theme_list_window = Window(
            content=theme_list_control,
            height=min(20, len(self.themes) * 2 + 5),  # Account for descriptions
        )

        layout = Layout(
            HSplit(
                [
                    search_field,
                    theme_list_window,
                ]
            )
        )

        # Key bindings
        kb = KeyBindings()
        selected_theme = None

        @kb.add("up")
        def move_up(event):
            if self.selected_index > 0:
                self.selected_index -= 1

        @kb.add("down")
        def move_down(event):
            if self.selected_index < len(self.filtered_themes) - 1:
                self.selected_index += 1

        @kb.add("enter")
        def select_theme(event):
            nonlocal selected_theme
            if self.filtered_themes:
                selected_theme = self.filtered_themes[self.selected_index][0]
            event.app.exit()

        @kb.add("escape")
        def cancel(event):
            event.app.exit()

        @kb.add("/")
        def start_search(event):
            event.app.layout.focus(search_field)

        # Handle search text changes
        def on_text_changed():
            self.search_text = search_field.text
            self.filter_themes(self.search_text)

        search_field.buffer.on_text_changed += on_text_changed

        # Create application
        app = Application(
            layout=layout,
            key_bindings=kb,
            style=self.style,
            mouse_support=False,
            full_screen=False,
        )

        # Run the application
        try:
            await app.run_async()
            return selected_theme
        except (EOFError, KeyboardInterrupt):
            return None
