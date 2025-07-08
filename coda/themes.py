"""Theme configuration and management for Coda UI.

This module centralizes all UI theming, including colors, styles, and formatting
for both the interactive prompt-toolkit UI and Rich console output.

DESIGN DECISION: Single File vs Directory Structure
==================================================

Current approach (single themes.py file) is optimal because:

✅ Pros of current structure:
- Scale appropriate: 11 themes is manageable in one file (~500 lines)
- Easy theme discovery: see all options at a glance
- Simple imports: `from coda.themes import THEMES`
- Easy maintenance: validation, inheritance, consistency checks in one place
- Theme comparison: can easily compare color palettes side-by-side

❌ Cons of splitting into themes/ directory:
- Premature optimization at current scale
- More complex imports and discovery
- Harder to maintain consistency across themes
- Added complexity for minimal benefit

📋 Future refactoring criteria (consider splitting when):
- 20+ themes: file becomes unwieldy
- Plugin themes: user-contributed themes need isolation
- Complex themes: themes become much more sophisticated (animations, dynamic colors)
- Theme categories: fundamentally different types (accessibility, print-friendly, etc.)
- File size: themes.py exceeds ~1000 lines

If refactoring becomes necessary, suggested structure:
```
coda/themes/
├── __init__.py        # Theme registry and manager
├── base.py           # Theme classes and validation
├── builtin/          # Built-in themes
│   ├── default.py    # Default, dark, light, minimal, vibrant
│   ├── monokai.py    # Monokai variants
│   ├── dracula.py    # Dracula variants
│   └── gruvbox.py    # Gruvbox variants
└── plugins/          # User/plugin themes
```

Last evaluated: 2025-07-06 (11 themes, ~500 lines)
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

from prompt_toolkit.styles import Style

from .constants import (
    THEME_DARK,
    THEME_DEFAULT,
    THEME_DRACULA_DARK,
    THEME_DRACULA_LIGHT,
    THEME_GRUVBOX_DARK,
    THEME_GRUVBOX_LIGHT,
    THEME_LIGHT,
    THEME_MINIMAL,
    THEME_MONOKAI_DARK,
    THEME_MONOKAI_LIGHT,
    THEME_VIBRANT,
)


def is_valid_color(color: str) -> bool:
    """Validate if a color string is valid for Rich/prompt-toolkit.

    Args:
        color: Color string to validate

    Returns:
        bool: True if valid color
    """
    if not color:
        return True  # Empty string is valid (no styling)

    # Basic color names that Rich supports
    valid_colors = {
        "black",
        "red",
        "green",
        "yellow",
        "blue",
        "magenta",
        "cyan",
        "white",
        "bright_black",
        "bright_red",
        "bright_green",
        "bright_yellow",
        "bright_blue",
        "bright_magenta",
        "bright_cyan",
        "bright_white",
        "dim",
        "bold",
        "italic",
        "underline",
        "reverse",
        "strike",
        "blink",
    }

    # Check for hex colors
    if color.startswith("#") and len(color) in (4, 7):
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False

    # Check for basic colors (possibly with styles)
    parts = color.lower().split()
    return all(part in valid_colors for part in parts)


def validate_theme_colors(theme: "Theme") -> list[str]:
    """Validate all colors in a theme.

    Args:
        theme: Theme to validate

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    # Validate console theme colors
    console_attrs = [
        "success",
        "error",
        "warning",
        "info",
        "dim",
        "bold",
        "panel_border",
        "panel_title",
        "user_message",
        "assistant_message",
        "system_message",
        "table_header",
        "table_row_odd",
        "table_row_even",
        "command",
        "command_description",
    ]

    for attr in console_attrs:
        color = getattr(theme.console, attr, "")
        if not is_valid_color(color):
            errors.append(f"Invalid console color for {attr}: {color}")

    # Note: Prompt toolkit styles are more complex and validated by prompt_toolkit itself
    # We don't validate them here to avoid duplicating prompt_toolkit's logic

    return errors


