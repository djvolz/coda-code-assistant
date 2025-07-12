"""Decorators for instrumenting Coda components with observability.

This module provides decorators for automatically adding metrics, tracing,
and error tracking to provider methods, session operations, and other components.
"""

import functools
import inspect
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar

from .manager import ObservabilityManager

# Type variable for generic function types
T = TypeVar("T", bound=Callable[..., Any])


@dataclass
class InstrumentationContext:
    """Shared context for instrumentation."""

    operation_name: str
    provider_name: str
    start_time: float
    metadata: dict[str, Any]

    @property
    def response_time_ms(self) -> float:
        """Calculate response time in milliseconds."""
        return (time.time() - self.start_time) * 1000

    def add_token_usage(self, result: Any) -> None:
        """Extract token usage from result if available."""
        if hasattr(result, "usage"):
            if hasattr(result.usage, "total_tokens"):
                self.metadata["tokens_used"] = result.usage.total_tokens
            elif hasattr(result.usage, "completion_tokens"):
                self.metadata["tokens_used"] = result.usage.completion_tokens


def _instrument_method(
    func: Callable,
    self: Any,
    args: tuple,
    kwargs: dict,
    context: InstrumentationContext,
    obs_manager: ObservabilityManager,
    record_tokens: bool = True,
) -> Any:
    """Common instrumentation logic for sync and async methods."""
    # Create tracing span
    with obs_manager.create_span(
        context.operation_name, provider=context.provider_name, operation_type="provider_method"
    ) as span:
        try:
            # Record request start
            obs_manager.record_provider_event(
                context.provider_name, "request_started", {"operation": context.operation_name}
            )

            # Execute the method (caller handles sync/async)
            result = yield

            # Update metadata
            context.metadata["response_time"] = context.response_time_ms

            if record_tokens:
                context.add_token_usage(result)

            # Record successful completion
            obs_manager.record_provider_event(
                context.provider_name, "request_completed", context.metadata
            )

            # Add span tags
            span.add_tag("success", True)
            span.add_tag("response_time_ms", context.response_time_ms)
            if "tokens_used" in context.metadata:
                span.add_tag("tokens_used", context.metadata["tokens_used"])

            return result

        except Exception as e:
            # Record error
            obs_manager.record_provider_event(
                context.provider_name,
                "request_error",
                {
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "response_time": context.response_time_ms,
                },
            )

            obs_manager.record_error(
                e, {"provider": context.provider_name, "operation": context.operation_name}
            )

            # Update span with error
            span.add_tag("success", False)
            span.add_tag("error", True)
            span.add_tag("error_type", type(e).__name__)
            span.add_log(f"Error: {str(e)}", level="error")

            raise


