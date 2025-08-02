"""Constants for the themes module.

All theme-specific constants are defined here to make the module self-contained.
"""

# Theme identifiers
DARK: str = "dark"
LIGHT: str = "light"

# List of all available themes
ALL_THEMES: list[str] = [
    DARK,
    LIGHT,
]

# Individual theme constants (for backward compatibility and explicit imports)
THEME_DARK: str = DARK
THEME_LIGHT: str = LIGHT
