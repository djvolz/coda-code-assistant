"""Model selection UI for interactive CLI."""

import asyncio
# Removed unused import: from functools import partial

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    ConditionalContainer,
    HSplit,
    Layout,
    ScrollablePane,
    Window,
    WindowAlign,
)
from prompt_toolkit.widgets import Frame, Label, TextArea
from rich.console import Console

from coda.base.providers import Model
from coda.base.theme import ThemeManager



class ModelSelector:
    """Interactive model selector for CLI."""

    def __init__(self, models: list[Model], console: Console | None = None):
        self.models = models
        self.selected_index = 0
        self.search_text = ""
        self.console = console or Console()
        self.theme_manager = ThemeManager()
        self.theme = self.theme_manager.current_theme
        self.filtered_models = self.models

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

        # Adjust selected index if needed
        if self.selected_index >= len(self.filtered_models):
            self.selected_index = max(0, len(self.filtered_models) - 1)

    def get_model_list_text(self) -> str:
        """Get formatted model list for display."""
        if not self.filtered_models:
            return "[No matching models]"

        lines = []
        for i, model in enumerate(self.filtered_models):
            # Determine selection indicator
            if i == self.selected_index:
                prefix = "▶ "
                style = "fg:cyan bold"  # Use a fixed color for now
            else:
                prefix = "  "
                style = ""

            # Format model info
            model_text = f"{prefix}{model.id} ({model.provider})"
            lines.append(model_text)

        return "\n".join(lines)

    def get_status_text(self) -> str:
        """Get status bar text."""
        total = len(self.models)
        shown = len(self.filtered_models)
        if shown < total:
            return f"Showing {shown} of {total} models"
        return f"{total} models available"

    async def select_model_interactive(self) -> str:
        """Interactive model selection using prompt-toolkit."""
        # Create key bindings
        kb = KeyBindings()

        @kb.add("c-c")
        @kb.add("escape")
        def exit_app(event):
            """Exit without selecting."""
            event.app.exit(result=None)

        @kb.add("enter")
        def select_model(event):
            """Select current model."""
            if self.filtered_models:
                event.app.exit(result=self.filtered_models[self.selected_index].id)

        @kb.add("up")
        @kb.add("c-p")
        def move_up(event):
            """Move selection up."""
            if self.selected_index > 0:
                self.selected_index -= 1
                event.app.invalidate()

        @kb.add("down")
        @kb.add("c-n")
        def move_down(event):
            """Move selection down."""
            if self.selected_index < len(self.filtered_models) - 1:
                self.selected_index += 1
                event.app.invalidate()

        # Create search field
        search_field = TextArea(
            height=1,
            prompt="Search: ",  # Use plain text for prompt
            multiline=False,
            focus_on_click=True,
        )

        def on_search_change(buf):
            """Handle search text changes."""
            self.search_text = search_field.text
            self.filter_models()
            app.invalidate()

        search_field.buffer.on_text_changed += on_search_change

        # Create layout
        # Import FormattedTextControl
        from prompt_toolkit.layout.controls import FormattedTextControl
        
        # Use FormattedTextControl with a callable
        model_list_window = Window(
            content=FormattedTextControl(
                text=lambda: HTML(self.get_model_list_text())
            ),
            wrap_lines=False,
        )

        # Use FormattedTextControl for status window too
        status_window = Window(
            content=FormattedTextControl(
                text=lambda: self.get_status_text()  # Plain text for status
            ),
            height=1,
            align=WindowAlign.RIGHT,
        )

        layout = Layout(
            HSplit(
                [
                    Label(text="Select Model"),
                    search_field,
                    Frame(ScrollablePane(model_list_window), title="Available Models"),
                    status_window,
                ]
            )
        )

        # Create application with theme style
        from prompt_toolkit.styles import Style
        
        # Get theme style from prompt theme
        theme_style_dict = self.theme.prompt.to_dict()
        style = Style.from_dict(theme_style_dict)
        
        app = Application(
            layout=layout, 
            key_bindings=kb, 
            style=style,
            full_screen=False, 
            mouse_support=True
        )

        # Run and get result
        selected_model = await app.run_async()
        return selected_model