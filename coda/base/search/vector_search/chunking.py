"""
Text chunking utilities for semantic search.

This module provides intelligent chunking strategies for different file types,
ensuring that code and documentation are split at meaningful boundaries.
"""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Chunk:
    """Represents a chunk of text with metadata."""

    text: str
    start_line: int
    end_line: int
    chunk_type: str  # e.g., "function", "class", "comment", "text"
    metadata: dict[str, Any] | None = None


class TextChunker:
    """Base class for text chunking strategies."""

    def __init__(
        self,
        chunk_size: int = 1000,  # Target chunk size in characters
        chunk_overlap: int = 200,  # Overlap between chunks
        min_chunk_size: int = 100,  # Minimum chunk size
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size

    def chunk_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split text into chunks with overlap."""
        chunks = []
        lines = text.split("\n")

        current_chunk = []
        current_start = 0
        current_size = 0

        for i, line in enumerate(lines):
            line_size = len(line) + 1  # +1 for newline

            # Check if adding this line would exceed chunk size
            if current_size + line_size > self.chunk_size and current_size >= self.min_chunk_size:
                # Create chunk
                chunk_text = "\n".join(current_chunk)
                chunks.append(
                    Chunk(
                        text=chunk_text,
                        start_line=current_start,
                        end_line=i - 1,
                        chunk_type="text",
                        metadata=metadata,
                    )
                )

                # Start new chunk with overlap
                overlap_start = max(
                    0, len(current_chunk) - self._calculate_overlap_lines(current_chunk)
                )
                current_chunk = current_chunk[overlap_start:]
                current_start = current_start + overlap_start
                current_size = sum(len(line) + 1 for line in current_chunk)

            current_chunk.append(line)
            current_size += line_size

        # Add final chunk
        if current_chunk and current_size >= self.min_chunk_size:
            chunk_text = "\n".join(current_chunk)
            chunks.append(
                Chunk(
                    text=chunk_text,
                    start_line=current_start,
                    end_line=len(lines) - 1,
                    chunk_type="text",
                    metadata=metadata,
                )
            )

        return chunks

    def _calculate_overlap_lines(self, lines: list[str]) -> int:
        """Calculate number of lines for overlap."""
        total_size = sum(len(line) + 1 for line in lines)
        if total_size <= self.chunk_overlap:
            return len(lines)

        overlap_size = 0
        overlap_lines = 0

        for line in reversed(lines):
            overlap_size += len(line) + 1
            overlap_lines += 1
            if overlap_size >= self.chunk_overlap:
                break

        return overlap_lines


class CodeChunker(TextChunker):
    """Intelligent code chunking that respects code structure."""

    def __init__(self, language: str = "python", **kwargs):
        super().__init__(**kwargs)
        self.language = language

    def chunk_text(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Split code into chunks at logical boundaries."""
        if self.language.lower() in ["python", "py"]:
            return self._chunk_python(text, metadata)
        elif self.language.lower() in ["javascript", "js", "typescript", "ts"]:
            return self._chunk_javascript(text, metadata)
        else:
            # Fall back to basic chunking
            return super().chunk_text(text, metadata)

    def _chunk_python(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Chunk Python code by functions and classes."""
        chunks = []
        lines = text.split("\n")

        # Patterns for Python structure
        class_pattern = re.compile(r"^class\s+(\w+)")
        func_pattern = re.compile(r"^def\s+(\w+)")
        method_pattern = re.compile(r"^\s+def\s+(\w+)")

        current_chunk = []
        current_start = 0
        current_type = "module"
        in_class = False

        for i, line in enumerate(lines):
            # Check for class definition
            if class_pattern.match(line):
                # Save previous chunk if exists
                if current_chunk and len("\n".join(current_chunk)) >= self.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text="\n".join(current_chunk),
                            start_line=current_start,
                            end_line=i - 1,
                            chunk_type=current_type,
                            metadata=metadata,
                        )
                    )
                current_chunk = [line]
                current_start = i
                current_type = "class"
                in_class = True

            # Check for function definition
            elif func_pattern.match(line) or (in_class and method_pattern.match(line)):
                # If we're in a class and this is a method, check chunk size
                if in_class and len("\n".join(current_chunk)) > self.chunk_size:
                    # Save class chunk up to this point
                    chunks.append(
                        Chunk(
                            text="\n".join(current_chunk),
                            start_line=current_start,
                            end_line=i - 1,
                            chunk_type=current_type,
                            metadata=metadata,
                        )
                    )
                    current_chunk = [line]
                    current_start = i
                    current_type = "method" if in_class else "function"
                else:
                    current_chunk.append(line)

            # Check if we're leaving a class (dedent to module level)
            elif in_class and line and not line[0].isspace():
                # Save current chunk
                if current_chunk and len("\n".join(current_chunk)) >= self.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text="\n".join(current_chunk),
                            start_line=current_start,
                            end_line=i - 1,
                            chunk_type=current_type,
                            metadata=metadata,
                        )
                    )
                current_chunk = [line]
                current_start = i
                current_type = "module"
                in_class = False

            else:
                current_chunk.append(line)

                # Check if chunk is getting too large
                if len("\n".join(current_chunk)) > self.chunk_size:
                    # Find a good breaking point (empty line or dedent)
                    break_point = self._find_break_point(current_chunk)

                    if break_point > 0:
                        chunk_text = "\n".join(current_chunk[:break_point])
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                start_line=current_start,
                                end_line=current_start + break_point - 1,
                                chunk_type=current_type,
                                metadata=metadata,
                            )
                        )

                        # Start new chunk with overlap
                        overlap_start = max(0, break_point - 5)  # Keep last 5 lines for context
                        current_chunk = current_chunk[overlap_start:]
                        current_start = current_start + overlap_start

        # Add final chunk
        if current_chunk and len("\n".join(current_chunk)) >= self.min_chunk_size:
            chunks.append(
                Chunk(
                    text="\n".join(current_chunk),
                    start_line=current_start,
                    end_line=len(lines) - 1,
                    chunk_type=current_type,
                    metadata=metadata,
                )
            )

        return chunks

    def _chunk_javascript(self, text: str, metadata: dict[str, Any] | None = None) -> list[Chunk]:
        """Chunk JavaScript/TypeScript code by functions and classes."""
        chunks = []
        lines = text.split("\n")

        # Patterns for JS/TS structure
        class_pattern = re.compile(r"^\s*class\s+(\w+)")
        func_pattern = re.compile(r"^\s*(async\s+)?function\s+(\w+)")
        arrow_func_pattern = re.compile(r"^\s*const\s+(\w+)\s*=\s*.*=>")
        re.compile(r"^\s+(\w+)\s*\(.*\)\s*{")

        current_chunk = []
        current_start = 0
        current_type = "module"
        brace_count = 0

        for i, line in enumerate(lines):
            # Count braces to track nesting
            brace_count += line.count("{") - line.count("}")

            # Check for various function/class patterns
            if (
                class_pattern.match(line)
                or func_pattern.match(line)
                or arrow_func_pattern.match(line)
            ):
                # Save previous chunk if exists
                if current_chunk and len("\n".join(current_chunk)) >= self.min_chunk_size:
                    chunks.append(
                        Chunk(
                            text="\n".join(current_chunk),
                            start_line=current_start,
                            end_line=i - 1,
                            chunk_type=current_type,
                            metadata=metadata,
                        )
                    )
                current_chunk = [line]
                current_start = i
                current_type = "class" if class_pattern.match(line) else "function"

            else:
                current_chunk.append(line)

                # Check if chunk is getting too large
                if len("\n".join(current_chunk)) > self.chunk_size:
                    # Find a good breaking point (closing brace at top level)
                    break_point = self._find_break_point(current_chunk)

                    if break_point > 0:
                        chunk_text = "\n".join(current_chunk[:break_point])
                        chunks.append(
                            Chunk(
                                text=chunk_text,
                                start_line=current_start,
                                end_line=current_start + break_point - 1,
                                chunk_type=current_type,
                                metadata=metadata,
                            )
                        )

                        # Start new chunk
                        current_chunk = current_chunk[break_point:]
                        current_start = current_start + break_point

        # Add final chunk
        if current_chunk and len("\n".join(current_chunk)) >= self.min_chunk_size:
            chunks.append(
                Chunk(
                    text="\n".join(current_chunk),
                    start_line=current_start,
                    end_line=len(lines) - 1,
                    chunk_type=current_type,
                    metadata=metadata,
                )
            )

        return chunks

    def _find_break_point(self, lines: list[str]) -> int:
        """Find a good point to break chunks (empty line or end of block)."""
        # Look for empty lines from the end
        for i in range(len(lines) - 1, len(lines) // 2, -1):
            if not lines[i].strip():
                return i

        # Look for lines with just closing braces
        for i in range(len(lines) - 1, len(lines) // 2, -1):
            if lines[i].strip() in ["}", ");", "},"]:
                return i + 1

        # Default to 3/4 point
        return (len(lines) * 3) // 4


def create_chunker(
    file_path: Path | None = None,
    file_type: str | None = None,
    chunk_size: int = 1000,
    chunk_overlap: int = 200,
    min_chunk_size: int = 100,
) -> TextChunker:
    """Create appropriate chunker based on file type.

    Args:
        file_path: Path to the file (used to determine file type)
        file_type: Explicit file type override
        chunk_size: Target chunk size in characters
        chunk_overlap: Overlap between chunks
        min_chunk_size: Minimum chunk size

    Returns:
        Appropriate chunker instance
    """
    if file_type:
        ext = file_type.lower()
    elif file_path:
        ext = file_path.suffix.lower().lstrip(".")
    else:
        return TextChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, min_chunk_size=min_chunk_size
        )

    # Map extensions to languages
    language_map = {
        "py": "python",
        "js": "javascript",
        "ts": "typescript",
        "jsx": "javascript",
        "tsx": "typescript",
    }

    if ext in language_map:
        return CodeChunker(
            language=language_map[ext],
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chunk_size=min_chunk_size,
        )
    elif ext in ["md", "txt", "rst"]:
        # Use larger chunks for documentation
        return TextChunker(
            chunk_size=max(chunk_size, 1500),
            chunk_overlap=max(chunk_overlap, 300),
            min_chunk_size=min_chunk_size,
        )
    else:
        return TextChunker(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap, min_chunk_size=min_chunk_size
        )
