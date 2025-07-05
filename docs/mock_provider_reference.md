# Mock Provider Reference for Coding Agents

This document describes the MockProvider's behavior patterns for automated testing and AI agent reference.

## Overview

The MockProvider (`coda.providers.MockProvider`) is a test provider that simulates realistic AI assistant behavior without external API dependencies. It provides predictable, context-aware responses based on pattern matching and conversation history.

## Models Available

- `mock-echo`: Context-aware responses with fallback echoing
- `mock-smart`: Same behavior as mock-echo (alias for testing)

## Response Patterns

The MockProvider processes messages in the following priority order:

### 1. Memory Questions (Highest Priority)

**Triggers**: "what were we discussing", "talking about"
**Behavior**: Analyzes previous messages (excluding current) for topics

```python
# Single message - no context
messages = [Message(role=Role.USER, content="What were we discussing?")]
# Response: "I don't see any previous conversation to reference."

# With conversation history
messages = [
    Message(role=Role.USER, content="What is Python?"),
    Message(role=Role.ASSISTANT, content="Python is a language"),
    Message(role=Role.USER, content="What were we discussing?")
]
# Response: "We were discussing: Python programming. What would you like to know more about?"
```

### 2. Programming Topics

**Python Questions**:
```python
# Basic Python question
Message(content="What is Python?")
# Response: "Python is a high-level programming language known for its simplicity and readability."

# Python with decorator context
messages = [
    Message(content="Tell me about decorators"),
    Message(content="What is Python?")
]
# Response: "Yes, we were discussing Python decorators. They are functions that modify other functions, using the @decorator syntax."
```

**JavaScript Questions**:
```python
Message(content="Tell me about JavaScript")
# Response: "JavaScript is a dynamic programming language primarily used for web development."
```

**Decorator Questions**:
```python
# Single message
Message(content="What are decorators?")
# Response: "Decorators in Python are a way to modify functions using the @ syntax. For example: @property or @staticmethod."

# With previous decorator context
messages = [
    Message(content="Tell me about decorators"),
    Message(content="What are Python decorators?")
]
# Response: "Yes, we were discussing Python decorators. They are functions that modify other functions, using the @decorator syntax."
```

### 3. Greetings and Help

```python
Message(content="Hello")
# Response: "Hello! How can I help you today?"

Message(content="Help me")
# Response: "I'm a mock AI assistant. I can help you test session management features."
```

### 4. Echo Fallback (Lowest Priority)

For unrecognized input, provides contextual echo:

```python
# Single message
Message(content="The weather is nice")
# Response: "You said: 'The weather is nice'"

# In conversation
messages = [
    Message(content="First question"),
    Message(content="Random input")  # Current message
]
# Response: "You said: 'Random input' This is message #2 in our conversation. Earlier you asked about: 'First question...'"
```

## Topic Recognition

The MockProvider recognizes these topics in conversation history:

- **"python"** → "Python programming"
- **"decorator"** → "Python decorators" 
- **"javascript"** → "JavaScript"

## Testing Patterns

### Test Conversation Continuity

```python
def test_session_memory():
    provider = MockProvider()
    
    # Build conversation
    messages = [
        Message(role=Role.USER, content="What is Python?"),
        Message(role=Role.ASSISTANT, content="Python is a language"),
        Message(role=Role.USER, content="Tell me about decorators"),
        Message(role=Role.ASSISTANT, content="Decorators modify functions")
    ]
    
    # Test memory
    messages.append(Message(role=Role.USER, content="What were we discussing?"))
    response = provider.chat(messages, "mock-echo")
    
    # Should reference previous topics
    assert "Python" in response or "decorator" in response
```

### Test Memory Isolation

```python
def test_no_false_memory():
    provider = MockProvider()
    
    # Single message with topic keywords but no context
    messages = [Message(role=Role.USER, content="What were we discussing about Python?")]
    response = provider.chat(messages, "mock-echo")
    
    # Should NOT assume context from keywords in current message
    assert "I don't see any previous conversation" in response
```

### Test Context Awareness

```python
def test_context_building():
    provider = MockProvider()
    
    # Progressive conversation
    msg1 = [Message(role=Role.USER, content="What is Python?")]
    response1 = provider.chat(msg1, "mock-echo")
    assert "high-level programming language" in response1
    
    # Add context about decorators
    msg2 = msg1 + [
        Message(role=Role.ASSISTANT, content=response1),
        Message(role=Role.USER, content="What is Python?")  # Same question with context
    ]
    response2 = provider.chat(msg2, "mock-echo")
    # Should give same basic response since no decorator context yet
    assert "high-level programming language" in response2
```

## Key Testing Use Cases

### ✅ Session Management Tests
- **Save/Load Verification**: Test that conversation context is preserved
- **Memory Restoration**: Verify AI remembers previous topics after session load
- **Context Isolation**: Ensure cleared conversations have no memory

### ✅ Conversation Flow Tests
- **Topic Progression**: Test how conversations build context over time
- **Memory Questions**: Verify "what were we discussing" works correctly
- **Context Switching**: Test branching conversations

### ✅ Provider Interface Tests
- **Model Listing**: Test `list_models()` returns mock models
- **Streaming**: Test `chat_stream()` yields word-by-word responses
- **Async Support**: Test `achat()` and `achat_stream()` methods

## Important Testing Notes

### Memory Question Priority
Memory questions ("what were we discussing") are processed BEFORE topic-specific responses. This prevents false positives where topic keywords in the memory question itself trigger topic responses.

### Context Validation
The provider only references topics from PREVIOUS messages, not the current message being processed. This ensures realistic memory behavior.

### Predictable Responses
Responses are deterministic based on input patterns, making them suitable for automated testing assertions.

### No External Dependencies
MockProvider works completely offline and requires no API keys or network access.

## Example Test Template

```python
def test_mock_provider_behavior():
    provider = MockProvider()
    
    # Test specific pattern
    messages = [
        Message(role=Role.USER, content="your test input"),
        # Add more messages for context if needed
    ]
    
    response = provider.chat(messages, "mock-echo")
    
    # Assert expected behavior
    assert "expected content" in response
    # or
    assert any(keyword in response.lower() for keyword in ["keyword1", "keyword2"])
```

## Streaming Behavior

The MockProvider also supports streaming responses:

```python
def test_streaming():
    provider = MockProvider()
    messages = [Message(role=Role.USER, content="Hello")]
    
    chunks = list(provider.chat_stream(messages, "mock-echo"))
    full_response = "".join(chunk.content for chunk in chunks)
    
    assert full_response == "Hello! How can I help you today?"
```

This reference enables coding agents to write comprehensive tests that leverage the MockProvider's predictable behavior patterns while testing realistic conversation scenarios.