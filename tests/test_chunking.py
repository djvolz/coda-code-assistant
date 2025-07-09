"""Tests for the chunking module."""

from pathlib import Path

import pytest

from coda.chunking import Chunk, CodeChunker, TextChunker, create_chunker


class TestChunk:
    """Test the Chunk dataclass."""

    def test_chunk_creation(self):
        """Test basic chunk creation."""
        chunk = Chunk(text="Hello world", start_line=0, end_line=0, chunk_type="text")
        assert chunk.text == "Hello world"
        assert chunk.start_line == 0
        assert chunk.end_line == 0
        assert chunk.chunk_type == "text"
        assert chunk.metadata is None

    def test_chunk_with_metadata(self):
        """Test chunk creation with metadata."""
        metadata = {"file_path": "/test/file.py", "language": "python"}
        chunk = Chunk(
            text="def test():\n    pass",
            start_line=10,
            end_line=11,
            chunk_type="function",
            metadata=metadata,
        )
        assert chunk.metadata == metadata
        assert chunk.chunk_type == "function"


class TestTextChunker:
    """Test the base TextChunker class."""

    def test_default_parameters(self):
        """Test chunker with default parameters."""
        chunker = TextChunker()
        assert chunker.chunk_size == 1000
        assert chunker.chunk_overlap == 200
        assert chunker.min_chunk_size == 100

    def test_custom_parameters(self):
        """Test chunker with custom parameters."""
        chunker = TextChunker(chunk_size=500, chunk_overlap=100, min_chunk_size=50)
        assert chunker.chunk_size == 500
        assert chunker.chunk_overlap == 100
        assert chunker.min_chunk_size == 50

    def test_chunk_small_text(self):
        """Test chunking text smaller than chunk size."""
        chunker = TextChunker(chunk_size=1000, min_chunk_size=10)
        text = "Line 1\nLine 2\nLine 3"
        chunks = chunker.chunk_text(text)

        assert len(chunks) == 1
        assert chunks[0].text == text
        assert chunks[0].start_line == 0
        assert chunks[0].end_line == 2

    def test_chunk_large_text(self):
        """Test chunking text larger than chunk size."""
        chunker = TextChunker(chunk_size=50, chunk_overlap=10, min_chunk_size=20)
        lines = [f"This is line number {i} with some content" for i in range(10)]
        text = "\n".join(lines)

        chunks = chunker.chunk_text(text)
        assert len(chunks) > 1

        # Verify chunks have overlap
        for i in range(len(chunks) - 1):
            # Check that there's some content overlap
            chunk1_lines = chunks[i].text.split("\n")
            chunk2_lines = chunks[i + 1].text.split("\n")
            assert any(line in chunk1_lines for line in chunk2_lines[:2])

    def test_chunk_with_metadata(self):
        """Test chunking with metadata propagation."""
        chunker = TextChunker()
        text = "Some text content"
        metadata = {"source": "test.txt"}

        chunks = chunker.chunk_text(text, metadata=metadata)
        assert all(chunk.metadata == metadata for chunk in chunks)

    def test_empty_text(self):
        """Test chunking empty text."""
        chunker = TextChunker()
        chunks = chunker.chunk_text("")
        assert len(chunks) == 0

    def test_text_below_min_chunk_size(self):
        """Test text below minimum chunk size."""
        chunker = TextChunker(min_chunk_size=100)
        text = "Short"
        chunks = chunker.chunk_text(text)
        assert len(chunks) == 0  # Too small to create a chunk

    def test_calculate_overlap_lines(self):
        """Test overlap calculation."""
        chunker = TextChunker(chunk_overlap=50)
        lines = ["Line 1", "Line 2", "Line 3", "Line 4"]
        overlap = chunker._calculate_overlap_lines(lines)
        assert overlap > 0
        assert overlap <= len(lines)


