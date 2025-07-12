# Session Management Testing Guide

## Quick Manual Test

You can now test the session management functionality with the new **mock provider**:

### 1. Start CLI with Mock Provider

```bash
uv run coda --provider mock
```

Select model `1` (mock-echo) when prompted.

### 2. Test the Complete Workflow

```bash
# Start conversation
Hello, can you help me with Python?

# Continue conversation  
What are decorators in Python?

# Save the session
/session save "Python Tutorial"
# (Press Enter for empty description)

# Add more to conversation
Can you show me decorator examples?

# List sessions to verify save
/session list

# Clear conversation
/clear

# Verify AI has no memory
What were we discussing?
# Should respond that no previous conversation exists

# Load the saved session
/session load "Python Tutorial"
# Should see: "Restored X messages to conversation history"

# Test that AI remembers the context
What were we discussing about decorators?
# Should reference the previous Python/decorator conversation!

# Test session info
/session info

# Test export
/export markdown

# Test search
/session search "Python"
```

### 3. Test Session Branching

```bash
# In the loaded session, create a branch
/session branch "Advanced Python"

# Continue with advanced topics
Tell me about metaclasses in Python

# Switch back to original
/session load "Python Tutorial"

# Verify original conversation is intact
/session info
```

## Automated Tests

### Run Comprehensive Tests

```bash
# Run all session tests
uv run python -m pytest tests/session/ -v

# Run specific integration test  
uv run python -c "
from tests.integration.test_session_integration import TestSessionEndToEnd
test = TestSessionEndToEnd()
test.test_complete_session_lifecycle()
print('✅ Integration test passed!')
"
```

### Test Mock Provider

```bash
# Test mock provider directly
uv run python -c "
from coda.providers import MockProvider, Message, Role

provider = MockProvider()
messages = [
    Message(role=Role.USER, content='What is Python?'),
    Message(role=Role.ASSISTANT, content='Python is a programming language'),
    Message(role=Role.USER, content='What were we discussing?')
]

response = provider.chat(messages, 'mock-echo')
print(f'Response: {response}')
assert 'python' in response.lower()
print('✅ Mock provider context test passed!')
"
```

## Expected Behavior

### ✅ Session Save/Load
- **Save**: `/session save "name"` stores conversation in SQLite database
- **Load**: `/session load "name"` restores conversation AND makes it available to AI
- **Verification**: AI remembers previous conversation after loading

### ✅ Context Continuity  
- **Before Load**: AI has no memory of previous conversations
- **After Load**: AI can reference and continue previous conversations
- **Branching**: Create conversation branches from any point

### ✅ Session Management
- **List**: View all saved sessions with metadata
- **Search**: Full-text search across all conversations  
- **Export**: Export sessions in JSON, Markdown, HTML, or text format
- **Info**: View detailed session information

### ✅ Mock Provider Features
- **Context Awareness**: Remembers conversation history
- **Topic Recognition**: Recognizes Python, JavaScript, decorators, etc.
- **Memory Questions**: Responds appropriately to "what were we discussing"
- **Conversation Flow**: Maintains context across multiple turns

## Troubleshooting

### If Session Loading Doesn't Work
1. Verify session was saved: `/session list`
2. Check for error messages during load
3. Verify database exists: `~/.cache/coda/sessions.db`
4. Try with a fresh session

### If AI Doesn't Remember Context
1. Look for "Restored X messages to conversation history" message
2. Verify the session contains the expected messages: `/session info`
3. Check that you're using a conversation-aware provider (mock, oci_genai, etc.)

### Mock Provider Benefits
- **No External Dependencies**: Works offline, no API keys needed
- **Predictable Responses**: Consistent behavior for testing
- **Context Demonstration**: Clearly shows memory working
- **Fast Testing**: Immediate responses for rapid iteration

The mock provider is perfect for:
- ✅ Testing session management features
- ✅ Validating conversation continuity
- ✅ Demonstrating the fix for session loading
- ✅ CI/CD testing without external services
- ✅ Development and debugging

---

**Result**: You now have comprehensive testing for the session management fix, including a mock provider that demonstrates conversation continuity working correctly! 🎯