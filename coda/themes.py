"""Theme configuration and management for Coda UI.

This module centralizes all UI theming, including colors, styles, and formatting
for both the interactive prompt-toolkit UI and Rich console output.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional
from prompt_toolkit.styles import Style

from .constants import (
    THEME_DEFAULT,
    THEME_DARK,
    THEME_LIGHT,
    THEME_MINIMAL,
    THEME_VIBRANT,
    AVAILABLE_THEMES,
)


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
    
    def to_style_dict(self) -> Dict[str, str]:
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
    
    def to_prompt_toolkit_style(self) -> Style:
        """Convert theme to prompt-toolkit Style object."""
        return Style.from_dict({
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
            "provider": "#888888",
            "info": "#888888 italic",
            "title": self.model_title,
        })


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
THEMES: Dict[str, Theme] = {
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
            warning="yellow3",
            info="blue",
            dim="grey50",
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
}


class ThemeManager:
    """Manages theme selection and application."""
    
    def __init__(self, theme_name: Optional[str] = None):
        """Initialize theme manager.
        
        Args:
            theme_name: Name of theme to use. Defaults to THEME_DEFAULT.
        """
        self.current_theme_name = theme_name or THEME_DEFAULT
        self._current_theme: Optional[Theme] = None
    
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
            ValueError: If theme name is not recognized
        """
        if theme_name not in THEMES:
            raise ValueError(
                f"Unknown theme: {theme_name}. "
                f"Available themes: {', '.join(THEMES.keys())}"
            )
        self.current_theme_name = theme_name
        self._current_theme = None
    
    def get_console_theme(self) -> ConsoleTheme:
        """Get console theme configuration."""
        return self.current_theme.console
    
    def get_prompt_style(self) -> Style:
        """Get prompt-toolkit style object."""
        return self.current_theme.prompt.to_prompt_toolkit_style()
    
    def list_themes(self) -> Dict[str, str]:
        """List available themes with descriptions."""
        return {name: theme.description for name, theme in THEMES.items()}
    
    @staticmethod
    def create_custom_theme(
        name: str,
        description: str,
        base_theme: str = THEME_DEFAULT,
        **overrides: Any
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
        
        return new_theme


# Global theme manager instance
_theme_manager: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get the global theme manager instance."""
    global _theme_manager
    if _theme_manager is None:
        _theme_manager = ThemeManager()
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