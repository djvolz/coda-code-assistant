"""Error handling for CLI operations."""

import sys
import traceback

from rich.console import Console

from coda.base.theme import ThemeManager

from .constants import COMPARTMENT_ID_MISSING, HELP_COMPARTMENT_ID


class CLIErrorHandler:
    """Handles errors in a user-friendly way for CLI operations."""

    def __init__(self, console: Console, debug: bool = False):
        self.console = console
        self.debug = debug
        theme_manager = ThemeManager()
        self.theme = theme_manager.get_console_theme()

    def handle_provider_error(self, error: Exception, provider_name: str, factory=None):
        """Handle provider-specific errors with helpful messages."""
        error_str = str(error)

        if "compartment_id is required" in error_str:
            self.console.print(
                f"\n[{self.theme.error}]Error:[/{self.theme.error}] {COMPARTMENT_ID_MISSING}"
            )
            self.console.print("\nPlease set it via one of these methods:")
            self.console.print(HELP_COMPARTMENT_ID)
        elif "Unknown provider" in error_str and factory:
            self.console.print(
                f"\n[{self.theme.error}]Error:[/{self.theme.error}] Provider '{provider_name}' not found"
            )
            self.console.print(f"\nAvailable providers: {', '.join(factory.list_available())}")
        else:
            self.console.print(f"\n[{self.theme.error}]Error:[/{self.theme.error}] {error}")

        self._show_debug_info(error)
        sys.exit(1)

    def handle_general_error(self, error: Exception):
        """Handle general errors."""
        self.console.print(f"\n[{self.theme.error}]Error:[/{self.theme.error}] {error}")
        self._show_debug_info(error)
        sys.exit(1)

    def _show_debug_info(self, error: Exception):
        """Show debug information if debug mode is enabled."""
        if self.debug:
            traceback.print_exc()

    def safe_execute(self, func, *args, **kwargs):
        """Execute a function with error handling.

        Returns the result of the function or None if an error occurred.
        """
        try:
            return func(*args, **kwargs)
        except Exception as e:
            self.handle_general_error(e)
            return None
