"""Developer modes and related functionality shared across CLI modes."""

from enum import Enum


class DeveloperMode(Enum):
    """Available developer modes with different AI personalities."""

    GENERAL = "general"
    CODE = "code"
    DEBUG = "debug"
    EXPLAIN = "explain"
    REVIEW = "review"
    REFACTOR = "refactor"
    PLAN = "plan"


MODE_DESCRIPTIONS = {
    DeveloperMode.GENERAL: "General conversation and assistance",
    DeveloperMode.CODE: "Optimized for writing new code with best practices",
    DeveloperMode.DEBUG: "Focus on error analysis and debugging assistance",
    DeveloperMode.EXPLAIN: "Detailed code explanations and documentation",
    DeveloperMode.REVIEW: "Security and code quality review",
    DeveloperMode.REFACTOR: "Code improvement and optimization suggestions",
    DeveloperMode.PLAN: "Architecture planning and system design",
}

SYSTEM_PROMPTS = {
    DeveloperMode.GENERAL: "You are a helpful AI assistant. Provide clear, accurate, and useful responses to any questions or requests.",
    DeveloperMode.CODE: "You are a helpful coding assistant. Focus on writing clean, efficient, and well-documented code following best practices.",
    DeveloperMode.DEBUG: "You are a debugging expert. Focus on identifying issues, analyzing error messages, and providing clear solutions with explanations.",
    DeveloperMode.EXPLAIN: "You are a patient teacher. Provide detailed explanations of code, concepts, and implementations in a clear and educational manner.",
    DeveloperMode.REVIEW: "You are a code reviewer. Focus on security, performance, best practices, and potential improvements in the code.",
    DeveloperMode.REFACTOR: "You are a refactoring specialist. Suggest improvements for code clarity, performance, and maintainability while preserving functionality.",
    DeveloperMode.PLAN: "You are a software architect. Help with system design, architecture planning, technology choices, and breaking down complex problems into manageable components.",
}


def get_mode_description(mode: DeveloperMode) -> str:
    """Get description for a specific mode."""
    return MODE_DESCRIPTIONS.get(mode, "")


def get_system_prompt(mode: DeveloperMode) -> str:
    """Get system prompt based on mode."""
    return SYSTEM_PROMPTS.get(mode, "")
