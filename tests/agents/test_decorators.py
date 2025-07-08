"""Unit tests for agent decorators."""

import asyncio
import inspect

import pytest

from coda.agents.decorators import tool


class TestToolDecorator:
    """Test the @tool decorator functionality."""

    def test_basic_decoration(self):
        """Test basic function decoration."""

        @tool
        def sample_function(x, y):
            """Add two numbers."""
            return x + y

        # Function should still work normally
        assert sample_function(2, 3) == 5

        # Check metadata
        assert hasattr(sample_function, "_is_tool")
        assert sample_function._is_tool is True
        assert sample_function._tool_name == "sample_function"
        assert sample_function._tool_description == "Add two numbers."

    def test_custom_name_and_description(self):
        """Test decorator with custom name and description."""

        @tool(name="custom_tool", description="Custom description")
        def another_function():
            return "result"

        assert another_function._tool_name == "custom_tool"
        assert another_function._tool_description == "Custom description"
        assert another_function() == "result"

    def test_no_docstring(self):
        """Test decorator on function without docstring."""

        @tool
        def no_doc_function():
            return 42

        assert no_doc_function._tool_description == ""
        assert no_doc_function() == 42

    def test_preserves_function_attributes(self):
        """Test that decorator preserves original function attributes."""

        @tool
        def original_function(a, b=10):
            """Original docstring."""
            return a + b

        # Check that function name and docstring are preserved
        assert original_function.__name__ == "original_function"
        assert original_function.__doc__ == "Original docstring."

        # Check that function signature is preserved
        sig = inspect.signature(original_function)
        assert "a" in sig.parameters
        assert "b" in sig.parameters
        assert sig.parameters["b"].default == 10

    def test_async_function_decoration(self):
        """Test decoration of async functions."""

        @tool
        async def async_function(value):
            """Async function that processes value."""
            await asyncio.sleep(0.01)
            return value * 2

        # Check metadata
        assert async_function._is_tool is True
        assert async_function._tool_name == "async_function"
        assert async_function._tool_description == "Async function that processes value."

        # Test async execution
        result = asyncio.run(async_function(5))
        assert result == 10

    def test_mixed_decorator_syntax(self):
        """Test both @tool and @tool() syntax."""

        # Without parentheses
        @tool
        def func1():
            return 1

        # With empty parentheses
        @tool()
        def func2():
            return 2

        # With arguments
        @tool(name="func3_custom")
        def func3():
            return 3

        assert func1._tool_name == "func1"
        assert func2._tool_name == "func2"
        assert func3._tool_name == "func3_custom"

        assert func1() == 1
        assert func2() == 2
        assert func3() == 3

    def test_complex_function_signatures(self):
        """Test decorator with complex function signatures."""

        @tool
        def complex_function(pos_arg, *args, kw_arg=None, **kwargs):
            """Function with complex signature."""
            return {"pos_arg": pos_arg, "args": args, "kw_arg": kw_arg, "kwargs": kwargs}

        result = complex_function(1, 2, 3, kw_arg="test", extra="data")
        assert result["pos_arg"] == 1
        assert result["args"] == (2, 3)
        assert result["kw_arg"] == "test"
        assert result["kwargs"] == {"extra": "data"}

    def test_class_method_decoration(self):
        """Test decorating class methods."""

        class MyClass:
            @tool
            def instance_method(self, value):
                """Instance method tool."""
                return value * 2

            @classmethod
            @tool
            def class_method(cls, value):
                """Class method tool."""
                return value * 3

            @staticmethod
            @tool
            def static_method(value):
                """Static method tool."""
                return value * 4

        obj = MyClass()

        # Test instance method
        assert obj.instance_method(5) == 10
        assert obj.instance_method._tool_name == "instance_method"

        # Test class method
        assert MyClass.class_method(5) == 15
        assert MyClass.class_method._tool_name == "class_method"

        # Test static method
        assert MyClass.static_method(5) == 20
        assert MyClass.static_method._tool_name == "static_method"

    def test_multiline_docstring(self):
        """Test handling of multiline docstrings."""

        @tool
        def multiline_doc():
            """
            This is a function with a multiline docstring.

            It has multiple paragraphs and formatting.
            - Point 1
            - Point 2

            Returns:
                str: A result
            """
            return "result"

        # Should preserve full docstring
        assert "multiple paragraphs" in multiline_doc._tool_description
        assert "Point 1" in multiline_doc._tool_description

    def test_exception_handling(self):
        """Test that decorated functions can still raise exceptions."""

        @tool
        def error_function():
            """Function that raises an error."""
            raise ValueError("Test error")

        with pytest.raises(ValueError, match="Test error"):
            error_function()

    def test_return_value_preservation(self):
        """Test that various return values are preserved."""

        @tool
        def return_none():
            return None

        @tool
        def return_list():
            return [1, 2, 3]

        @tool
        def return_dict():
            return {"key": "value"}

        @tool
        def return_tuple():
            return (1, "two", 3.0)

        assert return_none() is None
        assert return_list() == [1, 2, 3]
        assert return_dict() == {"key": "value"}
        assert return_tuple() == (1, "two", 3.0)

    def test_nested_decoration(self):
        """Test decorator with other decorators."""

        def other_decorator(func):
            def wrapper(*args, **kwargs):
                return f"wrapped: {func(*args, **kwargs)}"

            return wrapper

        @tool
        @other_decorator
        def decorated_function():
            return "original"

        assert decorated_function() == "wrapped: original"
        assert hasattr(decorated_function, "_is_tool")

    def test_generator_function(self):
        """Test decorating generator functions."""

        @tool
        def generator_tool(n):
            """Generator that yields numbers."""
            yield from range(n)

        result = list(generator_tool(3))
        assert result == [0, 1, 2]
        assert generator_tool._tool_name == "generator_tool"

    def test_async_generator_function(self):
        """Test decorating async generator functions."""

        @tool
        async def async_generator_tool(n):
            """Async generator that yields numbers."""
            for i in range(n):
                await asyncio.sleep(0.01)
                yield i

        async def collect_results():
            results = []
            async for value in async_generator_tool(3):
                results.append(value)
            return results

        result = asyncio.run(collect_results())
        assert result == [0, 1, 2]
        assert async_generator_tool._tool_name == "async_generator_tool"
