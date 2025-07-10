"""All constants definitions for Coda.

This module contains all constant values organized by category.
It has zero external dependencies and uses only Python standard library.
"""

from typing import Any


class _ConstantNamespace:
    """Base class for constant namespaces to prevent modification."""

    def __setattr__(self, name: str, value: Any) -> None:
        if hasattr(self, name):
            raise AttributeError(f"Cannot modify constant: {name}")
        super().__setattr__(name, value)


class _APP(_ConstantNamespace):
    """Application metadata constants."""

    NAME: str = "coda"
    DISPLAY_NAME: str = "Coda"


class _UI(_ConstantNamespace):
    """User interface constants."""

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


class _API(_ConstantNamespace):
    """API and network constants."""

    # Timeouts (in seconds)
    TIMEOUT: int = 30

    # Cache durations (in seconds)
    MODEL_CACHE_DURATION: int = 24 * 60 * 60  # 24 hours
    PROVIDER_CACHE_DURATION: int = 60 * 60  # 1 hour

    # Token management
    CONTEXT_AGGRESSIVE_RATIO: float = 0.6
    CONTEXT_BALANCED_RATIO: float = 0.75
    CONTEXT_CONSERVATIVE_RATIO: float = 0.9
    PRESERVE_LAST_N_MESSAGES: int = 10


class _DEFAULTS(_ConstantNamespace):
    """Default configuration values."""

    PROVIDER: str = "oci_genai"
    MODE: str = "general"
    TEMPERATURE: float = 0.7
    CONTEXT_LENGTH: int = 4096
    MAX_HISTORY: int = 1000
    THEME: str = "default"
    EXPORT_LIMIT: int = 50


class _LIMITS(_ConstantNamespace):
    """System limits and constraints."""

    # Session limits
    SESSION_LIST: int = 50
    SESSION_SEARCH: int = 10
    SESSION_DELETE: int = 1000
    SESSION_INFO: int = 100
    SESSION_LAST: int = 1


class _PROVIDERS(_ConstantNamespace):
    """Provider identifiers."""

    OCI_GENAI: str = "oci_genai"
    LITELLM: str = "litellm"
    OLLAMA: str = "ollama"
    MOCK: str = "mock"
    OPENAI: str = "openai"

    @property
    def ALL(self) -> list[str]:
        """Get list of all available providers."""
        return [
            self.OCI_GENAI,
            self.LITELLM,
            self.OLLAMA,
            self.MOCK,
        ]


class _THEMES(_ConstantNamespace):
    """Theme identifiers."""

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

    @property
    def ALL(self) -> list[str]:
        """Get list of all available themes."""
        return [
            self.DEFAULT,
            self.DARK,
            self.LIGHT,
            self.MINIMAL,
            self.VIBRANT,
            self.MONOKAI_DARK,
            self.MONOKAI_LIGHT,
            self.DRACULA_DARK,
            self.DRACULA_LIGHT,
            self.GRUVBOX_DARK,
            self.GRUVBOX_LIGHT,
        ]


class _MODES(_ConstantNamespace):
    """Developer mode identifiers."""

    GENERAL: str = "general"
    CODE: str = "code"
    DEBUG: str = "debug"
    EXPLAIN: str = "explain"
    REVIEW: str = "review"
    REFACTOR: str = "refactor"
    PLAN: str = "plan"

    @property
    def ALL(self) -> list[str]:
        """Get list of all available modes."""
        return [
            self.GENERAL,
            self.CODE,
            self.DEBUG,
            self.EXPLAIN,
            self.REVIEW,
            self.REFACTOR,
            self.PLAN,
        ]


class _EXPORT(_ConstantNamespace):
    """Export format identifiers."""

    JSON: str = "json"
    MARKDOWN: str = "markdown"
    TXT: str = "txt"
    HTML: str = "html"

    @property
    def ALL(self) -> list[str]:
        """Get list of all export formats."""
        return [
            self.JSON,
            self.MARKDOWN,
            self.TXT,
            self.HTML,
        ]


class _ROLES(_ConstantNamespace):
    """Message role identifiers."""

    USER: str = "user"
    ASSISTANT: str = "assistant"
    SYSTEM: str = "system"
    TOOL: str = "tool"


class _SESSION(_ConstantNamespace):
    """Session-related constants."""

    # Status values
    STATUS_ACTIVE: str = "active"
    STATUS_ARCHIVED: str = "archived"
    STATUS_DELETED: str = "deleted"

    # Naming patterns
    AUTO_PREFIX: str = "auto-"
    AUTO_DATE_FORMAT: str = "%Y%m%d-%H%M%S"

    # Database
    FTS_TABLE_NAME: str = "messages_fts"
    FTS_CONTENT_TABLE: str = "messages"


