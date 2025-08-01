"""Pre-defined themes for the theme module.

This module contains all built-in theme definitions.
Zero dependencies - uses only theme models.
"""

try:
    from .models import ConsoleTheme, PromptTheme, Theme, ThemeNames
except ImportError:
    # If running as standalone after copy-paste
    from models import ConsoleTheme, PromptTheme, Theme, ThemeNames


# Pre-defined themes collection
THEMES: dict[str, Theme] = {
    ThemeNames.DARK: Theme(
        name=ThemeNames.DARK,
        description="Dark mode optimized for low light",
        console=ConsoleTheme(
            success="white",  # Changed from bright_green to white
            error="bright_red",
            warning="bright_yellow",
            info="bold cyan",  # Bold cyan for Assistant label
            panel_border="blue",
            panel_title="white bold",
            user_message="bright_blue",
            assistant_message="white",  # Changed from bright_green to white
            system_message="yellow",
            code_theme="monokai",
            table_header="bold cyan",
            table_row_odd="",
            table_row_even="dim",
            dim="#888888",
            bold="bold",
            command="cyan",
            command_description="",
        ),
        prompt=PromptTheme(
            input_field="",  # No background, use terminal default
            completion="bg:#2d2d2d #ffffff",
            completion_selected="bg:#005577 #ffffff",
            toolbar="bg:#2d2d2d #aaaaaa",
            model_selected="bg:#005577 #ffffff bold",
            model_title="#ffffff bold",  # White for better readability
            search="bg:#444444 #ffffff",
            search_match="bg:#005577 #ffffff",  # Changed from cyan to blue
            success="#ffffff",  # White instead of green
            error="#ff6666",
            warning="#ffff66",
            info="#66ccff",
        ),
        is_dark=True,
    ),
    ThemeNames.LIGHT: Theme(
        name=ThemeNames.LIGHT,
        description="Light theme for bright environments",
        console=ConsoleTheme(
            success="#006400",  # Dark green
            error="#8b0000",  # Dark red
            warning="#b8860b",  # Dark goldenrod
            info="bold blue",  # Bold blue for Assistant label visibility
            panel_border="#00008b",  # Dark blue
            panel_title="bold blue",  # Bold blue for visibility
            user_message="#00008b",  # Dark blue
            assistant_message="black",  # Black for better contrast on white bg
            system_message="#8b008b",  # Dark magenta
            code_theme="friendly",
            table_header="bold blue",  # Bold blue (simplified)
            table_row_odd="",
            table_row_even="#f0f0f0",
            dim="#666666",
            bold="bold",
            command="#00008b",  # Dark blue
            command_description="",
        ),
        prompt=PromptTheme(
            input_field="",  # No background, use terminal default
            completion="bg:#eeeeee #000000",
            completion_selected="bg:#0066cc #ffffff bold",
            toolbar="bg:#eeeeee #000000",
            model_selected="bg:#006600 #ffffff bold",
            model_title="#000000 bold",  # Black text for better contrast on light background
            search="bg:#eeeeee #000000",
            search_match="bg:#0066cc #ffffff",
        ),
        is_dark=False,
    ),
}


def get_theme_names() -> list[str]:
    """Get list of all available theme names."""
    return list(THEMES.keys())


def get_dark_themes() -> list[str]:
    """Get list of dark theme names."""
    return [name for name, theme in THEMES.items() if theme.is_dark]


def get_light_themes() -> list[str]:
    """Get list of light theme names."""
    return [name for name, theme in THEMES.items() if not theme.is_dark]


def get_high_contrast_themes() -> list[str]:
    """Get list of high contrast theme names."""
    return [name for name, theme in THEMES.items() if theme.high_contrast]
