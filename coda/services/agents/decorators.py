"""Decorators for the agent system."""

import inspect
from functools import wraps


def tool(func=None, *, name=None, description=None):
    """
    Decorator to mark a function as a tool for agents.

    Can be used as @tool or @tool(name="custom_name", description="desc")

    Args:
        func: The function to decorate
        name: Optional custom name for the tool (defaults to function name)
        description: Optional description (defaults to function docstring)

    Returns:
        Decorated function with tool metadata
    """

    def decorator(func):
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            return func(*args, **kwargs)

        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            return await func(*args, **kwargs)

        # Choose wrapper based on function type
        if inspect.iscoroutinefunction(func):
            wrapper = async_wrapper
        else:
            wrapper = sync_wrapper

        # Add tool metadata
        wrapper._is_tool = True
        wrapper._tool_name = name or func.__name__
        wrapper._tool_description = description or (inspect.getdoc(func) or "")

        return wrapper

    # Handle both @tool and @tool(...) syntax
    if func is None:
        return decorator
    return decorator(func)
