"""Constants for the CLI module.

All CLI-specific constants are defined here to make the module self-contained.
"""

# Display limits
MAX_LINE_LENGTH: int = 80
MAX_MODELS_DISPLAY: int = 20
MAX_MODELS_BASIC_DISPLAY: int = 10
CONSOLE_WIDTH_DEFAULT: int = 80

# Prompt toolkit styles
PROMPT_STYLE_SELECTED: str = "bg:#00aa00 #ffffff bold"
PROMPT_STYLE_SEARCH: str = "bg:#444444 #ffffff"
PROMPT_STYLE_TITLE: str = "#00aa00 bold"

# Panel styles
PANEL_BORDER_STYLE: str = "cyan"
PANEL_TITLE_STYLE: str = "bold"

# Status messages
COMING_SOON: str = "(Coming soon)"
NOT_IMPLEMENTED: str = "Not implemented yet"


# Developer modes
class DeveloperMode:
    """Developer mode identifiers."""

    GENERAL: str = "general"
    CODE: str = "code"
    DEBUG: str = "debug"
    EXPLAIN: str = "explain"
    REVIEW: str = "review"
    REFACTOR: str = "refactor"
    PLAN: str = "plan"

    @classmethod
    def all(cls) -> list[str]:
        """Get all available modes."""
        return [
            cls.GENERAL,
            cls.CODE,
            cls.DEBUG,
            cls.EXPLAIN,
            cls.REVIEW,
            cls.REFACTOR,
            cls.PLAN,
        ]


# Export formats
class ExportFormat:
    """Export format identifiers."""

    JSON: str = "json"
    MARKDOWN: str = "markdown"
    TXT: str = "txt"
    HTML: str = "html"

    @classmethod
    def all(cls) -> list[str]:
        """Get all export formats."""
        return [
            cls.JSON,
            cls.MARKDOWN,
            cls.TXT,
            cls.HTML,
        ]


# File names
HISTORY_FILE: str = "history.txt"

# Error messages
COMPARTMENT_ID_MISSING: str = "OCI compartment ID not configured"
PROVIDER_NOT_FOUND: str = "Provider '{provider}' not found"
MODEL_NOT_FOUND: str = "Model '{model}' not found"
SESSION_NOT_FOUND: str = "Session '{session}' not found"
INVALID_EXPORT_FORMAT: str = "Invalid export format: {format}"

# Help text
HELP_COMPARTMENT_ID: str = """Please set it via one of these methods:
1. Environment variable: export OCI_COMPARTMENT_ID='your-compartment-id'
2. Coda config file: ~/.config/coda/config.toml"""
