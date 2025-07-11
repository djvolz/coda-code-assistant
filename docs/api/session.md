# Session Module API Reference

## Overview

The Session module provides conversation management with persistence, branching, and history tracking. It enables stateful interactions with AI providers while maintaining conversation context.

## Installation

The Session module requires SQLAlchemy for persistence:

```bash
pip install coda-assistant[session]
```

## Quick Start

```python
from coda.base.session import SessionManager

# Create session manager
manager = SessionManager({"session": {"storage_path": "~/.coda/sessions"}})

# Create or load a session
session = manager.create_session("my-chat")

# Add messages
session.add_message({"role": "user", "content": "Hello!"})
session.add_message({"role": "assistant", "content": "Hi there!"})

# Get conversation history
messages = session.get_messages()

# Save session
manager.save_session(session)
```

## API Reference

### SessionManager Class

```python
class SessionManager:
    """Manages session lifecycle and persistence."""
    
    def __init__(self, config: dict[str, Any]):
        """
        Initialize session manager.
        
        Args:
            config: Configuration dictionary with session settings
        """
```

#### Methods

##### create_session(name: str, branch_from: str | None = None) -> Session

Create a new session or load existing one.

```python
# New session
session = manager.create_session("project-chat")

# Branch from existing session
branch = manager.create_session("project-chat-v2", branch_from="project-chat")
```

##### save_session(session: Session) -> None

Save session to persistent storage.

```python
manager.save_session(session)
```

##### delete_session(name: str) -> None

Delete a session.

```python
manager.delete_session("old-chat")
```

##### list_sessions() -> list[SessionInfo]

List all available sessions.

```python
sessions = manager.list_sessions()
for session_info in sessions:
    print(f"{session_info.name}: {session_info.message_count} messages")
```

##### get_session_info(name: str) -> SessionInfo | None

Get metadata about a session without loading messages.

```python
info = manager.get_session_info("my-chat")
if info:
    print(f"Created: {info.created_at}")
    print(f"Updated: {info.updated_at}")
```

### Session Class

```python
class Session:
    """Represents a conversation session."""
    
    def __init__(
        self,
        name: str,
        messages: list[dict[str, Any]] | None = None,
        metadata: dict[str, Any] | None = None
    ):
        """
        Initialize a session.
        
        Args:
            name: Unique session identifier
            messages: Initial message list
            metadata: Session metadata
        """
```

#### Properties

- `name: str` - Session identifier
- `messages: list[dict]` - Conversation messages
- `metadata: dict` - Session metadata
- `created_at: datetime` - Creation timestamp
- `updated_at: datetime` - Last update timestamp

#### Methods

##### add_message(message: dict[str, Any]) -> None

Add a message to the session.

```python
session.add_message({
    "role": "user",
    "content": "What is Python?",
    "timestamp": datetime.now().isoformat()
})
```

##### get_messages(limit: int | None = None) -> list[dict[str, Any]]

Get conversation messages.

```python
# Get all messages
all_messages = session.get_messages()

# Get last 10 messages
recent = session.get_messages(limit=10)
```

##### clear_messages() -> None

Clear all messages from the session.

```python
session.clear_messages()
```

##### update_metadata(metadata: dict[str, Any]) -> None

Update session metadata.

```python
session.update_metadata({
    "topic": "Python programming",
    "model": "gpt-4",
    "tags": ["tutorial", "basics"]
})
```

##### get_token_count() -> int

Get approximate token count for the session.

```python
tokens = session.get_token_count()
if tokens > 3000:
    print("Approaching context limit")
```

##### truncate_messages(max_messages: int) -> None

Keep only the most recent messages.

```python
# Keep last 50 messages
session.truncate_messages(50)
```

### SessionInfo Class

```python
@dataclass
class SessionInfo:
    """Session metadata without loading full messages."""
    name: str
    message_count: int
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]
    size_bytes: int
```

## Storage Backends

### SQLite Backend (Default)

```python
config = {
    "session": {
        "backend": "sqlite",
        "storage_path": "~/.coda/sessions",
        "connection_pool_size": 5
    }
}
```

### In-Memory Backend

```python
config = {
    "session": {
        "backend": "memory"
    }
}
# Note: Sessions are lost when program exits
```

