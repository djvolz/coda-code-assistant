"""🔧 BASE MODULE
Standalone terminal/UI theme management module.

This module provides comprehensive theming support for terminal applications:
- Console themes (colors, styles for terminal output)
- Prompt themes (input fields, completions, toolbars)
- Theme validation and customization
- Zero required dependencies

Example usage:
    from coda.theme import Theme, ThemeManager

    # Use default theme
    theme_mgr = ThemeManager()
    console_theme = theme_mgr.get_console_theme()

    # Set specific theme
    theme_mgr.set_theme("dark")

    # Create custom theme
    custom = ThemeManager.create_custom_theme(
        "mycompany",
        "Company brand colors",
        base_theme="default",
        success="#00aa00",
        error="#ff0000"
    )
"""

from .manager import Theme, ThemeManager
from .models import ConsoleTheme, PromptTheme
from .themes import THEMES, get_theme_names

__all__ = [
    "Theme",
    "ThemeManager",
    "ConsoleTheme",
    "PromptTheme",
    "THEMES",
    "get_theme_names",
]