@dataclass
class ConsoleTheme:
    """Theme configuration for Rich console output."""

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

    # Message roles
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
        """Convert theme to Rich style dictionary."""
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
    """Theme configuration for prompt-toolkit UI."""

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

    # Model selector specific
    model_selected: str = "bg:#00aa00 #ffffff bold"
    model_search: str = "bg:#444444 #ffffff"
    model_title: str = "#00aa00 bold"
    model_provider: str = "#888888"
    model_info: str = "#888888 italic"

    def to_prompt_toolkit_style(self) -> Style:
        """Convert theme to prompt-toolkit Style object."""
        return Style.from_dict(
            {
                # Input field
                "": self.input_field,
                "cursor": self.cursor,
                "selected-text": self.selection,
                # Completions
                "completion": self.completion,
                "completion.current": self.completion_selected,
                "completion.meta": self.completion_meta,
                # Search
                "search": self.search,
                "search.current": self.search_match,
                # Toolbar and status
                "bottom-toolbar": self.toolbar,
                "status": self.status,
                # Prompts
                "prompt": self.prompt,
                "continuation": self.continuation,
                # Model selector
                "selected": self.model_selected,
                "provider": self.model_provider,
                "info": self.model_info,
                "title": self.model_title,
            }
        )


@dataclass
class Theme:
    """Complete theme configuration."""

    name: str
    description: str
    console: ConsoleTheme = field(default_factory=ConsoleTheme)
    prompt: PromptTheme = field(default_factory=PromptTheme)

    # Additional theme metadata
    is_dark: bool = True
    high_contrast: bool = False


