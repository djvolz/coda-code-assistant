"""Constants for the themes module.

All theme-specific constants are defined here to make the module self-contained.
"""

# Theme identifiers
DEFAULT: str = "default"
DARK: str = "dark"
LIGHT: str = "light"
MINIMAL: str = "minimal"
VIBRANT: str = "vibrant"
MONOKAI_DARK: str = "monokai_dark"
MONOKAI_LIGHT: str = "monokai_light"
DRACULA_DARK: str = "dracula_dark"
DRACULA_LIGHT: str = "dracula_light"
GRUVBOX_DARK: str = "gruvbox_dark"
GRUVBOX_LIGHT: str = "gruvbox_light"

# List of all available themes
ALL_THEMES: list[str] = [
    DEFAULT,
    DARK,
    LIGHT,
    MINIMAL,
    VIBRANT,
    MONOKAI_DARK,
    MONOKAI_LIGHT,
    DRACULA_DARK,
    DRACULA_LIGHT,
    GRUVBOX_DARK,
    GRUVBOX_LIGHT,
]

# Individual theme constants (for backward compatibility and explicit imports)
THEME_DEFAULT: str = DEFAULT
THEME_DARK: str = DARK
THEME_LIGHT: str = LIGHT
THEME_MINIMAL: str = MINIMAL
THEME_VIBRANT: str = VIBRANT
THEME_MONOKAI_DARK: str = MONOKAI_DARK
THEME_MONOKAI_LIGHT: str = MONOKAI_LIGHT
THEME_DRACULA_DARK: str = DRACULA_DARK
THEME_DRACULA_LIGHT: str = DRACULA_LIGHT
THEME_GRUVBOX_DARK: str = GRUVBOX_DARK
THEME_GRUVBOX_LIGHT: str = GRUVBOX_LIGHT
