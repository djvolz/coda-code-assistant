# Session Module

The Session module provides conversation management with persistence, branching, and history tracking.

## Features

- 💾 **Persistent Storage**: Save and resume conversations
- 🌳 **Session Branching**: Create alternative conversation paths
- 📜 **History Management**: Track and search conversation history
- 🗄️ **Multiple Backends**: SQLite (default) or in-memory storage
- 🔍 **Metadata Support**: Tag and organize sessions

## Quick Start

```python
from coda.base.session import SessionManager

# Initialize session manager
manager = SessionManager({
    "session": {
        "storage_path": "~/.coda/sessions"
    }
})

# Create or load a session
session = manager.create_session("my-chat")

# Add messages
session.add_message({"role": "user", "content": "Hello!"})
session.add_message({"role": "assistant", "content": "Hi there!"})

# Save session
manager.save_session(session)

# List all sessions
for session_info in manager.list_sessions():
    print(f"{session_info.name}: {session_info.message_count} messages")
```

## Session Management

### Creating Sessions

```python
# New session
session = manager.create_session("project-discussion")

# Branch from existing session
branch = manager.create_session(
    "project-discussion-v2",
    branch_from="project-discussion"
)
```

### Working with Messages

```python
# Add messages with metadata
session.add_message({
    "role": "user",
    "content": "What is Python?",
    "timestamp": datetime.now().isoformat(),
    "model": "gpt-4"
})

# Get messages
all_messages = session.get_messages()
recent_messages = session.get_messages(limit=10)

# Clear or truncate
session.clear_messages()
session.truncate_messages(max_messages=50)
```

### Session Metadata

```python
# Update metadata
session.update_metadata({
    "topic": "Python programming",
    "tags": ["tutorial", "basics"],
    "model": "gpt-4"
})

# Access metadata
print(session.metadata)
```

## Storage Backends

### SQLite (Default)

```python
config = {
    "session": {
        "backend": "sqlite",
        "storage_path": "~/.coda/sessions",
        "connection_pool_size": 5
    }
}
```

### In-Memory

```python
config = {
    "session": {
        "backend": "memory"
    }
}
# Note: Sessions are lost when program exits
```

## Advanced Features

### Session Templates

```python
# Create a code review session
session = manager.create_session("code-review")
session.add_message({
    "role": "system",
    "content": "You are an expert code reviewer."
})
```

### Export/Import

```python
import json

# Export session
data = {
    "messages": session.get_messages(),
    "metadata": session.metadata
}
with open("session-backup.json", "w") as f:
    json.dump(data, f)

# Import session
with open("session-backup.json") as f:
    data = json.load(f)
imported = manager.create_session("imported")
for msg in data["messages"]:
    imported.add_message(msg)
```

### Session Search

```python
# Find sessions by metadata
python_sessions = [
    s for s in manager.list_sessions()
    if "python" in s.metadata.get("topic", "").lower()
]
```

## Configuration

```toml
[session]
# Storage backend: "sqlite" or "memory"
backend = "sqlite"

# Storage location for SQLite
storage_path = "~/.coda/sessions"

# Auto-save interval in seconds (0 = disabled)
autosave_interval = 300

# Maximum session size in MB
max_session_size = 100

# Enable compression for large messages
compress_messages = true
```

## Database Schema

The SQLite backend uses the following schema:

```sql
-- Sessions table
CREATE TABLE sessions (
    id TEXT PRIMARY KEY,
    name TEXT UNIQUE NOT NULL,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    metadata JSON
);

-- Messages table
CREATE TABLE messages (
    id INTEGER PRIMARY KEY,
    session_id TEXT,
    role TEXT,
    content TEXT,
    timestamp TIMESTAMP,
    metadata JSON,
    FOREIGN KEY (session_id) REFERENCES sessions(id)
);
```

## API Documentation

For detailed API documentation, see [Session API Reference](../../../docs/api/session.md).

## Examples

- [Session Manager Demo](../../../tests/examples/session_manager/) - Full featured example
- [Session Tests](../../../tests/base/session/) - Test implementations

## Performance Tips

1. Use `get_messages(limit=n)` for large sessions
2. Regularly truncate old messages
3. Use in-memory backend for temporary sessions
4. Enable compression for long conversations