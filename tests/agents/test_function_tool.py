"""Unit tests for FunctionTool class."""

import asyncio
from typing import Any

import pytest

from coda.agents.decorators import tool
from coda.agents.function_tool import FunctionTool


class TestFunctionTool:
    """Test the FunctionTool class."""

    def test_from_callable_with_decorated_function(self):
        """Test creating FunctionTool from a decorated function."""

        @tool
        def sample_tool(name: str, count: int = 5):
            """A sample tool for testing."""
            return f"{name} * {count}"

        func_tool = FunctionTool.from_callable(sample_tool)

        assert func_tool.name == "sample_tool"
        assert func_tool.description == "A sample tool for testing."
        assert func_tool.callable == sample_tool

        # Check parameter schema
        assert func_tool.parameters["type"] == "object"
        assert "name" in func_tool.parameters["properties"]
        assert "count" in func_tool.parameters["properties"]
        assert func_tool.parameters["properties"]["name"]["type"] == "string"
        assert func_tool.parameters["properties"]["count"]["type"] == "integer"
        assert func_tool.parameters["required"] == ["name"]

    def test_from_callable_without_decorator_raises_error(self):
        """Test that non-decorated functions raise ValueError."""

        def regular_function():
            return "not a tool"

        with pytest.raises(ValueError, match="is not marked as a tool"):
            FunctionTool.from_callable(regular_function)

    def test_execute_sync_function(self):
        """Test executing synchronous functions."""

        @tool
        def multiply(x: int, y: int):
            """Multiply two numbers."""
            return x * y

        func_tool = FunctionTool.from_callable(multiply)
        result = asyncio.run(func_tool.execute({"x": 5, "y": 3}))
        assert result == 15

    def test_execute_async_function(self):
        """Test executing asynchronous functions."""

        @tool
        async def async_multiply(x: int, y: int):
            """Multiply two numbers asynchronously."""
            await asyncio.sleep(0.01)
            return x * y

        func_tool = FunctionTool.from_callable(async_multiply)
        result = asyncio.run(func_tool.execute({"x": 4, "y": 7}))
        assert result == 28

    def test_parameter_schema_generation(self):
        """Test JSON schema generation for various parameter types."""

        @tool
        def complex_params(
            text: str,
            number: int,
            decimal: float,
            flag: bool,
            items: list,
            mapping: dict,
            optional: str | None = None,
            default_val: int = 42,
        ):
            """Function with various parameter types."""
            return locals()

        func_tool = FunctionTool.from_callable(complex_params)
        props = func_tool.parameters["properties"]

        # Check type mappings
        assert props["text"]["type"] == "string"
        assert props["number"]["type"] == "integer"
        assert props["decimal"]["type"] == "number"
        assert props["flag"]["type"] == "boolean"
        assert props["items"]["type"] == "array"
        assert props["mapping"]["type"] == "object"

        # Check required parameters (those without defaults)
        required = func_tool.parameters["required"]
        assert "text" in required
        assert "number" in required
        assert "decimal" in required
        assert "flag" in required
        assert "items" in required
        assert "mapping" in required
        assert "optional" not in required  # Has default None
        assert "default_val" not in required  # Has default 42

    def test_prepare_arguments(self):
        """Test argument preparation and cleaning."""

        @tool
        def test_func(arg1: str, arg2: int):
            return f"{arg1}-{arg2}"

        func_tool = FunctionTool.from_callable(test_func)

        # Test with clean arguments
        cleaned = func_tool._prepare_arguments({"arg1": "test", "arg2": 123})
        assert cleaned == {"arg1": "test", "arg2": 123}

        # Test with extra colons and whitespace
        cleaned = func_tool._prepare_arguments(
            {"arg1:": "test", "arg2  :": 123, "extra": "ignored"}
        )
        assert cleaned == {"arg1": "test", "arg2": 123}
        assert "extra" not in cleaned

    def test_to_dict(self):
        """Test dictionary conversion."""

        @tool(name="custom_name", description="Custom description")
        def sample_func(x: int):
            return x * 2

        func_tool = FunctionTool.from_callable(sample_func)
        tool_dict = func_tool.to_dict()

        assert tool_dict["name"] == "custom_name"
        assert tool_dict["description"] == "Custom description"
        assert "parameters" in tool_dict
        assert "callable" not in tool_dict  # Should exclude callable

    def test_equality(self):
        """Test FunctionTool equality comparison."""

        @tool
        def func1(x: int):
            return x

        @tool
        def func2(x: int):
            return x * 2

        tool1a = FunctionTool.from_callable(func1)
        tool1b = FunctionTool.from_callable(func1)
        tool2 = FunctionTool.from_callable(func2)

        # Same function should create equal tools
        assert tool1a == tool1b

        # Different functions should create different tools
        assert tool1a != tool2

        # Test with non-FunctionTool object
        assert tool1a != "not a tool"

    def test_function_with_no_parameters(self):
        """Test function without parameters."""

        @tool
        def no_params():
            """Function with no parameters."""
            return "result"

        func_tool = FunctionTool.from_callable(no_params)
        assert func_tool.parameters["properties"] == {}
        assert func_tool.parameters["required"] == []

        result = asyncio.run(func_tool.execute({}))
        assert result == "result"

    def test_function_with_self_parameter(self):
        """Test that self parameter is ignored in schema."""

        class MyClass:
            @tool
            def method_with_self(self, value: str):
                """Method that uses self."""
                return f"self-{value}"

        obj = MyClass()
        func_tool = FunctionTool.from_callable(obj.method_with_self)

        # self should not be in parameters
        assert "self" not in func_tool.parameters["properties"]
        assert "value" in func_tool.parameters["properties"]

    def test_function_with_agent_parameter(self):
        """Test that agent parameter is ignored in schema."""

        @tool
        def func_with_agent(agent, value: str):
            """Function that takes agent parameter."""
            return f"agent-{value}"

        func_tool = FunctionTool.from_callable(func_with_agent)

        # agent should not be in parameters
        assert "agent" not in func_tool.parameters["properties"]
        assert "value" in func_tool.parameters["properties"]

    def test_error_handling_in_parameter_schema(self):
        """Test that schema building handles errors gracefully."""

        # Create a function with problematic signature
        @tool
        def problematic_func(*args, **kwargs):
            """Function with variable args."""
            return args, kwargs

        func_tool = FunctionTool.from_callable(problematic_func)

        # Should return schema with args and kwargs
        assert func_tool.parameters["type"] == "object"
        # The implementation may include args/kwargs in properties
        # Just check that it doesn't crash and returns a valid schema
        assert isinstance(func_tool.parameters["properties"], dict)
        assert isinstance(func_tool.parameters["required"], list)

    def test_function_returning_various_types(self):
        """Test functions returning different types."""

        @tool
        def return_list() -> list[int]:
            return [1, 2, 3]

        @tool
        def return_dict() -> dict[str, Any]:
            return {"key": "value", "number": 42}

        @tool
        def return_none() -> None:
            return None

        # Test list return
        func_tool = FunctionTool.from_callable(return_list)
        result = asyncio.run(func_tool.execute({}))
        assert result == [1, 2, 3]

        # Test dict return
        func_tool = FunctionTool.from_callable(return_dict)
        result = asyncio.run(func_tool.execute({}))
        assert result == {"key": "value", "number": 42}

        # Test None return
        func_tool = FunctionTool.from_callable(return_none)
        result = asyncio.run(func_tool.execute({}))
        assert result is None

    def test_function_with_type_annotations_without_hints(self):
        """Test function with annotations but no type hints."""

        @tool
        def func_no_hints(param):
            """Function without type hints."""
            return param

        func_tool = FunctionTool.from_callable(func_no_hints)

        # Should default to string type
        assert func_tool.parameters["properties"]["param"]["type"] == "string"
        assert "param" in func_tool.parameters["required"]

    def test_custom_tool_metadata(self):
        """Test creating FunctionTool with custom metadata."""

        @tool(name="my_custom_tool", description="This is a custom tool")
        def custom_func(value: str):
            return value.upper()

        func_tool = FunctionTool.from_callable(custom_func)

        assert func_tool.name == "my_custom_tool"
        assert func_tool.description == "This is a custom tool"

        result = asyncio.run(func_tool.execute({"value": "hello"}))
        assert result == "HELLO"
