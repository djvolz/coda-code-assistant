"""Interactive selector for CLI commands."""

from typing import Any, Callable, Optional

from prompt_toolkit import Application
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import (
    HSplit,
    Layout,
    ScrollablePane,
    Window,
    WindowAlign,
)
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame, Label, TextArea
from rich.console import Console

from coda.services.config import get_config_service


class Selector:
    """Interactive selector for CLI commands with keyboard navigation."""

    def __init__(
        self,
        title: str,
        options: list[tuple[str, str, Optional[dict[str, Any]]]],
        console: Console = None,
        enable_search: bool = False,
        search_prompt: str = "Search: ",
        show_metadata: bool = False,
    ):
        """
        Initialize the unified selector.

        Args:
            title: Title to display
            options: List of (value, description, metadata) tuples
            console: Rich console for output
            enable_search: Whether to show search field
            search_prompt: Prompt text for search field
            show_metadata: Whether to show metadata in the list
        """
        self.title = title
        self.options = options
        self.console = console or Console()
        self.enable_search = enable_search
        self.search_prompt = search_prompt
        self.show_metadata = show_metadata
        
        # State
        self.selected_index = 0
        self.search_text = ""
        self.filtered_options = self.options
        self.selected_value = None
        
        # Get theme from config service
        config_service = get_config_service()
        self.theme = config_service.theme_manager.get_console_theme()
        self.prompt_theme = config_service.theme_manager.current_theme.prompt

    def filter_options(self):
        """Filter options based on search text."""
        if not self.search_text:
            self.filtered_options = self.options
        else:
            search_lower = self.search_text.lower()
            self.filtered_options = [
                opt for opt in self.options
                if search_lower in opt[0].lower() or search_lower in opt[1].lower()
            ]
        
        # Adjust selected index if needed
        if self.selected_index >= len(self.filtered_options):
            self.selected_index = max(0, len(self.filtered_options) - 1)

    def get_formatted_options(self) -> HTML:
        """Get formatted option list with current selection highlighted."""
        lines = []
        
        # Add title
        lines.append(f"<title>{self.title}</title>")
        if self.enable_search and self.search_text:
            lines.append(f"<dim>Filter: {self.search_text}</dim>")
        lines.append("")
        
        # Show options
        if not self.filtered_options:
            lines.append("<dim>[No matching options]</dim>")
        else:
            for i, (value, description, metadata) in enumerate(self.filtered_options):
                is_selected = i == self.selected_index
                
                if is_selected:
                    prefix = "▶ "
                    style = "selected"
                else:
                    prefix = "  "
                    style = "option"
                
                # Format the option line
                option_line = f"{prefix}{value:<15} {description}"
                
                # Add metadata if requested and available
                if self.show_metadata and metadata:
                    meta_str = " ".join(f"[{k}: {v}]" for k, v in metadata.items())
                    option_line += f" <meta>{meta_str}</meta>"
                
                lines.append(f"<{style}>{option_line}</{style}>")
        
        # Add help text
        lines.append("")
        help_parts = ["↑/↓: Navigate", "Enter: Select", "Esc: Cancel"]
        if self.enable_search:
            help_parts.insert(2, "Type to search")
            help_parts.insert(3, "Tab: Toggle focus")
        lines.append(f"<help>{' | '.join(help_parts)}</help>")
        
        return HTML("\n".join(lines))

    def get_status_text(self) -> str:
        """Get status bar text."""
        total = len(self.options)
        shown = len(self.filtered_options)
        if shown < total:
            return f"Showing {shown} of {total}"
        return f"{total} available"

    def create_key_bindings(self, search_field=None, dummy_focus=None) -> KeyBindings:
        """Create key bindings for the selector."""
        kb = KeyBindings()
        
        @kb.add("up", eager=True)
        @kb.add("k", eager=True)
        def move_up(event):
            # Move focus to dummy widget if in search field
            if self.enable_search and search_field and event.app.layout.has_focus(search_field):
                event.app.layout.focus(dummy_focus)
            
            if self.selected_index > 0:
                self.selected_index -= 1
                event.app.invalidate()
        
        @kb.add("down", eager=True)
        @kb.add("j", eager=True)
        def move_down(event):
            # Move focus to dummy widget if in search field
            if self.enable_search and search_field and event.app.layout.has_focus(search_field):
                event.app.layout.focus(dummy_focus)
            
            if self.selected_index < len(self.filtered_options) - 1:
                self.selected_index += 1
                event.app.invalidate()
        
        @kb.add("enter", eager=True)
        def select_option(event):
            if self.filtered_options:
                self.selected_value = self.filtered_options[self.selected_index][0]
                event.app.exit()
        
        @kb.add("c-c")
        def cancel_ctrl_c(event):
            event.app.exit()
            
        @kb.add("escape", eager=True)
        def cancel_or_unfocus(event):
            # If in search field, unfocus it; otherwise exit
            if self.enable_search and search_field and event.app.layout.has_focus(search_field):
                # Move focus to dummy widget
                event.app.layout.focus(dummy_focus)
            else:
                event.app.exit()
        
        # Add search field focus toggle if search is enabled
        if self.enable_search and search_field:
            @kb.add("tab", eager=True)
            def toggle_focus(event):
                # Toggle between search and dummy focus
                if event.app.layout.has_focus(search_field):
                    event.app.layout.focus(dummy_focus)
                else:
                    event.app.layout.focus(search_field)
                    
            @kb.add("/")
            def focus_search(event):
                # Only focus search if not already there
                if not event.app.layout.has_focus(search_field):
                    event.app.layout.focus(search_field)
        
        return kb

    async def select_interactive(self) -> Optional[str]:
        """Show interactive selector and return selected value."""
        # Create layout components
        if self.enable_search:
            # Create search field
            search_field = TextArea(
                height=1,
                prompt=self.search_prompt,
                multiline=False,
                wrap_lines=False,
            )
            
            def on_search_change(buf):
                self.search_text = search_field.text
                self.filter_options()
                app.invalidate()
            
            search_field.buffer.on_text_changed += on_search_change
        else:
            search_field = None
        
        # Create the main content window
        content_window = Window(
            content=FormattedTextControl(
                text=lambda: self.get_formatted_options()
            ),
            wrap_lines=False,
        )
        
        # Create status window
        status_window = Window(
            content=FormattedTextControl(
                text=lambda: self.get_status_text()
            ),
            height=1,
            align=WindowAlign.RIGHT,
        )
        
        # Build layout
        dummy_focus = None  # Initialize for later reference
        
        if self.enable_search:
            # Create a dummy focusable widget to handle arrow key navigation
            # This is a 1-height invisible widget that captures focus for arrow keys
            dummy_focus = TextArea(
                height=1,
                focusable=True,
                multiline=False,
                style="hidden",  # Will be styled as invisible
            )
            
            layout_parts = [
                Label(text=self.title),
                search_field,
                Frame(ScrollablePane(content_window), title="Options"),
                dummy_focus,  # Place after content for better focus flow
                status_window,
            ]
        else:
            # For non-search selectors, create content directly
            layout_parts = [
                content_window,
                status_window,
            ]
        
        layout = Layout(HSplit(layout_parts))
        
        # Create style from theme
        style_dict = {
            "title": f"{self.theme.info} bold",
            "option": self.theme.dim if self.theme.dim == "dim" else f"fg:{self.theme.dim}",
            "selected": f"{self.theme.success} bold",
            "help": "gray",
            "meta": "italic gray",
            "dim": "gray",
            "hidden": "bg:default fg:default",  # Invisible style
        }
        
        # Handle the dim style properly
        if self.theme.dim.startswith('#'):
            style_dict["option"] = self.theme.dim
        elif self.theme.dim == "dim":
            style_dict["option"] = "gray"
        
        style = Style.from_dict(style_dict)
        
        # Create key bindings - pass dummy_focus if search is enabled
        if self.enable_search:
            kb = self.create_key_bindings(search_field, dummy_focus)
        else:
            kb = self.create_key_bindings()
        
        # Create application
        app = Application(
            layout=layout,
            key_bindings=kb,
            style=style,
            full_screen=False,
            mouse_support=True,
        )
        
        # Run and get result
        await app.run_async()
        
        return self.selected_value


# Convenience subclasses for specific use cases
# Note: ModelSelector and ThemeSelector have been moved to completion_selector.py
# for better search functionality using prompt_toolkit's completion system


class SimpleSelector(Selector):
    """Simple selector without search for basic options."""
    
    def __init__(self, title: str, options: list[tuple[str, str]], console: Console = None):
        # Convert simple format to full format
        full_options = [(opt[0], opt[1], None) for opt in options]
        
        super().__init__(
            title=title,
            options=full_options,
            console=console,
            enable_search=False,
            show_metadata=False,
        )


# Legacy compatibility classes that redirect to SimpleSelector

class ModeSelector(SimpleSelector):
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


class ExportSelector(SimpleSelector):
    """Selector for export formats."""
    
    def __init__(self, console: Console = None):
        options = [
            ("json", "Export as JSON format"),
            ("markdown", "Export as Markdown (human-readable)"),
            ("txt", "Export as plain text"),
            ("html", "Export as HTML with syntax highlighting"),
        ]
        super().__init__("Select Export Format", options, console)


class SessionCommandSelector(SimpleSelector):
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