"""Constants and configuration values for Coda.

This module centralizes all hardcoded values that were previously scattered
throughout the codebase, making them easier to maintain and modify.
"""

from pathlib import Path
import os

# Version and metadata
APP_NAME = "coda"
APP_DISPLAY_NAME = "Coda"

# Directory structure constants
CONFIG_DIR_NAME = "coda"
DATA_DIR_NAME = "coda"
CACHE_DIR_NAME = "coda"

# File names and extensions
CONFIG_FILE_NAME = "config.toml"
SESSION_DB_NAME = "sessions.db"
HISTORY_FILE_NAME = "history.txt"
FIRST_RUN_MARKER = ".first_run_complete"

# File extensions
CONFIG_FILE_EXT = ".toml"
JSON_FILE_EXT = ".json"
MARKDOWN_FILE_EXT = ".md"
TEXT_FILE_EXT = ".txt"
HTML_FILE_EXT = ".html"

# XDG-compliant directory paths
def get_config_dir() -> Path:
    """Get XDG-compliant config directory."""
    xdg_config = os.environ.get("XDG_CONFIG_HOME")
    if xdg_config:
        return Path(xdg_config) / CONFIG_DIR_NAME
    return Path.home() / ".config" / CONFIG_DIR_NAME

def get_data_dir() -> Path:
    """Get XDG-compliant data directory."""
    xdg_data = os.environ.get("XDG_DATA_HOME")
    if xdg_data:
        return Path(xdg_data) / DATA_DIR_NAME
    return Path.home() / ".local" / "share" / DATA_DIR_NAME

def get_cache_dir() -> Path:
    """Get XDG-compliant cache directory."""
    xdg_cache = os.environ.get("XDG_CACHE_HOME")
    if xdg_cache:
        return Path(xdg_cache) / CACHE_DIR_NAME
    return Path.home() / ".cache" / CACHE_DIR_NAME

# Default paths
USER_CONFIG_PATH = get_config_dir() / CONFIG_FILE_NAME
SESSION_DB_PATH = get_cache_dir() / SESSION_DB_NAME
HISTORY_FILE_PATH = get_data_dir() / HISTORY_FILE_NAME
FIRST_RUN_MARKER_PATH = get_data_dir() / FIRST_RUN_MARKER

# Project-specific paths
PROJECT_CONFIG_DIR = ".coda"
PROJECT_CONFIG_FILE = PROJECT_CONFIG_DIR + "/" + CONFIG_FILE_NAME

# System config path (rarely used)
SYSTEM_CONFIG_PATH = Path("/etc") / CONFIG_DIR_NAME / CONFIG_FILE_NAME

# Environment variable names
ENV_PREFIX = "CODA_"
ENV_DEFAULT_PROVIDER = ENV_PREFIX + "DEFAULT_PROVIDER"
ENV_DEBUG = ENV_PREFIX + "DEBUG"
ENV_OCI_COMPARTMENT_ID = "OCI_COMPARTMENT_ID"
ENV_XDG_CONFIG_HOME = "XDG_CONFIG_HOME"
ENV_XDG_DATA_HOME = "XDG_DATA_HOME"
ENV_XDG_CACHE_HOME = "XDG_CACHE_HOME"

# Default configuration values
DEFAULT_PROVIDER = "oci_genai"
DEFAULT_MODE = "general"
DEFAULT_TEMPERATURE = 0.7
DEFAULT_CONTEXT_LENGTH = 4096
DEFAULT_MAX_HISTORY = 1000

# Session and query limits
SESSION_LIST_LIMIT = 50
SESSION_SEARCH_LIMIT = 10
SESSION_DELETE_LIMIT = 1000
SESSION_INFO_LIMIT = 100
SESSION_LAST_LIMIT = 1
DEFAULT_EXPORT_LIMIT = 50

# Cache durations (in seconds)
MODEL_CACHE_DURATION = 24 * 60 * 60  # 24 hours
PROVIDER_CACHE_DURATION = 60 * 60    # 1 hour

# Database schema constants
FTS_TABLE_NAME = "messages_fts"
FTS_CONTENT_TABLE = "messages"

# Session naming patterns
AUTO_SESSION_PREFIX = "auto-"
AUTO_SESSION_DATE_FORMAT = "%Y%m%d-%H%M%S"

