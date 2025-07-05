# Developer Modes Guide

Coda provides seven specialized developer modes that optimize the AI assistant's responses for different programming tasks. Each mode sets a specific system prompt that guides the AI's behavior and focus.

## Available Modes

### 🌐 General Mode (default)
**Purpose**: General conversation and assistance  
**Best for**: General questions, brainstorming, or when you're not sure which mode to use  
**Command**: `/mode general`

The AI provides balanced, helpful responses suitable for any type of question or request.

### 💻 Code Mode
**Purpose**: Optimized for writing new code with best practices  
**Best for**: Implementing new features, writing functions, creating scripts  
**Command**: `/mode code`

The AI focuses on writing clean, efficient, and well-documented code following best practices.

### 🐛 Debug Mode
**Purpose**: Focus on error analysis and debugging assistance  
**Best for**: Fixing bugs, understanding error messages, troubleshooting issues  
**Command**: `/mode debug`

The AI becomes a debugging expert, focusing on identifying issues, analyzing error messages, and providing clear solutions with explanations.

### 📚 Explain Mode
**Purpose**: Detailed code explanations and documentation  
**Best for**: Learning new concepts, understanding existing code, getting thorough explanations  
**Command**: `/mode explain`

The AI acts as a patient teacher, providing detailed explanations of code, concepts, and implementations in a clear and educational manner.

### 🔍 Review Mode
**Purpose**: Security and code quality review  
**Best for**: Code reviews, security audits, finding potential issues  
**Command**: `/mode review`

The AI focuses on security vulnerabilities, performance issues, best practices, and potential improvements in your code.

### 🔧 Refactor Mode
**Purpose**: Code improvement and optimization suggestions  
**Best for**: Improving existing code, optimizing performance, enhancing readability  
**Command**: `/mode refactor`

The AI suggests improvements for code clarity, performance, and maintainability while preserving functionality.

### 📐 Plan Mode
**Purpose**: Architecture planning and system design  
**Best for**: System design, architecture decisions, breaking down complex problems  
**Command**: `/mode plan`

The AI becomes a software architect, helping with system design, architecture planning, technology choices, and breaking down complex problems into manageable components.

## How to Use Modes

### Interactive Mode
```bash
# Start Coda
uv run coda

# Switch to a specific mode
/mode debug

# Ask your question
Why am I getting "TypeError: cannot read property 'length' of undefined"?

# Switch to another mode anytime
/mode refactor
How can I improve this function?
```

### One-Shot Mode
```bash
# Use a specific mode for a single query
uv run coda --one-shot --mode explain "What is recursion?"

# Or with basic mode
uv run coda --basic --one-shot --mode review "SELECT * FROM users WHERE id = ${userId}"
```

### Command Line Flag
```bash
# Start with a specific mode
uv run coda --mode code
uv run coda --basic --mode debug
```

## Mode Comparison Examples

Here's how different modes respond to the same question:

### Example: "What's a singleton pattern?"

**General Mode**: Provides a balanced explanation with basic example  
**Code Mode**: Shows implementation examples in multiple languages  
**Explain Mode**: Detailed educational explanation with pros/cons and use cases  
**Review Mode**: Focuses on when to use/avoid singletons and potential issues  
**Refactor Mode**: Shows how to refactor code to/from singleton pattern  
**Plan Mode**: Discusses architectural implications and alternatives

### Real Example: "How do I handle errors in Python?"

<details>
<summary><b>Code Mode Response</b></summary>

```python
# Basic error handling with try-except
try:
    result = risky_operation()
except SpecificError as e:
    logger.error(f"Operation failed: {e}")
    raise
except Exception as e:
    logger.exception("Unexpected error")
    return default_value
finally:
    cleanup_resources()

# Context manager for automatic cleanup
from contextlib import contextmanager

@contextmanager
def error_handler():
    try:
        yield
    except Exception as e:
        log_error(e)
        raise

# Custom exception classes
class ValidationError(Exception):
    """Raised when input validation fails"""
    pass
```
</details>

<details>
<summary><b>Explain Mode Response</b></summary>

Error handling in Python is a fundamental concept that helps you write robust programs. Let me explain it step by step:

**What are Exceptions?**
Exceptions are events that occur during program execution that disrupt the normal flow. Python uses exceptions to signal errors.

**The Try-Except Block**
The basic structure consists of:
1. `try`: Code that might raise an exception
2. `except`: Code that handles the exception
3. `else`: Code that runs if no exception occurs
4. `finally`: Code that always runs

**Exception Hierarchy**
Python has a hierarchy of built-in exceptions:
- `BaseException` (top level)
  - `Exception` (common base class)
    - `ValueError`: Invalid value
    - `TypeError`: Wrong type
    - `KeyError`: Missing dictionary key
    - etc.

**Best Practices**
1. Be specific with exception types
2. Don't catch exceptions silently
3. Use logging for error tracking
4. Clean up resources in finally blocks
5. Create custom exceptions for domain-specific errors
</details>

### Example: SQL Injection Vulnerability

```sql
query = f"SELECT * FROM users WHERE id = {user_id}"
```

**Debug Mode**: Explains why the query fails with certain inputs  
**Review Mode**: Immediately identifies SQL injection risk and security implications  
**Refactor Mode**: Shows how to fix using parameterized queries  
**Explain Mode**: Teaches about SQL injection attacks and prevention

## Tips for Effective Mode Usage

1. **Start with the right mode**: Choose a mode that matches your current task
2. **Switch modes as needed**: You can change modes anytime during a session
3. **Mode persists**: The mode stays active until you change it or clear the conversation
4. **Combine modes**: Use different modes in sequence (e.g., debug → refactor → review)
5. **Check current mode**: Use `/mode` without arguments to see the active mode

## Mode Implementation Details

Each mode sets a specific system prompt that guides the AI's behavior:

- **General**: "You are a helpful AI assistant. Provide clear, accurate, and useful responses."
- **Code**: "You are a helpful coding assistant. Focus on writing clean, efficient code."
- **Debug**: "You are a debugging expert. Focus on identifying issues and solutions."
- **Explain**: "You are a patient teacher. Provide detailed explanations."
- **Review**: "You are a code reviewer. Focus on security, performance, best practices."
- **Refactor**: "You are a refactoring specialist. Suggest improvements."
- **Plan**: "You are a software architect. Help with system design and planning."

## Common Workflows

### Debugging Workflow
```bash
/mode debug
# Paste error message
/mode explain
# Understand the root cause
/mode code
# Implement the fix
```

### Code Review Workflow
```bash
/mode review
# Paste code for review
/mode refactor
# Get improvement suggestions
/mode code
# Implement improvements
```

### Learning Workflow
```bash
/mode explain
# Ask about a concept
/mode code
# See implementation examples
/mode review
# Understand best practices
```

## Keyboard Shortcuts

- Check current mode: `/mode`
- Quick mode switch: `/mode <name>` or `/m <name>`
- Mode descriptions: `/help` shows all modes

## Notes

- System prompts are included with every message to the AI
- Mode changes take effect immediately on the next message
- Clearing the conversation (`/clear`) preserves the current mode
- Switching models preserves the current mode
- Both basic and interactive CLI modes support all developer modes