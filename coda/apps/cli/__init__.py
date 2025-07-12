"""🔗 APP MODULE
Coda CLI - Command line interface and interactive mode.

This module provides the user interface and coordinates between all Coda modules.
Requires: coda.base.config, coda.base.theme, coda.base.providers, coda.base.search, coda.base.session, coda.services.agents
"""

from .main import main

__all__ = ["main"]
