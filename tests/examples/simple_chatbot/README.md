# Simple Chatbot Example

A basic chatbot demonstrating core Coda module usage.

## Features

- Interactive command-line chat interface
- Provider selection (OpenAI, Anthropic, etc.)
- Model switching during conversation
- Conversation history management
- Token usage tracking

## Prerequisites

- Python 3.8+
- Coda modules installed
- At least one AI provider configured

## Setup

1. Install Coda:
   ```bash
   pip install -e ../..
   ```

2. Configure your AI provider(s):
   ```bash
   # Option 1: Environment variable
   export CODA_OPENAI_API_KEY="your-api-key"
   
   # Option 2: Config file
   cat > ~/.config/coda/config.toml << EOF
   [openai]
   api_key = "your-api-key"
   EOF
   ```

## Usage

Run the chatbot:

```bash
python chatbot.py
```

### Commands

- `quit` or `exit` - Exit the chatbot
- `clear` - Clear conversation history
- `model` - Switch to a different model

### Example Session

```
=== Coda Simple Chatbot ===

Available providers: openai, anthropic
Choose provider (or press Enter for first available): openai
Using model: gpt-4

Chatting with openai. Commands:
  'quit' or 'exit' - Exit the chatbot
  'clear' - Clear conversation history
  'model' - Change model

You: Hello! What can you help me with?
Assistant: Hello! I can help you with a wide variety of tasks, including:

1. **Answering questions** on many topics
2. **Writing assistance** - essays, emails, creative writing
3. **Programming help** - code examples, debugging, explanations
4. **Problem solving** - math, logic, analysis
5. **Learning support** - explaining concepts, study help
6. **Creative tasks** - brainstorming, storytelling
7. **General conversation** - discussing ideas and topics

What would you like to explore today?

[Tokens used: 127]

You: Write a Python function to calculate factorial
Assistant: Here's a Python function to calculate factorial with both iterative and recursive implementations:

```python
def factorial_iterative(n):
    """
    Calculate factorial using iteration.
    
    Args:
        n (int): Non-negative integer
        
    Returns:
        int: Factorial of n
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    
    result = 1
    for i in range(1, n + 1):
        result *= i
    return result


def factorial_recursive(n):
    """
    Calculate factorial using recursion.
    
    Args:
        n (int): Non-negative integer
        
    Returns:
        int: Factorial of n
        
    Raises:
        ValueError: If n is negative
    """
    if n < 0:
        raise ValueError("Factorial is not defined for negative numbers")
    
    # Base case
    if n == 0 or n == 1:
        return 1
    
    # Recursive case
    return n * factorial_recursive(n - 1)


# Example usage
if __name__ == "__main__":
    # Test both implementations
    test_values = [0, 1, 5, 10]
    
    for n in test_values:
        iter_result = factorial_iterative(n)
        rec_result = factorial_recursive(n)
        print(f"{n}! = {iter_result} (iterative) = {rec_result} (recursive)")
    
    # Test error handling
    try:
        factorial_iterative(-1)
    except ValueError as e:
        print(f"Error: {e}")
```

The iterative version is generally more efficient for large values of n since it doesn't have the recursive call overhead and won't hit Python's recursion limit.

[Tokens used: 423]

You: quit

Goodbye!
```

## How It Works

1. **Configuration Loading**: Uses the Config module to load settings
2. **Provider Creation**: Uses ProviderFactory to create AI provider instances
3. **Message Management**: Maintains conversation history
4. **Error Handling**: Gracefully handles configuration and API errors

## Extending the Example

You can extend this chatbot by:

1. **Adding Session Persistence**:
   ```python
   from coda.base.session import SessionManager
   session_manager = SessionManager(config.to_dict())
   session = session_manager.create_session("my-chat")
   ```

2. **Adding Themes**:
   ```python
   from coda.base.theme import ThemeManager
   theme = ThemeManager(config.to_dict())
   theme.display_message("Assistant", response)
   ```

3. **Multiple Providers**:
   ```python
   providers = {name: factory.create(name) for name in available}
   # Compare responses from different providers
   ```

## Troubleshooting

### No providers available
- Check your configuration file exists
- Verify API keys are set correctly
- Ensure required provider packages are installed

### Authentication errors
- Verify your API key is valid
- Check you have credits/quota available
- Ensure network connectivity

### Import errors
- Make sure Coda is installed: `pip install -e ../..`
- Check you're in the correct virtual environment