## Examples

### Basic Conversation Management

```python
from coda.base.session import SessionManager
from coda.base.providers import ProviderFactory

# Initialize
manager = SessionManager(config)
factory = ProviderFactory(config)
provider = factory.create("openai")

# Create session
session = manager.create_session("coding-help")

# Interactive chat
while True:
    user_input = input("You: ")
    if user_input.lower() == "quit":
        break
    
    # Add user message
    session.add_message({"role": "user", "content": user_input})
    
    # Get AI response
    response = provider.chat(
        messages=session.get_messages(),
        model="gpt-4"
    )
    
    # Add assistant message
    session.add_message({
        "role": "assistant",
        "content": response.content,
        "model": "gpt-4"
    })
    
    print(f"AI: {response.content}")

# Save on exit
manager.save_session(session)
```

### Session Branching

```python
# Load existing session
main_session = manager.create_session("main-project")

# Create a branch to explore different approach
branch_session = manager.create_session(
    "main-project-experiment",
    branch_from="main-project"
)

# Branch has all messages from parent
print(f"Branch has {len(branch_session.get_messages())} messages")

# Add experimental messages to branch
branch_session.add_message({
    "role": "user",
    "content": "Let's try a different approach..."
})

# Save both independently
manager.save_session(main_session)
manager.save_session(branch_session)
```

### Session Search and Filter

```python
def find_sessions_by_topic(manager: SessionManager, topic: str) -> list[str]:
    """Find sessions related to a topic."""
    matching = []
    
    for session_info in manager.list_sessions():
        # Check metadata
        if topic.lower() in session_info.metadata.get("topic", "").lower():
            matching.append(session_info.name)
            continue
        
        # Check recent messages (expensive)
        session = manager.create_session(session_info.name)
        for msg in session.get_messages(limit=10):
            if topic.lower() in msg.get("content", "").lower():
                matching.append(session_info.name)
                break
    
    return matching

# Find all Python-related sessions
python_sessions = find_sessions_by_topic(manager, "python")
```

### Session Templates

```python
class TemplateSession:
    """Pre-configured session templates."""
    
    @staticmethod
    def code_review(manager: SessionManager, name: str) -> Session:
        """Create a code review session."""
        session = manager.create_session(name)
        
        session.add_message({
            "role": "system",
            "content": "You are an expert code reviewer. Analyze code for bugs, security issues, performance, and style."
        })
        
        session.update_metadata({
            "template": "code_review",
            "created_from_template": True
        })
        
        return session
    
    @staticmethod
    def tutoring(manager: SessionManager, name: str, subject: str) -> Session:
        """Create a tutoring session."""
        session = manager.create_session(name)
        
        session.add_message({
            "role": "system",
            "content": f"You are a patient and knowledgeable tutor for {subject}. Use the Socratic method when appropriate."
        })
        
        session.update_metadata({
            "template": "tutoring",
            "subject": subject
        })
        
        return session

# Use templates
review_session = TemplateSession.code_review(manager, "pr-123-review")
tutor_session = TemplateSession.tutoring(manager, "python-basics", "Python")
```

### Session Export/Import

```python
import json
from pathlib import Path

def export_session(session: Session, path: Path) -> None:
    """Export session to JSON file."""
    data = {
        "name": session.name,
        "messages": session.get_messages(),
        "metadata": session.metadata,
        "created_at": session.created_at.isoformat(),
        "updated_at": session.updated_at.isoformat()
    }
    
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def import_session(manager: SessionManager, path: Path) -> Session:
    """Import session from JSON file."""
    with open(path) as f:
        data = json.load(f)
    
    session = manager.create_session(data["name"])
    session.messages = data["messages"]
    session.update_metadata(data["metadata"])
    
    manager.save_session(session)
    return session

# Export for sharing
export_session(session, Path("session-export.json"))

# Import on another machine
imported = import_session(manager, Path("session-export.json"))
```

## Advanced Usage

### Custom Storage Backend