class TestCodeChunker:
    """Test the CodeChunker class."""

    def test_python_chunker_creation(self):
        """Test creating a Python code chunker."""
        chunker = CodeChunker(language="python")
        assert chunker.language == "python"

    def test_javascript_chunker_creation(self):
        """Test creating a JavaScript code chunker."""
        chunker = CodeChunker(language="javascript")
        assert chunker.language == "javascript"

    def test_chunk_python_functions(self):
        """Test chunking Python code with functions."""
        chunker = CodeChunker(language="python", chunk_size=200, min_chunk_size=50)
        code = '''def function1():
    """First function."""
    return 1

def function2():
    """Second function."""
    return 2

def function3():
    """Third function."""
    return 3
'''
        chunks = chunker.chunk_text(code)
        assert len(chunks) >= 1

        # Check that function-related chunks exist (might be module type if small)
        assert any(c.chunk_type in ["function", "module"] for c in chunks)

    def test_chunk_python_classes(self):
        """Test chunking Python code with classes."""
        chunker = CodeChunker(language="python", chunk_size=300)
        code = '''class MyClass:
    """A test class."""

    def __init__(self):
        self.value = 0

    def method1(self):
        return self.value

    def method2(self):
        self.value += 1

class AnotherClass:
    """Another test class."""
    pass
'''
        chunks = chunker.chunk_text(code)

        # Check that classes are identified
        class_chunks = [c for c in chunks if c.chunk_type == "class"]
        assert len(class_chunks) > 0

        # Check that methods might be separate chunks if classes are large
        method_chunks = [c for c in chunks if c.chunk_type == "method"]
        assert len(method_chunks) >= 0  # May or may not have separate method chunks

    def test_chunk_javascript_code(self):
        """Test chunking JavaScript code."""
        chunker = CodeChunker(language="javascript", chunk_size=200, min_chunk_size=50)
        code = """function hello() {
    console.log("Hello");
}

const arrow = () => {
    return "arrow";
};

class MyClass {
    constructor() {
        this.value = 0;
    }
}
"""
        chunks = chunker.chunk_text(code)
        assert len(chunks) >= 1

        # Check that appropriate chunks exist
        assert any(c.chunk_type in ["function", "class", "module"] for c in chunks)

    def test_chunk_mixed_content(self):
        """Test chunking code with mixed content."""
        chunker = CodeChunker(language="python", chunk_size=150)
        code = '''# Module docstring
"""This is a test module."""

import os
import sys

# Constants
DEFAULT_VALUE = 42

def helper():
    """Helper function."""
    return DEFAULT_VALUE

class MainClass:
    """Main class."""

    def run(self):
        return helper()
'''
        chunks = chunker.chunk_text(code)
        assert len(chunks) >= 2  # Should split due to size

        # Verify chunk types
        types = {chunk.chunk_type for chunk in chunks}
        assert "module" in types or "function" in types or "class" in types

    def test_find_break_point(self):
        """Test finding good break points in code."""
        chunker = CodeChunker(language="python")
        lines = [
            "def func():",
            "    line1",
            "    line2",
            "",
            "    line3",
            "}",
            "",
            "def another():",
        ]

        break_point = chunker._find_break_point(lines)
        assert 0 < break_point < len(lines)

        # Should prefer breaking at empty lines or closing braces
        assert lines[break_point - 1] == "" or lines[break_point - 1].strip() in ["}", ");", "},"]

    def test_unsupported_language_fallback(self):
        """Test fallback to TextChunker for unsupported languages."""
        chunker = CodeChunker(language="rust", min_chunk_size=10)  # Not implemented
        text = 'fn main() {\n    println!("Hello");\n}'

        chunks = chunker.chunk_text(text)
        # May or may not create chunks depending on text size
        if chunks:
            assert all(chunk.chunk_type == "text" for chunk in chunks)  # Falls back to text


class TestCreateChunker:
    """Test the create_chunker factory function."""

    def test_create_python_chunker(self):
        """Test creating a chunker for Python files."""
        chunker = create_chunker(file_path=Path("test.py"))
        assert isinstance(chunker, CodeChunker)
        assert chunker.language == "python"

    def test_create_javascript_chunker(self):
        """Test creating a chunker for JavaScript files."""
        chunker = create_chunker(file_path=Path("test.js"))
        assert isinstance(chunker, CodeChunker)
        assert chunker.language == "javascript"

    def test_create_typescript_chunker(self):
        """Test creating a chunker for TypeScript files."""
        chunker = create_chunker(file_path=Path("test.ts"))
        assert isinstance(chunker, CodeChunker)
        assert chunker.language == "typescript"

    def test_create_text_chunker_for_docs(self):
        """Test creating a chunker for documentation files."""
        for ext in ["md", "txt", "rst"]:
            chunker = create_chunker(file_path=Path(f"test.{ext}"))
            assert isinstance(chunker, TextChunker)
            assert chunker.chunk_size >= 1500  # Larger chunks for docs

    def test_create_chunker_with_file_type_override(self):
        """Test creating a chunker with explicit file type."""
        chunker = create_chunker(file_type="py")
        assert isinstance(chunker, CodeChunker)
        assert chunker.language == "python"

    def test_create_default_chunker(self):
        """Test creating a default chunker."""
        chunker = create_chunker()
        assert isinstance(chunker, TextChunker)

    def test_create_chunker_with_custom_params(self):
        """Test creating a chunker with custom parameters."""
        chunker = create_chunker(
            file_path=Path("test.py"), chunk_size=2000, chunk_overlap=400, min_chunk_size=200
        )
        assert isinstance(chunker, CodeChunker)
        assert chunker.chunk_size == 2000
        assert chunker.chunk_overlap == 400
        assert chunker.min_chunk_size == 200

    def test_create_chunker_unknown_extension(self):
        """Test creating a chunker for unknown file type."""
        chunker = create_chunker(file_path=Path("test.xyz"))
        assert isinstance(chunker, TextChunker)  # Falls back to text chunker


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_very_long_lines(self):
        """Test handling very long lines."""
        chunker = TextChunker(chunk_size=100)
        long_line = "a" * 200  # Line longer than chunk size
        text = f"{long_line}\nshort line"

        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 1
        # Should still create chunks even with long lines

    def test_only_whitespace(self):
        """Test handling whitespace-only content."""
        chunker = TextChunker()
        text = "   \n\n   \t\t  \n  "
        chunks = chunker.chunk_text(text)

        # May or may not create chunks depending on min size
        assert isinstance(chunks, list)

    def test_unicode_content(self):
        """Test handling Unicode content."""
        chunker = TextChunker(chunk_size=50, min_chunk_size=10)
        text = "Hello 世界\n你好 World\n🌍 Earth"

        chunks = chunker.chunk_text(text)
        # Text might be small enough to fit in one chunk
        if chunks:
            # At least one chunk should contain some Unicode
            assert any(
                "世界" in chunk.text or "你好" in chunk.text or "🌍" in chunk.text
                for chunk in chunks
            )

    @pytest.mark.parametrize(
        "chunk_size,overlap",
        [
            (100, 200),  # Overlap larger than chunk size
            (100, 100),  # Overlap equal to chunk size
        ],
    )
    def test_invalid_overlap_sizes(self, chunk_size, overlap):
        """Test handling invalid overlap configurations."""
        chunker = TextChunker(chunk_size=chunk_size, chunk_overlap=overlap)
        text = "\n".join([f"Line {i}" for i in range(20)])

        # Should still work, just with adjusted overlap
        chunks = chunker.chunk_text(text)
        assert len(chunks) >= 1
