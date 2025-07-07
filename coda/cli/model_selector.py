"""Interactive model selection using prompt-toolkit."""

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import FormattedTextControl, HSplit, Layout, Window
from prompt_toolkit.widgets import TextArea
from rich.console import Console

from ..constants import (
    CONSOLE_STYLE_ERROR,
    MAX_MODELS_BASIC_DISPLAY,
    MAX_MODELS_DISPLAY,
)
from ..themes import get_prompt_style


class ModelSelector:
    """Interactive model selector with search and navigation."""

    def __init__(self, models: list, console: Console = None):
        self.models = models
        if console:
            self.console = console
        else:
            from ..themes import get_themed_console
            self.console = get_themed_console()
        self.filtered_models = models
        self.selected_index = 0
        self.search_text = ""
        # Use theme-based style
        self.style = get_prompt_style()

    def create_model_list_text(self) -> HTML:
        """Create formatted text for model list."""
        lines = ["<title>Select a Model</title>\n"]

        # Add search info
        if self.search_text:
            lines.append(f"<info>Filter: {self.search_text}</info>\n")

        # Add model list
        for i, model in enumerate(self.filtered_models[:20]):  # Show max 20
            if i == self.selected_index:
                lines.append(f"<selected>▶ {model.id} ({model.provider})</selected>")
            else:
                lines.append(f"  {model.id} <provider>({model.provider})</provider>")

        if len(self.filtered_models) > MAX_MODELS_DISPLAY:
            lines.append(f"\n<info>... and {len(self.filtered_models) - MAX_MODELS_DISPLAY} more</info>")

        # Add help text
        lines.append("\n<info>↑/↓: Navigate  Enter: Select  /: Search  Esc: Cancel</info>")

        return HTML("\n".join(lines))

    def filter_models(self):
        """Filter models based on search text."""
        if not self.search_text:
            self.filtered_models = self.models
        else:
            search_lower = self.search_text.lower()
            self.filtered_models = [
                m
                for m in self.models
                if search_lower in m.id.lower() or search_lower in m.provider.lower()
            ]
        self.selected_index = 0

    async def select_model_interactive(self) -> str | None:
        """Show interactive model selection and return selected model ID."""
        selected_model = None

        # Key bindings
        kb = KeyBindings()

        @kb.add("up")
        def _up(event):
            if self.selected_index > 0:
                self.selected_index -= 1
                event.app.invalidate()

        @kb.add("down")
        def _down(event):
            if self.selected_index < min(len(self.filtered_models) - 1, 19):
                self.selected_index += 1
                event.app.invalidate()

        @kb.add("enter")
        def _select(event):
            nonlocal selected_model
            if self.filtered_models:
                selected_model = self.filtered_models[self.selected_index].id
            event.app.exit()

        @kb.add("escape")
        @kb.add("c-c")
        def _cancel(event):
            event.app.exit()

        @kb.add("/")
        def _search(event):
            # Start search mode
            self.search_text = ""
            self.filter_models()
            event.app.layout.focus(search_field)

        # Search field
        search_field = TextArea(
            height=1,
            prompt="Search: ",
            style="class:search",
            multiline=False,
            wrap_lines=False,
        )

        def on_search_change():
            self.search_text = search_field.text
            self.filter_models()

        search_field.buffer.on_text_changed += lambda _: on_search_change()

        # Layout
        model_list = Window(
            FormattedTextControl(
                lambda: self.create_model_list_text(),
                focusable=True,
            ),
            height=25,
        )

        layout = Layout(
            HSplit(
                [
                    model_list,
                    search_field,
                ]
            ),
            focused_element=model_list,
        )

        # Create and run application
        app = Application(
            layout=layout,
            key_bindings=kb,
            style=self.style,
            mouse_support=True,
            full_screen=False,
        )

        await app.run_async()
        return selected_model

    def select_model_basic(self) -> str:
        """Basic model selection for non-interactive mode."""
        self.console.print("\n[bold]Available models:[/bold]")
        for i, m in enumerate(self.models[:MAX_MODELS_BASIC_DISPLAY], 1):
            self.console.print(f"{i:2d}. {m.id} ({m.provider})")

        if len(self.models) > MAX_MODELS_BASIC_DISPLAY:
            self.console.print(f"    ... and {len(self.models) - MAX_MODELS_BASIC_DISPLAY} more")

        while True:
            try:
                choice = self.console.input("\nSelect model number [1]: ") or "1"
                index = int(choice) - 1
                if 0 <= index < len(self.models):
                    return self.models[index].id
                else:
                    self.console.print(f"{CONSOLE_STYLE_ERROR}Invalid selection. Please try again.[/]")
            except ValueError:
                self.console.print(f"{CONSOLE_STYLE_ERROR}Please enter a number.[/]")
            except KeyboardInterrupt:
                raise SystemExit(0) from None