```python
from coda.base.session import SessionStorage

class CustomStorage(SessionStorage):
    """Custom session storage implementation."""
    
    def save(self, session: Session) -> None:
        """Save session to custom backend."""
        # Implement your storage logic
        pass
    
    def load(self, name: str) -> Session | None:
        """Load session from custom backend."""
        # Implement your retrieval logic
        pass
    
    def delete(self, name: str) -> None:
        """Delete session from custom backend."""
        # Implement your deletion logic
        pass
    
    def list_all(self) -> list[SessionInfo]:
        """List all sessions."""
        # Implement your listing logic
        pass

# Use custom storage
manager = SessionManager(config, storage=CustomStorage())
```

### Session Middleware

```python
class SessionMiddleware:
    """Add automatic behaviors to sessions."""
    
    def __init__(self, session: Session):
        self.session = session
    
    def add_message(self, message: dict) -> None:
        """Add message with automatic enhancements."""
        # Add timestamp
        if "timestamp" not in message:
            message["timestamp"] = datetime.now().isoformat()
        
        # Add token count estimate
        message["token_estimate"] = len(message["content"]) // 4
        
        # Detect language for code blocks
        if "```" in message["content"]:
            message["has_code"] = True
        
        self.session.add_message(message)

# Use middleware
session = manager.create_session("enhanced-chat")
enhanced = SessionMiddleware(session)
enhanced.add_message({"role": "user", "content": "Show me Python code"})
```

### Session Analytics

```python
from collections import Counter
from datetime import datetime, timedelta

class SessionAnalytics:
    """Analyze session usage patterns."""
    
    def __init__(self, manager: SessionManager):
        self.manager = manager
    
    def get_statistics(self) -> dict:
        """Get overall session statistics."""
        sessions = self.manager.list_sessions()
        
        total_messages = sum(s.message_count for s in sessions)
        total_size = sum(s.size_bytes for s in sessions)
        
        # Find most active sessions
        active_sessions = sorted(
            sessions,
            key=lambda s: s.updated_at,
            reverse=True
        )[:5]
        
        return {
            "total_sessions": len(sessions),
            "total_messages": total_messages,
            "total_size_mb": total_size / 1024 / 1024,
            "active_sessions": [s.name for s in active_sessions]
        }
    
    def get_activity_timeline(self, days: int = 7) -> dict:
        """Get session activity over time."""
        cutoff = datetime.now() - timedelta(days=days)
        sessions = self.manager.list_sessions()
        
        daily_activity = Counter()
        for session in sessions:
            if session.updated_at > cutoff:
                day = session.updated_at.date()
                daily_activity[day] += session.message_count
        
        return dict(daily_activity)

# Analyze usage
analytics = SessionAnalytics(manager)
stats = analytics.get_statistics()
print(f"Total sessions: {stats['total_sessions']}")
print(f"Storage used: {stats['total_size_mb']:.1f} MB")
```

## Performance Considerations

1. **Lazy Loading**: Messages are loaded only when accessed
2. **Message Limits**: Use `get_messages(limit=n)` for large sessions
3. **Indexing**: Session names and metadata are indexed for fast lookup
4. **Connection Pooling**: SQLite backend uses connection pooling
5. **Truncation**: Regularly truncate old messages to manage size

## Error Handling

```python
from coda.base.session import SessionError, SessionNotFoundError

try:
    session = manager.create_session("my-chat")
except SessionError as e:
    print(f"Session error: {e}")
    # Handle storage errors, corruption, etc.

try:
    session = manager.load_session("nonexistent")
except SessionNotFoundError:
    print("Session not found")
    # Create new session or handle missing session
```

## Configuration Options

```toml
[session]
# Storage backend: "sqlite" or "memory"
backend = "sqlite"

# Storage location for SQLite
storage_path = "~/.coda/sessions"

# Maximum messages to keep in memory
message_cache_size = 1000

# Auto-save interval in seconds (0 = disabled)
autosave_interval = 300

# Connection pool size for SQLite
connection_pool_size = 5

# Enable compression for large messages
compress_messages = true

# Maximum session size in MB
max_session_size = 100
```

## See Also

- [Integration Guide](../integration-guide.md) - Using sessions with providers
- [Example: Session Manager](../../tests/examples/session_manager/) - Full session management example
- [Session Best Practices](../guides/session-best-practices.md) - Tips for effective session management