"""Theme manager implementation.

This module provides the main theme management functionality.
Zero dependencies except for theme models and validation.
"""

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from rich.console import Console

try:
    from .models import ConsoleTheme, PromptTheme, Theme, ThemeNames
    from .themes import THEMES
    from .validation import validate_theme_colors
except ImportError:
    # If running as standalone after copy-paste
    from models import ConsoleTheme, PromptTheme, Theme, ThemeNames
    from themes import THEMES
    from validation import validate_theme_colors


class ThemeManager:
    """Manages theme selection and application."""

    def __init__(self, theme_name: str | None = None):
        """Initialize theme manager.

        Args:
            theme_name: Name of theme to use. Defaults to 'default'.
        """
        self.current_theme_name = theme_name or ThemeNames.DEFAULT
        self._current_theme: Theme | None = None
        self._custom_themes: dict[str, Theme] = {}

    @property
    def current_theme(self) -> Theme:
        """Get current theme object."""
        if self._current_theme is None:
            # Check custom themes first
            if self.current_theme_name in self._custom_themes:
                self._current_theme = self._custom_themes[self.current_theme_name]
            else:
                self._current_theme = THEMES.get(
                    self.current_theme_name, THEMES[ThemeNames.DEFAULT]
                )
        return self._current_theme

    def set_theme(self, theme_name: str) -> None:
        """Set the current theme.

        Args:
            theme_name: Name of theme to use

        Raises:
            ValueError: If theme name is not recognized or theme has invalid colors
        """
        # Check if it's a valid theme
        if theme_name not in THEMES and theme_name not in self._custom_themes:
            available = list(THEMES.keys()) + list(self._custom_themes.keys())
            raise ValueError(
                f"Unknown theme: {theme_name}. Available themes: {', '.join(available)}"
            )

        # Validate theme colors
        if theme_name in self._custom_themes:
            theme = self._custom_themes[theme_name]
        else:
            theme = THEMES[theme_name]

        errors = validate_theme_colors(theme)
        if errors:
            raise ValueError(f"Theme '{theme_name}' has invalid colors:\n" + "\n".join(errors))

        self.current_theme_name = theme_name
        self._current_theme = None

    def get_console_theme(self) -> ConsoleTheme:
        """Get console theme configuration."""
        return self.current_theme.console

    def get_prompt_theme(self) -> PromptTheme:
        """Get prompt theme configuration."""
        return self.current_theme.prompt

    def get_console(self) -> "Console":
        """Get a Rich console with the current theme applied."""
        from rich.console import Console
        from rich.theme import Theme as RichTheme

        console_theme = self.get_console_theme()

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

    def list_themes(self) -> dict[str, str]:
        """List available themes with descriptions.

        Returns:
            Dictionary mapping theme names to descriptions
        """
        themes = {name: theme.description for name, theme in THEMES.items()}
        themes.update({name: theme.description for name, theme in self._custom_themes.items()})
        return themes

    def list_theme_names(self) -> list[str]:
        """List available theme names.

        Returns:
            List of theme names
        """
        return list(THEMES.keys()) + list(self._custom_themes.keys())

    def register_custom_theme(self, theme: Theme) -> None:
        """Register a custom theme.

        Args:
            theme: Theme to register

        Raises:
            ValueError: If theme has invalid colors or name conflicts
        """
        # Validate theme
        errors = validate_theme_colors(theme)
        if errors:
            raise ValueError(
                f"Custom theme '{theme.name}' has invalid colors:\n" + "\n".join(errors)
            )

        # Warn if overriding built-in theme
        if theme.name in THEMES:
            import warnings

            warnings.warn(
                f"Custom theme '{theme.name}' overrides built-in theme", UserWarning, stacklevel=2
            )

        self._custom_themes[theme.name] = theme

    @staticmethod
    def create_custom_theme(
        name: str, description: str, base_theme: str = ThemeNames.DEFAULT, **overrides: Any
    ) -> Theme:
        """Create a custom theme based on an existing theme.

        Args:
            name: Name for the custom theme
            description: Description of the theme
            base_theme: Name of theme to base this on
            **overrides: Keyword arguments to override theme values

        Returns:
            New Theme object

        Example:
            >>> theme = ThemeManager.create_custom_theme(
            ...     "mycompany",
            ...     "Company brand colors",
            ...     base_theme="dark",
            ...     success="#00aa00",
            ...     error="#ff0000",
            ...     panel_border="#0066cc"
            ... )
        """
        base = THEMES.get(base_theme, THEMES[ThemeNames.DEFAULT])

        # Create new theme with base values
        new_theme = Theme(
            name=name,
            description=description,
            console=ConsoleTheme(**base.console.__dict__.copy()),
            prompt=PromptTheme(**base.prompt.__dict__.copy()),
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

    def export_theme(self, theme_name: str | None = None) -> dict[str, Any]:
        """Export a theme as a dictionary.

        Args:
            theme_name: Name of theme to export (current theme if None)

        Returns:
            Theme configuration as dictionary
        """
        if theme_name is None:
            theme = self.current_theme
        elif theme_name in self._custom_themes:
            theme = self._custom_themes[theme_name]
        elif theme_name in THEMES:
            theme = THEMES[theme_name]
        else:
            raise ValueError(f"Unknown theme: {theme_name}")

        return {
            "name": theme.name,
            "description": theme.description,
            "is_dark": theme.is_dark,
            "high_contrast": theme.high_contrast,
            "console": theme.console.__dict__,
            "prompt": theme.prompt.__dict__,
        }

    def import_theme(self, theme_data: dict[str, Any]) -> Theme:
        """Import a theme from a dictionary.

        Args:
            theme_data: Theme configuration dictionary

        Returns:
            Imported Theme object
        """
        # Extract data with defaults
        name = theme_data.get("name", "imported")
        description = theme_data.get("description", "Imported theme")
        is_dark = theme_data.get("is_dark", True)
        high_contrast = theme_data.get("high_contrast", False)

        # Create console theme
        console_data = theme_data.get("console", {})
        console = ConsoleTheme(**console_data)

        # Create prompt theme
        prompt_data = theme_data.get("prompt", {})
        prompt = PromptTheme(**prompt_data)

        # Create theme
        theme = Theme(
            name=name,
            description=description,
            console=console,
            prompt=prompt,
            is_dark=is_dark,
            high_contrast=high_contrast,
        )

        # Validate
        errors = validate_theme_colors(theme)
        if errors:
            raise ValueError(f"Imported theme '{name}' has invalid colors:\n" + "\n".join(errors))

        return theme
