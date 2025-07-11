"""🔧 BASE MODULE
Session management module for Coda.

This module provides session and conversation management with zero Coda dependencies.
Can be copy-pasted to any project for session handling.
"""

from .context import ContextManager, ContextWindow
from .database import SessionDatabase
from .manager import SessionManager
from .models import Message, Session

__all__ = [
    "SessionDatabase",
    "SessionManager",
    "Session",
    "Message",
    "ContextManager",
    "ContextWindow",
]