# Pre-defined themes
THEMES: dict[str, Theme] = {
    THEME_DEFAULT: Theme(
        name=THEME_DEFAULT,
        description="Default balanced theme",
        console=ConsoleTheme(),
        prompt=PromptTheme(),
        is_dark=True,
    ),
    THEME_DARK: Theme(
        name=THEME_DARK,
        description="Dark mode optimized for low light",
        console=ConsoleTheme(
            success="bright_green",
            error="bright_red",
            warning="bright_yellow",
            info="bright_cyan",
            panel_border="blue",
            user_message="bright_blue",
            assistant_message="bright_green",
            code_theme="dracula",
        ),
        prompt=PromptTheme(
            input_field="bg:#1e1e1e #ffffff",
            completion="bg:#2d2d2d #ffffff",
            completion_selected="bg:#005577 #ffffff",
            toolbar="bg:#2d2d2d #aaaaaa",
            model_selected="bg:#005577 #ffffff bold",
        ),
        is_dark=True,
    ),
    THEME_LIGHT: Theme(
        name=THEME_LIGHT,
        description="Light theme for bright environments",
        console=ConsoleTheme(
            success="green",
            error="red",
            warning="yellow",
            info="blue",
            dim="white",
            panel_border="blue",
            user_message="blue",
            assistant_message="green",
            code_theme="friendly",
        ),
        prompt=PromptTheme(
            input_field="bg:#ffffff #000000",
            completion="bg:#eeeeee #000000",
            completion_selected="bg:#dddddd #000000 bold",
            search="bg:#ffffff #000000",
            toolbar="bg:#eeeeee #000000",
            model_selected="bg:#00aa00 #ffffff bold",
        ),
        is_dark=False,
    ),
    THEME_MINIMAL: Theme(
        name=THEME_MINIMAL,
        description="Minimal colors for focused work",
        console=ConsoleTheme(
            success="white",
            error="white bold",
            warning="white",
            info="white",
            panel_border="white",
            panel_title="white bold",
            user_message="white bold",
            assistant_message="white",
            code_theme="bw",
        ),
        prompt=PromptTheme(
            completion="reverse",
            completion_selected="bold reverse",
            model_selected="reverse bold",
            model_title="bold",
        ),
        is_dark=True,
    ),
    THEME_VIBRANT: Theme(
        name=THEME_VIBRANT,
        description="High contrast with vibrant colors",
        console=ConsoleTheme(
            success="bright_green bold",
            error="bright_red bold",
            warning="bright_yellow bold",
            info="bright_cyan bold",
            panel_border="bright_magenta",
            user_message="bright_blue bold",
            assistant_message="bright_green bold",
            code_theme="rainbow_dash",
        ),
        prompt=PromptTheme(
            completion="bg:#ff00ff #ffffff",
            completion_selected="bg:#00ffff #000000 bold",
            model_selected="bg:#00ff00 #000000 bold",
            model_title="#ff00ff bold",
        ),
        is_dark=True,
        high_contrast=True,
    ),
    # Monokai themes
    THEME_MONOKAI_DARK: Theme(
        name=THEME_MONOKAI_DARK,
        description="Monokai color scheme - dark variant",
        console=ConsoleTheme(
            success="#a6e22e",  # Monokai green
            error="#f92672",  # Monokai red
            warning="#e6db74",  # Monokai yellow
            info="#66d9ef",  # Monokai blue
            dim="#75715e",  # Monokai comment
            panel_border="#66d9ef",
            panel_title="#f8f8f2",
            user_message="#66d9ef",
            assistant_message="#a6e22e",
            code_theme="monokai",
        ),
        prompt=PromptTheme(
            input_field="bg:#272822 #f8f8f2",  # Monokai background/foreground
            completion="bg:#3e3d32 #f8f8f2",
            completion_selected="bg:#49483e #f8f8f2 bold",
            search="bg:#272822 #f8f8f2",
            toolbar="bg:#3e3d32 #f8f8f2",
            model_selected="bg:#a6e22e #272822 bold",
            model_title="#f92672 bold",
            model_provider="#75715e",
            model_info="#75715e italic",
        ),
        is_dark=True,
    ),
    THEME_MONOKAI_LIGHT: Theme(
        name=THEME_MONOKAI_LIGHT,
        description="Monokai color scheme - light variant",
        console=ConsoleTheme(
            success="#529b2f",  # Darker green for light bg
            error="#d01b24",  # Darker red for light bg
            warning="#b8860b",  # Darker yellow for light bg
            info="#0066cc",  # Darker blue for light bg
            dim="#999999",
            panel_border="#0066cc",
            panel_title="#333333",
            user_message="#0066cc",
            assistant_message="#529b2f",
            code_theme="default",
        ),
        prompt=PromptTheme(
            input_field="bg:#f8f8f2 #272822",
            completion="bg:#eeeeee #272822",
            completion_selected="bg:#dddddd #272822 bold",
            search="bg:#f8f8f2 #272822",
            toolbar="bg:#eeeeee #272822",
            model_selected="bg:#529b2f #f8f8f2 bold",
            model_title="#d01b24 bold",
            model_provider="#999999",
            model_info="#999999 italic",
        ),
        is_dark=False,
    ),
    # Dracula themes
    THEME_DRACULA_DARK: Theme(
        name=THEME_DRACULA_DARK,
        description="Dracula color scheme - dark variant",
        console=ConsoleTheme(
            success="#50fa7b",  # Dracula green
            error="#ff5555",  # Dracula red
            warning="#f1fa8c",  # Dracula yellow
            info="#8be9fd",  # Dracula cyan
            dim="#6272a4",  # Dracula comment
            panel_border="#bd93f9",  # Dracula purple
            panel_title="#f8f8f2",
            user_message="#8be9fd",
            assistant_message="#50fa7b",
            code_theme="dracula",
        ),
        prompt=PromptTheme(
            input_field="bg:#282a36 #f8f8f2",  # Dracula background/foreground
            completion="bg:#44475a #f8f8f2",
            completion_selected="bg:#6272a4 #f8f8f2 bold",
            search="bg:#282a36 #f8f8f2",
            toolbar="bg:#44475a #f8f8f2",
            model_selected="bg:#50fa7b #282a36 bold",
            model_title="#ff79c6 bold",  # Dracula pink
            model_provider="#6272a4",
            model_info="#6272a4 italic",
        ),
        is_dark=True,
    ),
    THEME_DRACULA_LIGHT: Theme(
        name=THEME_DRACULA_LIGHT,
        description="Dracula color scheme - light variant",
        console=ConsoleTheme(
            success="#2d7d32",  # Darker green for light bg
            error="#d32f2f",  # Darker red for light bg
            warning="#f57f17",  # Darker yellow for light bg
            info="#0288d1",  # Darker cyan for light bg
            dim="#757575",
            panel_border="#7b1fa2",  # Darker purple for light bg
            panel_title="#212121",
            user_message="#0288d1",
            assistant_message="#2d7d32",
            code_theme="friendly",
        ),
        prompt=PromptTheme(
            input_field="bg:#f8f8f2 #282a36",
            completion="bg:#eeeeee #282a36",
            completion_selected="bg:#dddddd #282a36 bold",
            search="bg:#f8f8f2 #282a36",
            toolbar="bg:#eeeeee #282a36",
            model_selected="bg:#2d7d32 #f8f8f2 bold",
            model_title="#c2185b bold",  # Darker pink for light bg
            model_provider="#757575",
            model_info="#757575 italic",
        ),
        is_dark=False,
    ),
    # Gruvbox themes
    THEME_GRUVBOX_DARK: Theme(
        name=THEME_GRUVBOX_DARK,
        description="Gruvbox color scheme - dark variant",
        console=ConsoleTheme(
            success="#b8bb26",  # Gruvbox green
            error="#fb4934",  # Gruvbox red
            warning="#fabd2f",  # Gruvbox yellow
            info="#83a598",  # Gruvbox blue
            dim="#a89984",  # Gruvbox gray
            panel_border="#d3869b",  # Gruvbox purple
            panel_title="#ebdbb2",  # Gruvbox fg
            user_message="#83a598",
            assistant_message="#b8bb26",
            code_theme="gruvbox-dark",
        ),
        prompt=PromptTheme(
            input_field="bg:#282828 #ebdbb2",  # Gruvbox dark bg/fg
            completion="bg:#3c3836 #ebdbb2",
            completion_selected="bg:#504945 #ebdbb2 bold",
            search="bg:#282828 #ebdbb2",
            toolbar="bg:#3c3836 #ebdbb2",
            model_selected="bg:#b8bb26 #282828 bold",
            model_title="#fe8019 bold",  # Gruvbox orange
            model_provider="#a89984",
            model_info="#a89984 italic",
        ),
        is_dark=True,
    ),
    THEME_GRUVBOX_LIGHT: Theme(
        name=THEME_GRUVBOX_LIGHT,
        description="Gruvbox color scheme - light variant",
        console=ConsoleTheme(
            success="#79740e",  # Gruvbox green (light)
            error="#cc241d",  # Gruvbox red (light)
            warning="#b57614",  # Gruvbox yellow (light)
            info="#076678",  # Gruvbox blue (light)
            dim="#928374",  # Gruvbox gray (light)
            panel_border="#8f3f71",  # Gruvbox purple (light)
            panel_title="#3c3836",
            user_message="#076678",
            assistant_message="#79740e",
            code_theme="gruvbox-light",
        ),
        prompt=PromptTheme(
            input_field="bg:#fbf1c7 #3c3836",  # Gruvbox light bg/fg
            completion="bg:#f2e5bc #3c3836",
            completion_selected="bg:#ebdbb2 #3c3836 bold",
            search="bg:#fbf1c7 #3c3836",
            toolbar="bg:#f2e5bc #3c3836",
            model_selected="bg:#79740e #fbf1c7 bold",
            model_title="#af3a03 bold",  # Gruvbox orange (light)
            model_provider="#928374",
            model_info="#928374 italic",
        ),
        is_dark=False,
    ),
}


