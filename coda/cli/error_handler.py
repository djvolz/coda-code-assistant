"""Error handling for CLI operations."""

import sys
import traceback

from rich.console import Console


class CLIErrorHandler:
    """Handles errors in a user-friendly way for CLI operations."""

    def __init__(self, console: Console, debug: bool = False):
        self.console = console
        self.debug = debug

    def handle_provider_error(self, error: Exception, provider_name: str, factory=None):
        """Handle provider-specific errors with helpful messages."""
        error_str = str(error)

        if "compartment_id is required" in error_str:
            self.console.print("\n[red]Error:[/red] OCI compartment ID not configured")
            self.console.print("\nPlease set it via one of these methods:")
            self.console.print(
                "1. Environment variable: [cyan]export OCI_COMPARTMENT_ID='your-compartment-id'[/cyan]"
            )
            self.console.print("2. Coda config file: [cyan]~/.config/coda/config.toml[/cyan]")
        elif "Unknown provider" in error_str and factory:
            self.console.print(f"\n[red]Error:[/red] Provider '{provider_name}' not found")
            self.console.print(f"\nAvailable providers: {', '.join(factory.list_available())}")
        else:
            self.console.print(f"\n[red]Error:[/red] {error}")

        self._show_debug_info(error)
        sys.exit(1)

    def handle_general_error(self, error: Exception):
        """Handle general errors."""
        self.console.print(f"\n[red]Error:[/red] {error}")
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

