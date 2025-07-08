"""Type definitions for the agent system."""

from dataclasses import dataclass
from enum import Enum
from typing import Any


class RequiredActionType(str, Enum):
    """Types of required actions."""

    FUNCTION_CALLING = "FUNCTION_CALLING_REQUIRED_ACTION"


class PerformedActionType(str, Enum):
    """Types of performed actions."""

    FUNCTION_CALLING = "FUNCTION_CALLING_PERFORMED_ACTION"


@dataclass
class FunctionCall:
    """Represents a function call request."""

    name: str
    arguments: dict[str, Any]

    @classmethod
    def from_tool_call(cls, tool_call):
        """Create from provider ToolCall."""
        return cls(name=tool_call.name, arguments=tool_call.arguments)


@dataclass
class RequiredAction:
    """An action required by the agent."""

    action_id: str
    required_action_type: RequiredActionType
    function_call: FunctionCall | None = None

    @classmethod
    def from_tool_call(cls, tool_call):
        """Create from provider ToolCall."""
        return cls(
            action_id=tool_call.id,
            required_action_type=RequiredActionType.FUNCTION_CALLING,
            function_call=FunctionCall.from_tool_call(tool_call),
        )


@dataclass
class PerformedAction:
    """An action performed in response to a required action."""

    action_id: str
    performed_action_type: PerformedActionType
    function_call_output: str


@dataclass
class RunResponse:
    """Response from running an agent."""

    session_id: str | None
    data: dict[str, Any]
    raw_responses: list = None

    @property
    def content(self) -> str:
        """Get the content from the response."""
        if isinstance(self.data, dict):
            return self.data.get("content", "")
        return str(self.data)
