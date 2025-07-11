"""🔗 APP MODULE
Coda CLI - Command line interface and interactive mode.

This module provides the user interface and coordinates between all Coda modules.
Requires: coda.config, coda.theme, coda.providers, coda.search, coda.session, coda.agents
"""

from .main import main

__all__ = ["main"]