def instrument_provider_method(
    operation_name: str | None = None, record_tokens: bool = True, record_response_time: bool = True
) -> Callable[[T], T]:
    """Decorator to instrument provider methods with observability.

    Args:
        operation_name: Name of the operation (defaults to method name)
        record_tokens: Whether to record token usage
        record_response_time: Whether to record response time

    Returns:
        Decorated function with observability instrumentation
    """

    def decorator(func: T) -> T:
        if inspect.iscoroutinefunction(func):

            @functools.wraps(func)
            async def async_wrapper(self, *args, **kwargs):
                # Get observability manager
                obs_manager = getattr(self, "_observability_manager", None)
                if not obs_manager or not obs_manager.enabled:
                    return await func(self, *args, **kwargs)

                # Create context
                op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"
                provider_name = getattr(self, "provider_name", self.__class__.__name__)

                context = InstrumentationContext(
                    operation_name=op_name,
                    provider_name=provider_name,
                    start_time=time.time(),
                    metadata={},
                )

                # Create tracing span
                with obs_manager.create_span(
                    context.operation_name,
                    provider=context.provider_name,
                    operation_type="provider_method",
                ) as span:
                    try:
                        # Record request start
                        obs_manager.record_provider_event(
                            context.provider_name,
                            "request_started",
                            {"operation": context.operation_name},
                        )

                        # Execute the method
                        result = await func(self, *args, **kwargs)

                        # Update metadata
                        context.metadata["response_time"] = context.response_time_ms

                        if record_tokens:
                            context.add_token_usage(result)

                        # Record successful completion
                        obs_manager.record_provider_event(
                            context.provider_name, "request_completed", context.metadata
                        )

                        # Add span tags
                        span.add_tag("success", True)
                        span.add_tag("response_time_ms", context.response_time_ms)
                        if "tokens_used" in context.metadata:
                            span.add_tag("tokens_used", context.metadata["tokens_used"])

                        return result

                    except Exception as e:
                        # Record error
                        obs_manager.record_provider_event(
                            context.provider_name,
                            "request_error",
                            {
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "response_time": context.response_time_ms,
                            },
                        )

                        obs_manager.record_error(
                            e,
                            {
                                "provider": context.provider_name,
                                "operation": context.operation_name,
                            },
                        )

                        # Update span with error
                        span.add_tag("success", False)
                        span.add_tag("error", True)
                        span.add_tag("error_type", type(e).__name__)
                        span.add_log(f"Error: {str(e)}", level="error")

                        raise

            return async_wrapper
        else:

            @functools.wraps(func)
            def sync_wrapper(self, *args, **kwargs):
                # Get observability manager
                obs_manager = getattr(self, "_observability_manager", None)
                if not obs_manager or not obs_manager.enabled:
                    return func(self, *args, **kwargs)

                # Create context
                op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"
                provider_name = getattr(self, "provider_name", self.__class__.__name__)

                context = InstrumentationContext(
                    operation_name=op_name,
                    provider_name=provider_name,
                    start_time=time.time(),
                    metadata={},
                )

                # Create tracing span
                with obs_manager.create_span(
                    context.operation_name,
                    provider=context.provider_name,
                    operation_type="provider_method",
                ) as span:
                    try:
                        # Record request start
                        obs_manager.record_provider_event(
                            context.provider_name,
                            "request_started",
                            {"operation": context.operation_name},
                        )

                        # Execute the method
                        result = func(self, *args, **kwargs)

                        # Update metadata
                        context.metadata["response_time"] = context.response_time_ms

                        if record_tokens:
                            context.add_token_usage(result)

                        # Record successful completion
                        obs_manager.record_provider_event(
                            context.provider_name, "request_completed", context.metadata
                        )

                        # Add span tags
                        span.add_tag("success", True)
                        span.add_tag("response_time_ms", context.response_time_ms)
                        if "tokens_used" in context.metadata:
                            span.add_tag("tokens_used", context.metadata["tokens_used"])

                        return result

                    except Exception as e:
                        # Record error
                        obs_manager.record_provider_event(
                            context.provider_name,
                            "request_error",
                            {
                                "error_type": type(e).__name__,
                                "error_message": str(e),
                                "response_time": context.response_time_ms,
                            },
                        )

                        obs_manager.record_error(
                            e,
                            {
                                "provider": context.provider_name,
                                "operation": context.operation_name,
                            },
                        )

                        # Update span with error
                        span.add_tag("success", False)
                        span.add_tag("error", True)
                        span.add_tag("error_type", type(e).__name__)
                        span.add_log(f"Error: {str(e)}", level="error")

                        raise

            return sync_wrapper

    return decorator


