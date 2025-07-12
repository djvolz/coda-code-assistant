# Session Manager Example

Demonstrates persistent conversation management using Coda's session module.

## Features

- **Session Persistence**: Save and resume conversations
- **Multiple Sessions**: Manage multiple independent conversations
- **Session Branching**: Create new sessions from existing ones
- **History Viewing**: Browse conversation history
- **Statistics**: View session metrics and usage
- **Export**: Save sessions to JSON format

## Prerequisites

- Python 3.8+
- Coda modules installed
- At least one AI provider configured
- Write permissions for session storage

## Setup

1. Install Coda:
   ```bash
   pip install -e ../..
   ```

2. Configure your AI provider (see simple-chatbot example)

## Usage

Run the session manager:

```bash
python session_demo.py
```

### Main Menu Options

1. **List sessions** - Show all saved sessions
2. **Start/resume session** - Begin new or continue existing session
3. **Branch session** - Create a copy of an existing session
4. **Delete session** - Remove a session (conceptual)
5. **Quit** - Exit the application

### Session Commands

While in a session:
- `quit` - Save and exit session
- `history` - Show full conversation history
- `save` - Manually save session
- `stats` - Display session statistics
- `export` - Export session to JSON file
- `clear` - Clear session (with confirmation)

## Example Usage

### Creating a New Session

```
=== Session Manager Demo ===
1. List sessions
2. Start/resume session
3. Branch session
4. Delete session
5. Quit

Choice: 2
Session name: project-planning

Session 'project-planning' loaded with 0 messages

Commands:
  'quit' - Save and exit session
  'history' - Show conversation history
  'save' - Save session
  'stats' - Show session statistics
  'export' - Export session to JSON
  'clear' - Clear session (requires confirmation)

You: Let's plan a web application for task management
Assistant: I'd be happy to help you plan a web application for task management! Let's break this down into key components and considerations.

## Core Features for Task Management App:

### 1. **User Management**
- User registration/login
- Profile management
- Role-based access (admin, user, team lead)

### 2. **Task Operations**
- Create, read, update, delete tasks
- Task properties:
  - Title and description
  - Priority levels (High, Medium, Low)
  - Status (To Do, In Progress, Done)
  - Due dates
  - Tags/labels
  - Attachments

### 3. **Organization Features**
- Projects or categories
- Team/workspace management
- Task assignment to users
- Subtasks

### 4. **Collaboration**
- Comments on tasks
- Activity logs
- Notifications
- Real-time updates

Would you like me to elaborate on the technical stack, architecture, or any specific feature?

[Tokens: 325]

You: stats

--- Session Statistics ---
Total messages: 2
User messages: 1
Assistant messages: 1
User characters: 49
Assistant characters: 923
Avg user message: 49 chars
Avg assistant message: 923 chars

Models used:
  gpt-4: 1 responses
--- End Statistics ---

You: quit
Saving session...
Session 'project-planning' saved.
```

### Resuming a Session

```
Choice: 2
Session name: project-planning

Session 'project-planning' loaded with 2 messages

Last 3 messages:
  User: Let's plan a web application for task management
  Assistant: I'd be happy to help you plan a web application for task management! Let...

You: Let's focus on the technical architecture
Assistant: Excellent! Let's design a robust technical architecture for the task management application...
```

### Branching Sessions

Create a copy of an existing session to explore different directions:

```
Choice: 3
Source session name: project-planning
Target session name: project-planning-mobile

Created branch 'project-planning-mobile' from 'project-planning'
Copied 4 messages
```

## Session Storage

Sessions are stored in the default Coda session directory:
- Linux/Mac: `~/.local/share/coda/sessions/`
- Windows: `%APPDATA%/coda/sessions/`

Each session is saved as a JSON file with the session name.

## How It Works

1. **SessionManager**: Handles session creation, loading, and persistence
2. **Session Objects**: Contain conversation messages and metadata
3. **Message Format**: Each message includes role, content, and optional metadata
4. **Auto-save**: Sessions are automatically saved on exit

## Extending the Example

### 1. Add Search Functionality
```python
def search_sessions(self, query: str):
    sessions = self.session_manager.list_sessions()
    results = []
    for session in sessions:
        # Load and search session content
        s = self.session_manager.create_session(session["name"])
        for msg in s.get_messages():
            if query.lower() in msg["content"].lower():
                results.append(session["name"])
                break
    return results
```

### 2. Session Templates
```python
def create_from_template(self, name: str, template: str):
    session = self.session_manager.create_session(name)
    
    templates = {
        "code_review": [
            {"role": "system", "content": "You are a code reviewer..."},
            {"role": "user", "content": "Please review the following code:"}
        ],
        "brainstorm": [
            {"role": "system", "content": "You are a creative assistant..."},
            {"role": "user", "content": "Let's brainstorm ideas for:"}
        ]
    }
    
    if template in templates:
        for msg in templates[template]:
            session.add_message(msg)
```

### 3. Session Merging
```python
def merge_sessions(self, session_names: list, target_name: str):
    target = self.session_manager.create_session(target_name)
    
    for name in session_names:
        source = self.session_manager.create_session(name)
        target.messages.extend(source.get_messages())
    
    self.session_manager.save_session(target)
```

## Best Practices

1. **Session Naming**: Use descriptive names that indicate the purpose
2. **Regular Saves**: The demo auto-saves, but manual saves ensure no data loss
3. **Branching**: Use branches to explore different conversation paths
4. **Exports**: Export important sessions for backup or sharing
5. **Clean Up**: Periodically review and remove old sessions

## Troubleshooting

### Sessions not saving
- Check write permissions on session directory
- Ensure sufficient disk space
- Verify session names don't contain invalid characters

### Can't load session
- Check if session file exists in session directory
- Verify JSON file is not corrupted
- Ensure session name matches exactly (case-sensitive)

### Performance issues
- Large sessions may load slowly
- Consider implementing pagination for history viewing
- Archive old sessions to reduce directory size