"""Constants for the config module.

All configuration-specific constants are defined here to make the module self-contained.
"""

# Application metadata
APP_NAME: str = "coda"
APP_DISPLAY_NAME: str = "Coda"

# Default configuration values
DEFAULT_PROVIDER: str = "oci_genai"
DEFAULT_MODE: str = "general"
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_CONTEXT_LENGTH: int = 4096
DEFAULT_MAX_HISTORY: int = 1000
DEFAULT_THEME: str = "default"
DEFAULT_EXPORT_LIMIT: int = 50

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

# Environment variable names - only config-related ones
ENV_PREFIX: str = "CODA_"
ENV_DEFAULT_PROVIDER: str = "CODA_DEFAULT_PROVIDER"
ENV_DEBUG: str = "CODA_DEBUG"
ENV_XDG_CONFIG_HOME: str = "XDG_CONFIG_HOME"
ENV_XDG_DATA_HOME: str = "XDG_DATA_HOME"
ENV_XDG_CACHE_HOME: str = "XDG_CACHE_HOME"