class ThemeManager:
    """Manages theme selection and application."""

    def __init__(self, theme_name: str | None = None):
        """Initialize theme manager.

        Args:
            theme_name: Name of theme to use. Defaults to THEME_DEFAULT.
        """
        self.current_theme_name = theme_name or THEME_DEFAULT
        self._current_theme: Theme | None = None

    @property
    def current_theme(self) -> Theme:
        """Get current theme object."""
        if self._current_theme is None:
            self._current_theme = THEMES.get(self.current_theme_name, THEMES[THEME_DEFAULT])
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """Set the current theme.

        Args:
            theme_name: Name of theme to use

        Raises:
            ValueError: If theme name is not recognized or theme has invalid colors
        """
        if theme_name not in THEMES:
            raise ValueError(
                f"Unknown theme: {theme_name}. Available themes: {', '.join(THEMES.keys())}"
            )

        # Validate theme colors
        theme = THEMES[theme_name]
        errors = validate_theme_colors(theme)
        if errors:
            raise ValueError(f"Theme '{theme_name}' has invalid colors:\n" + "\n".join(errors))

        self.current_theme_name = theme_name
        self._current_theme = None

    def get_console_theme(self) -> ConsoleTheme:
        """Get console theme configuration."""
        return self.current_theme.console

    def get_prompt_style(self) -> Style:
        """Get prompt-toolkit style object."""
        return self.current_theme.prompt.to_prompt_toolkit_style()

    def list_themes(self) -> dict[str, str]:
        """List available themes with descriptions."""
        return {name: theme.description for name, theme in THEMES.items()}

    @staticmethod
    def create_custom_theme(
        name: str, description: str, base_theme: str = THEME_DEFAULT, **overrides: Any
    ) -> Theme:
        """Create a custom theme based on an existing theme.

        Args:
            name: Name for the custom theme
            description: Description of the theme
            base_theme: Name of theme to base this on
            **overrides: Keyword arguments to override theme values

        Returns:
            New Theme object
        """
        base = THEMES.get(base_theme, THEMES[THEME_DEFAULT])

        # Create new theme with base values
        new_theme = Theme(
            name=name,
            description=description,
            console=ConsoleTheme(**base.console.__dict__),
            prompt=PromptTheme(**base.prompt.__dict__),
            is_dark=base.is_dark,
            high_contrast=base.high_contrast,
        )

        # Apply overrides
        for key, value in overrides.items():
            if hasattr(new_theme.console, key):
                setattr(new_theme.console, key, value)
            elif hasattr(new_theme.prompt, key):
                setattr(new_theme.prompt, key, value)
            elif hasattr(new_theme, key):
                setattr(new_theme, key, value)

        # Validate the new theme
        errors = validate_theme_colors(new_theme)
        if errors:
            raise ValueError(f"Custom theme '{name}' has invalid colors:\n" + "\n".join(errors))

        return new_theme


