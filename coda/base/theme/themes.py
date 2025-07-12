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
    ThemeNames.DEFAULT: Theme(
        name=ThemeNames.DEFAULT,
        description="Default balanced theme",
        console=ConsoleTheme(),
        prompt=PromptTheme(),
        is_dark=True,
    ),
    ThemeNames.DARK: Theme(
        name=ThemeNames.DARK,
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
    ThemeNames.LIGHT: Theme(
        name=ThemeNames.LIGHT,
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
    ThemeNames.MINIMAL: Theme(
        name=ThemeNames.MINIMAL,
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
    ThemeNames.VIBRANT: Theme(
        name=ThemeNames.VIBRANT,
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
    ThemeNames.MONOKAI_DARK: Theme(
        name=ThemeNames.MONOKAI_DARK,
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
    ThemeNames.MONOKAI_LIGHT: Theme(
        name=ThemeNames.MONOKAI_LIGHT,
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
    ThemeNames.DRACULA_DARK: Theme(
        name=ThemeNames.DRACULA_DARK,
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
    ThemeNames.DRACULA_LIGHT: Theme(
        name=ThemeNames.DRACULA_LIGHT,
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
    ThemeNames.GRUVBOX_DARK: Theme(
        name=ThemeNames.GRUVBOX_DARK,
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
    ThemeNames.GRUVBOX_LIGHT: Theme(
        name=ThemeNames.GRUVBOX_LIGHT,
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
