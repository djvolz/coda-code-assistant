"""Compatibility layer for old theme API."""

from rich.console import Console
from .manager import ThemeManager
from .models import ConsoleTheme

# Global theme manager instance
_theme_manager = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
    return _theme_manager


def get_console_theme() -> ConsoleTheme:
    """Get the current console theme (compatibility function)."""
    theme_mgr = get_theme_manager()
    return theme_mgr.current_theme.console


def get_themed_console() -> Console:
    """Get a Rich console with the current theme applied (compatibility function)."""
    theme_mgr = get_theme_manager()
    console_theme = theme_mgr.get_console_theme()
    
    # Create a Rich console with the theme's style
    from rich.theme import Theme as RichTheme
    
    # Build Rich theme from our console theme colors
    style_dict = {
        "info": console_theme.info,
        "warning": console_theme.warning,
        "error": console_theme.error,
        "success": console_theme.success,
        "dim": console_theme.dim,
        "bold": console_theme.bold,
        "panel.border": console_theme.panel_border,
        "panel.title": console_theme.panel_title,
        "command": console_theme.command,
    }
    
    rich_theme = RichTheme(style_dict)
    return Console(theme=rich_theme)


# Re-export for backward compatibility
from .themes import THEMES