# CLI display limits
MAX_MODELS_DISPLAY = 20
MAX_MODELS_BASIC_DISPLAY = 10
CONSOLE_WIDTH_DEFAULT = 80

# Token limits for context management
CONTEXT_AGGRESSIVE_RATIO = 0.6
CONTEXT_BALANCED_RATIO = 0.75
CONTEXT_CONSERVATIVE_RATIO = 0.9
PRESERVE_LAST_N_MESSAGES = 10

# Provider names (for registry)
PROVIDER_OCI_GENAI = "oci_genai"
PROVIDER_LITELLM = "litellm"
PROVIDER_OLLAMA = "ollama"
PROVIDER_MOCK = "mock"
PROVIDER_OPENAI = "openai"  # Coming soon

# Available providers list
AVAILABLE_PROVIDERS = [
    PROVIDER_OCI_GENAI,
    PROVIDER_LITELLM,
    PROVIDER_OLLAMA,
    PROVIDER_MOCK,
]

# UI Theme names
THEME_DEFAULT = "default"
THEME_DARK = "dark"
THEME_LIGHT = "light"
THEME_MINIMAL = "minimal"
THEME_VIBRANT = "vibrant"

# Available themes
AVAILABLE_THEMES = [
    THEME_DEFAULT,
    THEME_DARK,
    THEME_LIGHT,
    THEME_MINIMAL,
    THEME_VIBRANT,
]

# Developer modes
MODE_GENERAL = "general"
MODE_CODE = "code"
MODE_DEBUG = "debug"
MODE_EXPLAIN = "explain"
MODE_REVIEW = "review"
MODE_REFACTOR = "refactor"
MODE_PLAN = "plan"

# Available modes
AVAILABLE_MODES = [
    MODE_GENERAL,
    MODE_CODE,
    MODE_DEBUG,
    MODE_EXPLAIN,
    MODE_REVIEW,
    MODE_REFACTOR,
    MODE_PLAN,
]

# Export formats
EXPORT_FORMAT_JSON = "json"
EXPORT_FORMAT_MARKDOWN = "markdown"
EXPORT_FORMAT_TXT = "txt"
EXPORT_FORMAT_HTML = "html"

# Available export formats
AVAILABLE_EXPORT_FORMATS = [
    EXPORT_FORMAT_JSON,
    EXPORT_FORMAT_MARKDOWN,
    EXPORT_FORMAT_TXT,
    EXPORT_FORMAT_HTML,
]

# Message roles
ROLE_USER = "user"
ROLE_ASSISTANT = "assistant"
ROLE_SYSTEM = "system"
ROLE_TOOL = "tool"

# Session status values
SESSION_STATUS_ACTIVE = "active"
SESSION_STATUS_ARCHIVED = "archived"
SESSION_STATUS_DELETED = "deleted"

# Error messages
ERROR_COMPARTMENT_ID_MISSING = "OCI compartment ID not configured"
ERROR_PROVIDER_NOT_FOUND = "Provider '{provider}' not found"
ERROR_MODEL_NOT_FOUND = "Model '{model}' not found"
ERROR_SESSION_NOT_FOUND = "Session '{session}' not found"
ERROR_INVALID_EXPORT_FORMAT = "Invalid export format: {format}"

# Help text constants
HELP_COMPARTMENT_ID = """Please set it via one of these methods:
1. Environment variable: export OCI_COMPARTMENT_ID='your-compartment-id'
2. Coda config file: ~/.config/coda/config.toml"""

# Prompt toolkit styles - will be moved to theme config later
PROMPT_STYLE_SELECTED = "bg:#00aa00 #ffffff bold"
PROMPT_STYLE_SEARCH = "bg:#444444 #ffffff"
PROMPT_STYLE_TITLE = "#00aa00 bold"

# Console output styles
CONSOLE_STYLE_SUCCESS = "[green]"
CONSOLE_STYLE_ERROR = "[red]"
CONSOLE_STYLE_WARNING = "[yellow]"
CONSOLE_STYLE_INFO = "[cyan]"
CONSOLE_STYLE_DIM = "[dim]"
CONSOLE_STYLE_BOLD = "[bold]"

# Panel styles
PANEL_BORDER_STYLE = "cyan"
PANEL_TITLE_STYLE = "bold"

# Coming soon markers
COMING_SOON = "(Coming soon)"
NOT_IMPLEMENTED = "Not implemented yet"