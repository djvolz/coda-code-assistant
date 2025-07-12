"""Constants for the session module.

All session-specific constants are defined here to make the module self-contained.
"""

# Session status values
STATUS_ACTIVE: str = "active"
STATUS_ARCHIVED: str = "archived"
STATUS_DELETED: str = "deleted"

# Session naming patterns
AUTO_PREFIX: str = "auto-"
AUTO_DATE_FORMAT: str = "%Y%m%d-%H%M%S"

# Database constants
FTS_TABLE_NAME: str = "messages_fts"
FTS_CONTENT_TABLE: str = "messages"

# Message role identifiers
ROLE_USER: str = "user"
ROLE_ASSISTANT: str = "assistant"
ROLE_SYSTEM: str = "system"
ROLE_TOOL: str = "tool"

# Session limits
LIMIT_LIST: int = 50
LIMIT_SEARCH: int = 10
LIMIT_DELETE: int = 1000
LIMIT_INFO: int = 100
LIMIT_LAST: int = 1

# Default values
DEFAULT_EXPORT_LIMIT: int = 50
DEFAULT_MAX_HISTORY: int = 1000

# File names
SESSION_DB: str = "sessions.db"
HISTORY_FILE: str = "history.txt"

# Note: SESSION_DB_PATH should be computed at runtime based on XDG paths
# It's not a constant but a computed value