def instrument_session_method(operation_name: str | None = None):
    """Decorator to instrument session management methods.

    Args:
        operation_name: Name of the operation (defaults to method name)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # Get observability manager from session manager
            obs_manager = getattr(self, "_observability_manager", None)
            if not obs_manager or not obs_manager.enabled:
                return func(self, *args, **kwargs)

            op_name = operation_name or f"{self.__class__.__name__}.{func.__name__}"

            # Start timing
            start_time = time.time()

            # Create tracing span
            with obs_manager.create_span(op_name, operation_type="session_method") as span:
                try:
                    # Execute the method
                    result = func(self, *args, **kwargs)

                    # Calculate response time
                    response_time = (time.time() - start_time) * 1000  # ms

                    # Record session event based on method name
                    if "create" in func.__name__.lower():
                        obs_manager.record_session_event(
                            "session_created",
                            {
                                "session_id": getattr(result, "id", None),
                                "response_time": response_time,
                            },
                        )
                    elif "save" in func.__name__.lower():
                        obs_manager.record_session_event(
                            "session_saved",
                            {
                                "session_id": args[0] if args else None,
                                "response_time": response_time,
                            },
                        )
                    elif "load" in func.__name__.lower():
                        obs_manager.record_session_event(
                            "session_loaded",
                            {
                                "session_id": args[0] if args else None,
                                "response_time": response_time,
                            },
                        )
                    elif "delete" in func.__name__.lower():
                        obs_manager.record_session_event(
                            "session_deleted",
                            {
                                "session_id": args[0] if args else None,
                                "response_time": response_time,
                            },
                        )

                    # Add span tags
                    span.add_tag("success", True)
                    span.add_tag("response_time_ms", response_time)

                    return result

                except Exception as e:
                    # Calculate response time for error case
                    response_time = (time.time() - start_time) * 1000  # ms

                    # Record error
                    obs_manager.record_session_event(
                        "session_error",
                        {
                            "operation": op_name,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "response_time": response_time,
                        },
                    )

                    obs_manager.record_error(
                        e,
                        {
                            "operation": op_name,
                            "args": str(args)[:200],  # Truncate for safety
                            "kwargs": str(kwargs)[:200],
                        },
                    )

                    # Add span tags
                    span.add_tag("success", False)
                    span.add_tag("error_type", type(e).__name__)
                    span.add_tag("response_time_ms", response_time)

                    raise

        return wrapper

    return decorator


def instrument_cli_command(command_name: str | None = None):
    """Decorator to instrument CLI commands with observability.

    Args:
        command_name: Name of the command (defaults to function name)
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Try to get observability manager from various sources
            obs_manager = None

            # Check if first argument has observability manager
            if args and hasattr(args[0], "_observability_manager"):
                obs_manager = args[0]._observability_manager

            # Check for global observability manager
            if not obs_manager:
                try:
                    from ..config import ConfigManager

                    config_manager = ConfigManager()
                    obs_manager = ObservabilityManager(config_manager)
                except Exception:
                    pass

            if not obs_manager or not obs_manager.enabled:
                return func(*args, **kwargs)

            cmd_name = command_name or func.__name__

            # Start timing
            start_time = time.time()

            # Create tracing span
            with obs_manager.create_span(
                f"cli_command_{cmd_name}", operation_type="cli_command", command=cmd_name
            ) as span:
                try:
                    # Execute the command
                    result = func(*args, **kwargs)

                    # Calculate response time
                    response_time = (time.time() - start_time) * 1000  # ms

                    # Record command execution
                    obs_manager.record_session_event(
                        "command_executed",
                        {"command": cmd_name, "response_time": response_time, "success": True},
                    )

                    # Add span tags
                    span.add_tag("success", True)
                    span.add_tag("response_time_ms", response_time)

                    return result

                except Exception as e:
                    # Calculate response time for error case
                    response_time = (time.time() - start_time) * 1000  # ms

                    # Record error
                    obs_manager.record_session_event(
                        "command_error",
                        {
                            "command": cmd_name,
                            "error_type": type(e).__name__,
                            "error_message": str(e),
                            "response_time": response_time,
                        },
                    )

                    obs_manager.record_error(
                        e,
                        {
                            "command": cmd_name,
                            "args": str(args)[:200],  # Truncate for safety
                            "kwargs": str(kwargs)[:200],
                        },
                    )

                    # Add span tags
                    span.add_tag("success", False)
                    span.add_tag("error_type", type(e).__name__)
                    span.add_tag("response_time_ms", response_time)

                    raise

        return wrapper

    return decorator