class _ERRORS(_ConstantNamespace):
    """Error message templates."""

    COMPARTMENT_ID_MISSING: str = "OCI compartment ID not configured"
    PROVIDER_NOT_FOUND: str = "Provider '{provider}' not found"
    MODEL_NOT_FOUND: str = "Model '{model}' not found"
    SESSION_NOT_FOUND: str = "Session '{session}' not found"
    INVALID_EXPORT_FORMAT: str = "Invalid export format: {format}"

    # Help text
    HELP_COMPARTMENT_ID: str = """Please set it via one of these methods:
1. Environment variable: export OCI_COMPARTMENT_ID='your-compartment-id'
2. Coda config file: ~/.config/coda/config.toml"""


class _FILES(_ConstantNamespace):
    """File system constants."""

    # Directory names
    CONFIG_DIR: str = "coda"
    DATA_DIR: str = "coda"
    CACHE_DIR: str = "coda"
    PROJECT_CONFIG_DIR: str = ".coda"
    OBSERVABILITY_DIR: str = "observability"

    # File names
    CONFIG_FILE: str = "config.toml"
    SESSION_DB: str = "sessions.db"
    HISTORY_FILE: str = "history.txt"
    FIRST_RUN_MARKER: str = ".first_run_complete"
    METRICS_FILE: str = "metrics.json"
    TRACES_FILE: str = "traces.json"

    # Extensions
    EXT_CONFIG: str = ".toml"
    EXT_JSON: str = ".json"
    EXT_MARKDOWN: str = ".md"
    EXT_TEXT: str = ".txt"
    EXT_HTML: str = ".html"

    # XDG paths (these are patterns, not actual paths)
    XDG_CONFIG_PATTERN: str = ".config"
    XDG_DATA_PATTERN: str = ".local/share"
    XDG_CACHE_PATTERN: str = ".cache"
    SYSTEM_CONFIG_PATTERN: str = "/etc"


class _ENV(_ConstantNamespace):
    """Environment variable names."""

    # Prefix for all Coda env vars
    PREFIX: str = "CODA_"

    # Core environment variables
    DEFAULT_PROVIDER: str = "CODA_DEFAULT_PROVIDER"
    DEBUG: str = "CODA_DEBUG"

    # OCI specific
    OCI_COMPARTMENT_ID: str = "OCI_COMPARTMENT_ID"

    # XDG compliance
    XDG_CONFIG_HOME: str = "XDG_CONFIG_HOME"
    XDG_DATA_HOME: str = "XDG_DATA_HOME"
    XDG_CACHE_HOME: str = "XDG_CACHE_HOME"

    # Observability
    OBSERVABILITY_ENABLED: str = "CODA_OBSERVABILITY_ENABLED"
    OBSERVABILITY_EXPORT_DIR: str = "CODA_OBSERVABILITY_EXPORT_DIR"
    METRICS_FLUSH_INTERVAL: str = "CODA_METRICS_FLUSH_INTERVAL"
    TRACING_SAMPLE_RATE: str = "CODA_TRACING_SAMPLE_RATE"
    TRACING_MAX_SPANS: str = "CODA_TRACING_MAX_SPANS"
    TRACING_FLUSH_INTERVAL: str = "CODA_TRACING_FLUSH_INTERVAL"
    HEALTH_CHECK_INTERVAL: str = "CODA_HEALTH_CHECK_INTERVAL"
    HEALTH_UNHEALTHY_THRESHOLD: str = "CODA_HEALTH_UNHEALTHY_THRESHOLD"
    HEALTH_DEGRADED_THRESHOLD: str = "CODA_HEALTH_DEGRADED_THRESHOLD"


class _OBSERVABILITY(_ConstantNamespace):
    """Observability default values."""

    ENABLED: bool = False
    METRICS_FLUSH_INTERVAL: int = 300  # 5 minutes
    TRACING_SAMPLE_RATE: float = 1.0  # 100% sampling
    TRACING_MAX_SPANS: int = 1000
    TRACING_FLUSH_INTERVAL: int = 60  # 1 minute
    HEALTH_CHECK_INTERVAL: int = 30  # 30 seconds
    HEALTH_UNHEALTHY_THRESHOLD: int = 3
    HEALTH_DEGRADED_THRESHOLD: float = 5000.0  # 5 seconds


# Create singleton instances
APP = _APP()
UI = _UI()
API = _API()
DEFAULTS = _DEFAULTS()
LIMITS = _LIMITS()
PROVIDERS = _PROVIDERS()
THEMES = _THEMES()
MODES = _MODES()
EXPORT = _EXPORT()
ROLES = _ROLES()
SESSION = _SESSION()
ERRORS = _ERRORS()
FILES = _FILES()
ENV = _ENV()
OBSERVABILITY = _OBSERVABILITY()
