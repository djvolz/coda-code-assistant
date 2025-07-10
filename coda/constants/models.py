"""Data models for constants module.

This module contains enums and data classes related to constants.
Zero dependencies - uses only Python standard library.
"""

from enum import Enum
from typing import NamedTuple


class ProviderType(str, Enum):
    """Provider type enumeration."""

    OCI_GENAI = "oci_genai"
    LITELLM = "litellm"
    OLLAMA = "ollama"
    MOCK = "mock"
    OPENAI = "openai"


class ThemeType(str, Enum):
    """Theme type enumeration."""

    DEFAULT = "default"
    DARK = "dark"
    LIGHT = "light"
    MINIMAL = "minimal"
    VIBRANT = "vibrant"
    MONOKAI_DARK = "monokai_dark"
    MONOKAI_LIGHT = "monokai_light"
    DRACULA_DARK = "dracula_dark"
    DRACULA_LIGHT = "dracula_light"
    GRUVBOX_DARK = "gruvbox_dark"
    GRUVBOX_LIGHT = "gruvbox_light"


class DeveloperMode(str, Enum):
    """Developer mode enumeration."""

    GENERAL = "general"
    CODE = "code"
    DEBUG = "debug"
    EXPLAIN = "explain"
    REVIEW = "review"
    REFACTOR = "refactor"
    PLAN = "plan"


class ExportFormat(str, Enum):
    """Export format enumeration."""

    JSON = "json"
    MARKDOWN = "markdown"
    TXT = "txt"
    HTML = "html"


class MessageRole(str, Enum):
    """Message role enumeration."""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class SessionStatus(str, Enum):
    """Session status enumeration."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


class ContextStrategy(str, Enum):
    """Context management strategy."""

    AGGRESSIVE = "aggressive"
    BALANCED = "balanced"
    CONSERVATIVE = "conservative"


class PathConfig(NamedTuple):
    """Configuration for XDG-compliant paths."""

    config_dir: str = ".config"
    data_dir: str = ".local/share"
    cache_dir: str = ".cache"
    app_name: str = "coda"


class LimitConfig(NamedTuple):
    """Configuration for various system limits."""

    session_list: int = 50
    session_search: int = 10
    session_delete: int = 1000
    session_info: int = 100
    session_last: int = 1
    export_default: int = 50
    max_models_display: int = 20
    max_models_basic: int = 10
