"""Data models for theme module.

This module contains theme-related data structures.
Zero dependencies - uses only Python standard library.
"""

from dataclasses import dataclass, field


@dataclass
class ConsoleTheme:
    """Theme configuration for terminal/console output.

    This defines colors and styles for various UI elements when
    outputting to the terminal.
    """

    # Basic styles
    success: str = "green"
    error: str = "red"
    warning: str = "yellow"
    info: str = "cyan"
    dim: str = "dim"
    bold: str = "bold"

    # Panel and borders
    panel_border: str = "cyan"
    panel_title: str = "bold cyan"

    # Message roles (for chat-like interfaces)
    user_message: str = "bright_blue"
    assistant_message: str = "bright_green"
    system_message: str = "yellow"

    # Code and syntax
    code_theme: str = "monokai"

    # Tables
    table_header: str = "bold cyan"
    table_row_odd: str = ""
    table_row_even: str = "dim"

    # Commands and help
    command: str = "cyan"
    command_description: str = ""

    def to_style_dict(self) -> dict[str, str]:
        """Convert theme to style dictionary for terminal libraries."""
        return {
            "success": self.success,
            "error": self.error,
            "warning": self.warning,
            "info": self.info,
            "dim": self.dim,
            "bold": self.bold,
        }


@dataclass
class PromptTheme:
    """Theme configuration for interactive prompts and inputs.

    This defines styles for input fields, completions, search,
    and other interactive UI elements.
    """

    # Editor and input
    input_field: str = ""
    cursor: str = "reverse"
    selection: str = "bg:#444444 #ffffff"

    # Completions and menus
    completion: str = "bg:#008888 #ffffff"
    completion_selected: str = "bg:#00aaaa #000000"
    completion_meta: str = "bg:#444444 #aaaaaa"

    # Search
    search: str = "bg:#444444 #ffffff"
    search_match: str = "bg:#00aaaa #000000"

    # Status and toolbar
    toolbar: str = "bg:#444444 #ffffff"
    status: str = "reverse"

    # Messages and prompts
    prompt: str = "bold"
    continuation: str = "#888888"

    # Model/item selector specific
    model_selected: str = "bg:#00aa00 #ffffff bold"
    model_search: str = "bg:#444444 #ffffff"
    model_title: str = "#00aa00 bold"
    model_provider: str = "#888888"
    model_info: str = "#888888 italic"

    def to_dict(self) -> dict[str, str]:
        """Convert theme to dictionary format for prompt-toolkit."""

        # Convert styles with spaces to prompt-toolkit format
        # "bg:#444444 #ffffff" becomes "bg:#444444 fg:#ffffff"
        def convert_style(style: str) -> str:
            if not style:
                return style
            parts = style.split()
            result_parts = []

            for part in parts:
                if part.startswith("bg:#"):
                    result_parts.append(part)
                elif part.startswith("#"):
                    # Color without prefix, assume it's foreground
                    result_parts.append(f"fg:{part}")
                else:
                    # Other attributes like bold, italic, reverse
                    result_parts.append(part)

            return " ".join(result_parts)

        return {
            # Input field
            "": convert_style(self.input_field),
            "cursor": convert_style(self.cursor),
            "selected-text": convert_style(self.selection),
            # Completions
            "completion": convert_style(self.completion),
            "completion.current": convert_style(self.completion_selected),
            "completion.meta": convert_style(self.completion_meta),
            # Search
            "search": convert_style(self.search),
            "search.current": convert_style(self.search_match),
            # Toolbar and status
            "bottom-toolbar": convert_style(self.toolbar),
            "status": convert_style(self.status),
            # Prompts
            "prompt": convert_style(self.prompt),
            "continuation": convert_style(self.continuation),
            # Model selector
            "selected": convert_style(self.model_selected),
            "provider": convert_style(self.model_provider),
            "info": convert_style(self.model_info),
            "title": convert_style(self.model_title),
        }


@dataclass
class Theme:
    """Complete theme configuration combining console and prompt themes."""

    name: str
    description: str
    console: ConsoleTheme = field(default_factory=ConsoleTheme)
    prompt: PromptTheme = field(default_factory=PromptTheme)

    # Additional theme metadata
    is_dark: bool = True
    high_contrast: bool = False

    def __post_init__(self):
        """Validate theme after initialization."""
        if not self.name:
            raise ValueError("Theme name cannot be empty")
        if not self.description:
            raise ValueError("Theme description cannot be empty")


# Pre-defined theme name constants for consistency
class ThemeNames:
    """Standard theme name constants."""

    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    MINIMAL = "minimal"
    VIBRANT = "vibrant"
    MONOKAI_DARK = "monokai_dark"
    MONOKAI_LIGHT = "monokai_light"
    DRACULA_DARK = "dracula_dark"
    DRACULA_LIGHT = "dracula_light"
    GRUVBOX_DARK = "gruvbox_dark"
    GRUVBOX_LIGHT = "gruvbox_light"
