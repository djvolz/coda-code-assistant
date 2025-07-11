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
    return theme_mgr.get_console()


# Re-export for backward compatibility
from .themes import THEMES