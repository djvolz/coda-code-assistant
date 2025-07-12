"""Completion-based selector using prompt_toolkit's built-in functionality."""

from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.application import get_app
from prompt_toolkit.completion import Completer, Completion, FuzzyCompleter
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.styles import Style
from rich.console import Console

from coda.services.config import get_config_service


class OptionCompleter(Completer):
    """Custom completer for option selection."""

    def __init__(self, options: list[tuple[str, str, dict[str, Any] | None]]):
        """
        Initialize with options.

        Args:
            options: List of (value, description, metadata) tuples
        """
        self.options = options

    def get_completions(self, document, complete_event):
        """Get completions based on current input."""
        word = document.text_before_cursor.lower()

        for value, description, metadata in self.options:
            # Match if search text is in value or description
            if not word or word in value.lower() or word in description.lower():
                # Format display with metadata if available
                display = f"{value:<15} {description}"
                if metadata:
                    meta_str = " ".join(f"[{k}: {v}]" for k, v in metadata.items())
                    display += f" {meta_str}"

                yield Completion(
                    value,
                    start_position=-len(document.text_before_cursor),
                    display=HTML(display),
                    display_meta=description,
                )


class CompletionSelector:
    """Selector using prompt_toolkit's completion system."""

    def __init__(
        self,
        title: str,
        options: list[tuple[str, str, dict[str, Any] | None]],
        console: Console = None,
        prompt_text: str = "> ",
        instruction_text: str = None,
    ):
        """
        Initialize the completion-based selector.

        Args:
            title: Title to display
            options: List of (value, description, metadata) tuples
            console: Rich console for output
            prompt_text: Prompt to show
            instruction_text: Optional instruction text
        """
        self.title = title
        self.options = options
        self.console = console or Console()
        self.prompt_text = prompt_text
        self.instruction_text = (
            instruction_text or "Select an option (arrow keys to navigate, Enter to select)"
        )

        # Get theme from config service
        config_service = get_config_service()
        self.theme_manager = config_service.theme_manager
        self.console_theme = self.theme_manager.get_console_theme()
        self.prompt_theme = self.theme_manager.current_theme.prompt

    def create_prompt_session(self) -> PromptSession:
        """Create a configured prompt session."""
        # Create completer with fuzzy matching
        base_completer = OptionCompleter(self.options)
        completer = FuzzyCompleter(base_completer, enable_fuzzy=True)

        # Get the prompt theme style dictionary
        prompt_styles = self.prompt_theme.to_dict()

        # Build style dict using theme values
        style_dict = {
            # Use theme's prompt style
            "prompt": prompt_styles.get("prompt", "bold"),
            # Use theme's completion styles
            "completion-menu.completion": prompt_styles.get("completion", ""),
            "completion-menu.completion.current": prompt_styles.get(
                "completion.current", f"bg:{self.console_theme.success} fg:black"
            ),
            "completion-menu.meta.completion": prompt_styles.get("completion.meta", "italic"),
            "completion-menu.meta.completion.current": prompt_styles.get(
                "completion.meta", "italic"
            )
            + " "
            + prompt_styles.get("completion.current", ""),
            # Additional styles
            "scrollbar.background": prompt_styles.get("toolbar", "bg:#444444"),
            "scrollbar.button": f"fg:{self.console_theme.info}",
        }

        style = Style.from_dict(style_dict)

        # Create prompt session with completion
        return PromptSession(
            completer=completer,
            complete_while_typing=True,
            style=style,
            mouse_support=True,
            complete_style="MULTI_COLUMN",  # or 'COLUMN' for single column
        )

    async def select_interactive(self, auto_complete: bool = True) -> str | None:
        """Show interactive selector and return selected value.

        Args:
            auto_complete: If True, automatically show completions on start
        """
        # Display title and instructions using theme colors
        self.console.print(
            f"\n[{self.console_theme.panel_title}]{self.title}[/{self.console_theme.panel_title}]"
        )
        self.console.print(
            f"[{self.console_theme.dim}]{self.instruction_text}[/{self.console_theme.dim}]\n"
        )

        # Create prompt session
        session = self.create_prompt_session()

        try:
            # Custom pre_run to trigger completions
            def trigger_completions():
                """Trigger completion menu on startup."""
                if auto_complete:
                    app = get_app()
                    if app and app.current_buffer:
                        app.current_buffer.start_completion(select_first=False)

            # Get user input
            result = await session.prompt_async(
                self.prompt_text, pre_run=trigger_completions if auto_complete else None
            )

            # Validate the result is one of our options
            valid_values = [opt[0] for opt in self.options]
            if result in valid_values:
                return result
            else:
                # Try to find a matching option
                result_lower = result.lower()
                for value, _description, _ in self.options:
                    if result_lower == value.lower():
                        return value

                # No exact match found
                self.console.print(
                    f"[{self.console_theme.error}]Invalid selection: {result}[/{self.console_theme.error}]"
                )
                return None

        except (EOFError, KeyboardInterrupt):
            # User cancelled
            return None


# Convenience subclasses


class CompletionModelSelector(CompletionSelector):
    """Model selector using completions."""

    def __init__(self, models: list, console: Console = None):
        # Convert Model objects to options format
        options = []
        for model in models:
            metadata = {
                "provider": model.provider,
            }
            if hasattr(model, "metadata") and model.metadata:
                if "context_window" in model.metadata:
                    metadata["context"] = f"{model.metadata['context_window']:,}"
                if "capabilities" in model.metadata:
                    caps = model.metadata["capabilities"]
                    if isinstance(caps, list):
                        metadata["caps"] = ",".join(caps[:2])

            options.append((model.id, model.provider, metadata))

        super().__init__(
            title="Select Model",
            options=options,
            console=console,
            instruction_text="Select a model (type to filter, arrow keys to navigate)",
        )


class CompletionThemeSelector(CompletionSelector):
    """Theme selector using completions."""

    def __init__(self, console: Console = None):
        from coda.base.theme import THEMES

        options = [
            (name, theme.description, {"dark": "✓" if theme.is_dark else "✗"})
            for name, theme in THEMES.items()
        ]

        super().__init__(
            title="Select Theme",
            options=options,
            console=console,
            instruction_text="Select a theme (type to filter, arrow keys to navigate)",
        )
