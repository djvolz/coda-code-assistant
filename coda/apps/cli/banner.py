"""Banner utilities for CLI applications.

This module provides consistent banner display functionality across
different CLI entry points.
"""

import os

from rich.text import Text

try:
    from coda.__version__ import __version__
except ImportError:
    __version__ = "dev"


def create_welcome_banner(theme) -> Text:
    """Create the welcome banner with ASCII art and version info.

    Args:
        theme: Theme object containing console theme colors

    Returns:
        Text: Rich Text object with formatted banner
    """
    banner_text = Text.from_markup(
        f"[{theme.panel_title}]"
        " ██████╗ ██████╗ ██████╗  █████╗ \n"
        "██╔════╝██╔═══██╗██╔══██╗██╔══██╗\n"
        "██║     ██║   ██║██║  ██║███████║\n"
        "██║     ██║   ██║██║  ██║██╔══██║\n"
        "╚██████╗╚██████╔╝██████╔╝██║  ██║\n"
        " ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝"
        f"[/{theme.panel_title}]\n"
        f"[{theme.info}]✨ Your AI-powered coding companion[/{theme.info}]\n"
        f"[{theme.dim}]v{__version__} • {os.getcwd()}[/{theme.dim}]"
    )

    return banner_text