# Global theme manager instance
_theme_manager: ThemeManager | None = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        # Get theme from configuration
        from .configuration import get_config

        config = get_config()
        theme_name = config.ui.get("theme", THEME_DEFAULT)
        _theme_manager = ThemeManager(theme_name)
    return _theme_manager


def set_theme(theme_name: str) -> None:
    """Set the global theme.

    Args:
        theme_name: Name of theme to use
    """
    get_theme_manager().set_theme(theme_name)


def get_console_theme() -> ConsoleTheme:
    """Get current console theme configuration."""
    return get_theme_manager().get_console_theme()


def get_prompt_style() -> Style:
    """Get current prompt-toolkit style."""
    return get_theme_manager().get_prompt_style()


def get_themed_console() -> "Console":
    """Get a Rich Console instance with the current theme applied.

    Returns:
        Console instance with theme styles
    """
    from rich.console import Console
    from rich.theme import Theme as RichTheme

    console_theme = get_console_theme()
    theme_dict = console_theme.to_style_dict()

    # Add additional Rich-compatible styles
    theme_dict.update(
        {
            "panel.border": console_theme.panel_border,
            "panel.title": console_theme.panel_title,
        }
    )

    rich_theme = RichTheme(theme_dict)
    return Console(theme=rich_theme)


def create_console(force_theme: str = None) -> "Console":
    """Create a console instance with proper theming.

    This is a convenience function that allows forcing a specific theme
    temporarily without modifying the global theme configuration.

    Args:
        force_theme: Optional theme name to use instead of the current theme

    Returns:
        Console instance with appropriate theme applied

    Example:
        # Use current theme
        console = create_console()

        # Force dark theme for this console instance
        console = create_console("dark")
    """
    if force_theme:
        # Temporarily set theme, get console, then restore
        original_theme = get_theme_manager().current_theme_name
        try:
            set_theme(force_theme)
            return get_themed_console()
        finally:
            # Restore original theme
            set_theme(original_theme)
    else:
        return get_themed_console()
