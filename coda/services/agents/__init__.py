"""🔗 SERVICE MODULE
Coda Agent System - AI agents with tool calling capabilities.

This module coordinates between providers and search modules to create AI agents.
Requires: coda.providers, coda.search
"""

from .agent import Agent
from .agent_types import FunctionCall, PerformedAction, RequiredAction
from .decorators import tool
from .function_tool import FunctionTool

__all__ = [
    "Agent",
    "tool",
    "FunctionTool",
    "RequiredAction",
    "PerformedAction",
    "FunctionCall",
]
