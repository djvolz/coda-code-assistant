"""Standalone constants module for Coda.

This module provides all constants used throughout Coda, organized by category.
It has zero dependencies and can be copy-pasted into any project.

Example usage:
    from coda.constants import UI, API, DEFAULTS, PROVIDERS

    print(UI.MAX_LINE_LENGTH)
    print(API.TIMEOUT)
    print(DEFAULTS.THEME)
"""

from .definitions import (
    # API and network constants
    API,
    # Core metadata
    APP,
    # Default values
    DEFAULTS,
    # Environment variables
    ENV,
    # Error messages
    ERRORS,
    # Export formats
    EXPORT,
    # File system constants
    FILES,
    # System limits
    LIMITS,
    # Developer modes
    MODES,
    # Observability constants
    OBSERVABILITY,
    # Provider constants
    PROVIDERS,
    # Message roles
    ROLES,
    # Session constants
    SESSION,
    # Theme constants
    THEMES,
    # UI constants
    UI,
)

__all__ = [
    "APP",
    "UI",
    "API",
    "DEFAULTS",
    "LIMITS",
    "PROVIDERS",
    "THEMES",
    "MODES",
    "EXPORT",
    "ROLES",
    "SESSION",
    "ERRORS",
    "FILES",
    "ENV",
    "OBSERVABILITY",
]
