"""NLP-based tool intent classification for intelligent tool selection."""

import re
from typing import Any


class ToolIntentClassifier:
    """Classifies user intent and matches to appropriate tools using NLP techniques."""

    def __init__(self, response_content: str, tools: list[Any]):
        """
        Initialize the classifier.

        Args:
            response_content: The model's response text to analyze
            tools: Available tools
        """
        self.response_content = response_content  # Keep original case for entity extraction
        self.response_content_lower = response_content.lower()  # Separate lowercase for analysis
        self.tools = tools
        self.entities = self._extract_entities()
        self.intent_signals = self._extract_intent_signals()

    def analyze(self) -> list[tuple[str, dict, float]]:
        """
        Analyze the response and return tool recommendations.

        Returns:
            List of (tool_name, arguments, confidence_score) tuples
        """
        recommendations = []

        for tool in self.tools:
            confidence, args = self._match_tool(tool)
            if confidence > 0.3:  # Minimum confidence threshold
                recommendations.append((tool.name, args, confidence))

        # Sort by confidence descending
        recommendations.sort(key=lambda x: x[2], reverse=True)

        return recommendations

    def _extract_entities(self) -> dict[str, list[str]]:
        """Extract key entities from the response content."""
        entities = {
            "files": [],
            "commands": [],
            "urls": [],
            "directories": [],
        }

        # File entities - look for file patterns
        file_patterns = [
            r"\b(\w+\.\w+)\b",  # filename.ext
            r"`([^`]+\.\w+)`",  # `filename.ext`
            r"\\`([^`]+\.\w+)\\`",  # \`filename.ext\` (escaped backticks)
            r'["\']([^"\']+\.\w+)["\']',  # "filename.ext" or 'filename.ext'
            r"(\w+\.\w+)",  # any word.ext pattern
        ]

        for pattern in file_patterns:
            matches = re.findall(pattern, self.response_content)  # Use original case
            entities["files"].extend(matches)

        # Command entities - look for command patterns
        command_patterns = [
            r"`([^`]+)`",  # `command`
            r"\b(ls|pwd|cd|mkdir|rm|cp|mv|grep|find|git)\b",  # common commands
        ]

        for pattern in command_patterns:
            matches = re.findall(pattern, self.response_content_lower)
            entities["commands"].extend(matches)

        # URL entities
        url_pattern = r"https?://[^\s]+"
        entities["urls"] = re.findall(url_pattern, self.response_content)

        # Directory entities
        dir_patterns = [
            r"\b(\w+/\w+)",  # path/to/dir
            r"/[^\s]+",  # absolute paths
        ]

        for pattern in dir_patterns:
            matches = re.findall(pattern, self.response_content_lower)
            entities["directories"].extend(matches)

        return entities

    def _extract_intent_signals(self) -> dict[str, float]:
        """Extract intent signals with confidence scores."""
        signals = {}

        # File operation intents
        file_ops = {
            "read_intent": [
                "read",
                "show",
                "display",
                "contents",
                "open",
                "view",
                "cat",
                "provide",
                "need",
                "check",
            ],
            "write_intent": ["write", "save", "create", "edit", "modify", "update"],
            "list_intent": ["list", "show", "directory", "files", "ls", "dir"],
        }

        for intent, keywords in file_ops.items():
            score = sum(1 for keyword in keywords if keyword in self.response_content_lower)
            signals[intent] = min(score / len(keywords), 1.0)  # Normalize to 0-1

        # Shell operation intents
        shell_keywords = ["run", "execute", "command", "shell", "bash", "terminal"]
        signals["shell_intent"] = min(
            sum(1 for keyword in shell_keywords if keyword in self.response_content_lower)
            / len(shell_keywords),
            1.0,
        )

        # Web operation intents
        web_keywords = [
            "search",
            "web",
            "internet",
            "online",
            "lookup",
            "find information",
            "google",
            "bing",
        ]
        signals["web_intent"] = min(
            sum(1 for keyword in web_keywords if keyword in self.response_content_lower)
            / len(web_keywords),
            1.0,
        )

        return signals

    def _match_tool(self, tool: Any) -> tuple[float, dict]:
        """
        Calculate confidence score for a specific tool match.

        Args:
            tool: Tool object to evaluate

        Returns:
            Tuple of (confidence_score, extracted_arguments)
        """
        confidence = 0.0
        args = {}

        # Direct tool name mention (high confidence)
        if tool.name in self.response_content_lower:
            confidence += 0.8

        # Semantic matching based on tool type
        if tool.name == "read_file":
            confidence += self._calculate_file_read_confidence()
            args = self._extract_file_arguments()

        elif tool.name == "write_file":
            confidence += self._calculate_file_write_confidence()
            args = self._extract_file_arguments()

        elif tool.name == "list_files":
            confidence += self._calculate_list_confidence()

        elif "shell" in tool.name or "run" in tool.name:
            confidence += self._calculate_shell_confidence()
            args = self._extract_command_arguments()

        elif "search" in tool.name or "web" in tool.name:
            confidence += self._calculate_web_confidence()
            args = self._extract_search_arguments()

        # Boost confidence if we have entities that match
        if args:
            confidence += 0.2

        return min(confidence, 1.0), args

    def _calculate_file_read_confidence(self) -> float:
        """Calculate confidence for file reading operations."""
        read_signals = self.intent_signals.get("read_intent", 0)
        has_files = len(self.entities["files"]) > 0

        # Keywords that strongly suggest file reading
        strong_indicators = ["contents", "show me", "display", "read"]
        strong_score = sum(
            0.2 for indicator in strong_indicators if indicator in self.response_content
        )

        return min(read_signals + (0.3 if has_files else 0) + strong_score, 1.0)

    def _calculate_file_write_confidence(self) -> float:
        """Calculate confidence for file writing operations."""
        write_signals = self.intent_signals.get("write_intent", 0)
        has_files = len(self.entities["files"]) > 0

        return min(write_signals + (0.3 if has_files else 0), 1.0)

    def _calculate_list_confidence(self) -> float:
        """Calculate confidence for file listing operations."""
        list_signals = self.intent_signals.get("list_intent", 0)
        has_dirs = len(self.entities["directories"]) > 0

        # Check for listing-specific phrases
        listing_phrases = ["list files", "show files", "directory contents", "what files"]
        phrase_score = sum(0.3 for phrase in listing_phrases if phrase in self.response_content)

        return min(list_signals + (0.2 if has_dirs else 0) + phrase_score, 1.0)

    def _calculate_shell_confidence(self) -> float:
        """Calculate confidence for shell operations."""
        shell_signals = self.intent_signals.get("shell_intent", 0)
        has_commands = len(self.entities["commands"]) > 0

        return min(shell_signals + (0.4 if has_commands else 0), 1.0)

    def _calculate_web_confidence(self) -> float:
        """Calculate confidence for web operations."""
        web_signals = self.intent_signals.get("web_intent", 0)

        return web_signals

    def _extract_file_arguments(self) -> dict:
        """Extract file-related arguments."""
        args = {}

        if self.entities["files"]:
            # Use the first detected file and check for case variations
            filename = self.entities["files"][0]

            # Try to find the actual file with proper case
            import os

            variations = [
                filename,
                filename.upper(),
                filename.lower(),
                filename.capitalize(),
            ]

            for variation in variations:
                if os.path.exists(variation):
                    args["filepath"] = variation
                    break
            else:
                # If no variations exist, use original
                args["filepath"] = filename

        return args

    def _extract_command_arguments(self) -> dict:
        """Extract command arguments."""
        args = {}

        if self.entities["commands"]:
            # Use the first detected command
            args["command"] = self.entities["commands"][0]

        return args

    def _extract_search_arguments(self) -> dict:
        """Extract search query arguments."""
        args = {}

        # Try to extract search query from common patterns
        search_patterns = [
            r"search.*?for\s+(.+?)(?:\.|$)",
            r"look.*?up\s+(.+?)(?:\.|$)",
            r"find.*?information.*?about\s+(.+?)(?:\.|$)",
        ]

        for pattern in search_patterns:
            matches = re.findall(pattern, self.response_content)
            if matches:
                args["query"] = matches[0].strip()
                break

        return args
