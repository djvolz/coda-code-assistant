"""Unit tests for TreeSitterAnalyzer."""

import tempfile
from pathlib import Path
from textwrap import dedent

import pytest

from coda.base.search.map.tree_sitter_analyzer import (
    CodeElement,
    DefinitionKind,
    FileAnalysis,
    TreeSitterAnalyzer,
)


class TestTreeSitterAnalyzer:
    """Test suite for TreeSitterAnalyzer."""

    def setup_method(self):
        """Set up test fixtures."""
        self.analyzer = TreeSitterAnalyzer()
        self.temp_dir = Path(tempfile.mkdtemp())

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil

        shutil.rmtree(self.temp_dir)

    def create_test_file(self, filename: str, content: str) -> Path:
        """Create a temporary test file."""
        file_path = self.temp_dir / filename
        file_path.write_text(dedent(content).strip())
        return file_path

    def test_language_detection(self):
        """Test language detection from file extensions."""
        assert self.analyzer.get_language_from_path("test.py") == "python"
        assert self.analyzer.get_language_from_path("test.js") == "javascript"
        assert self.analyzer.get_language_from_path("test.ts") == "typescript"
        assert self.analyzer.get_language_from_path("test.rs") == "rust"
        assert self.analyzer.get_language_from_path("test.go") == "go"
        assert self.analyzer.get_language_from_path("test.java") == "java"
        assert self.analyzer.get_language_from_path("test.c") == "c"
        assert self.analyzer.get_language_from_path("test.cpp") == "cpp"
        assert self.analyzer.get_language_from_path("test.unknown") is None

    def test_python_analysis(self):
        """Test Python code analysis."""
        python_code = """
        def hello_world():
            '''A simple greeting function.'''
            return "Hello, World!"

        class Calculator:
            '''A basic calculator class.'''

            def add(self, a, b):
                '''Add two numbers.'''
                return a + b

        from math import sqrt
        import os

        PI = 3.14159
        result = hello_world()
        """

        file_path = self.create_test_file("test.py", python_code)
        analysis = self.analyzer.analyze_file(file_path)

        assert analysis.language == "python"
        assert analysis.file_path == str(file_path)
        assert len(analysis.errors) == 0

        # Check definitions
        def_names = [d.name for d in analysis.definitions]
        assert "hello_world" in def_names
        assert "Calculator" in def_names
        assert "add" in def_names
        assert "PI" in def_names
        assert "result" in def_names

        # Check definition types
        functions = [d for d in analysis.definitions if d.kind == DefinitionKind.FUNCTION]
        classes = [d for d in analysis.definitions if d.kind == DefinitionKind.CLASS]
        variables = [d for d in analysis.definitions if d.kind == DefinitionKind.VARIABLE]

        assert len(functions) >= 2  # hello_world, add
        assert len(classes) >= 1  # Calculator
        assert len(variables) >= 2  # PI, result

        # Check imports
        [i.name for i in analysis.imports]
        assert len(analysis.imports) >= 1  # Should detect at least one import

    def test_javascript_analysis(self):
        """Test JavaScript code analysis."""
        js_code = """
        /**
         * A greeting function
         */
        function greet(name) {
            return `Hello, ${name}!`;
        }

        class Person {
            constructor(name) {
                this.name = name;
            }

            /**
             * Get the person's greeting
             */
            getGreeting() {
                return greet(this.name);
            }
        }

        const age = 25;
        let person = new Person("Alice");
        var message = person.getGreeting();
        """

        file_path = self.create_test_file("test.js", js_code)
        analysis = self.analyzer.analyze_file(file_path)

        assert analysis.language == "javascript"
        assert len(analysis.errors) == 0

        # Check definitions
        def_names = [d.name for d in analysis.definitions]
        assert "greet" in def_names
        assert "Person" in def_names

        # Should detect variable declarations
        variables = [d for d in analysis.definitions if d.kind == DefinitionKind.VARIABLE]
        assert len(variables) >= 1

    def test_rust_analysis(self):
        """Test Rust code analysis."""
        rust_code = """
        use std::collections::HashMap;

        /// A simple struct to represent a point
        pub struct Point {
            x: f64,
            y: f64,
        }

        impl Point {
            /// Create a new point
            pub fn new(x: f64, y: f64) -> Self {
                Point { x, y }
            }

            /// Calculate distance from origin
            pub fn distance_from_origin(&self) -> f64 {
                (self.x * self.x + self.y * self.y).sqrt()
            }
        }

        /// An enumeration of colors
        pub enum Color {
            Red,
            Green,
            Blue,
        }

        fn main() {
            let origin = Point::new(0.0, 0.0);
            println!("Hello, world!");
        }
        """

        file_path = self.create_test_file("test.rs", rust_code)
        analysis = self.analyzer.analyze_file(file_path)

        assert analysis.language == "rust"
        assert len(analysis.errors) == 0

        # Check definitions
        def_names = [d.name for d in analysis.definitions]
        assert "Point" in def_names
        assert "Color" in def_names
        assert "main" in def_names

        # Check for structs and enums
        structs = [d for d in analysis.definitions if d.kind == DefinitionKind.STRUCT]
        enums = [d for d in analysis.definitions if d.kind == DefinitionKind.ENUM]
        functions = [d for d in analysis.definitions if d.kind == DefinitionKind.FUNCTION]

        assert len(structs) >= 1
        assert len(enums) >= 1
        assert len(functions) >= 1

    def test_documentation_extraction_python(self):
        """Test documentation extraction for Python."""
        python_code = '''
        def documented_function():
            """This is a docstring for the function."""
            pass

        class DocumentedClass:
            """
            This is a multi-line docstring
            for the class.
            """
            pass
        '''

        file_path = self.create_test_file("test_docs.py", python_code)
        self.analyzer.analyze_file(file_path)

        # Test structured analysis which includes documentation
        structured = self.analyzer.get_structured_analysis(file_path)

        assert "functions" in structured
        assert "classes" in structured

        # Find the documented function
        functions = structured["functions"]
        documented_func = next((f for f in functions if f["name"] == "documented_function"), None)
        assert documented_func is not None
        assert documented_func["docstring"] is not None
        assert "docstring for the function" in documented_func["docstring"]

        # Find the documented class
        classes = structured["classes"]
        documented_class = next((c for c in classes if c["name"] == "DocumentedClass"), None)
        assert documented_class is not None
        assert documented_class["docstring"] is not None
        assert "multi-line docstring" in documented_class["docstring"]

    def test_analyze_directory(self):
        """Test directory analysis."""
        # Create multiple test files
        self.create_test_file(
            "module1.py",
            """
        def func1():
            pass
        """,
        )

        self.create_test_file(
            "module2.js",
            """
        function func2() {
            return 42;
        }
        """,
        )

        self.create_test_file("readme.txt", "This is not a code file")

        analyses = self.analyzer.analyze_directory(self.temp_dir)

        # Should analyze Python and JavaScript files, but not txt
        assert len(analyses) == 2

        python_files = [
            path for path, analysis in analyses.items() if analysis.language == "python"
        ]
        js_files = [
            path for path, analysis in analyses.items() if analysis.language == "javascript"
        ]

        assert len(python_files) == 1
        assert len(js_files) == 1

    def test_find_definition(self):
        """Test finding definitions across files."""
        # Create files with same function names
        self.create_test_file(
            "file1.py",
            """
        def common_function():
            pass
        """,
        )

        self.create_test_file(
            "file2.py",
            """
        def common_function():
            return 42

        def another_function():
            pass
        """,
        )

        analyses = self.analyzer.analyze_directory(self.temp_dir)
        results = self.analyzer.find_definition("common_function", analyses)

        # Should find the function in both files
        assert len(results) == 2
        assert all(r.name == "common_function" for r in results)
        assert all(r.kind == DefinitionKind.FUNCTION for r in results)

    def test_get_definitions_summary(self):
        """Test getting summary of definitions by kind."""
        self.create_test_file(
            "mixed.py",
            """
        class MyClass:
            def method1(self):
                pass

            def method2(self):
                pass

        def function1():
            pass

        def function2():
            pass

        variable1 = 10
        variable2 = "hello"
        """,
        )

        analyses = self.analyzer.analyze_directory(self.temp_dir)
        summary = self.analyzer.get_definitions_summary(analyses)

        assert summary.get("function", 0) >= 2  # function1, function2, method1, method2
        assert summary.get("class", 0) >= 1  # MyClass
        assert summary.get("variable", 0) >= 2  # variable1, variable2

    def test_get_file_dependencies(self):
        """Test extracting file dependencies."""
        python_code = """
        import os
        from pathlib import Path
        import sys
        """

        file_path = self.create_test_file("deps.py", python_code)
        analysis = self.analyzer.analyze_file(file_path)
        deps = self.analyzer.get_file_dependencies(analysis)

        # Should extract import names
        assert len(deps) >= 1

    def test_unsupported_language(self):
        """Test handling of unsupported file types."""
        file_path = self.create_test_file("test.unknown", "some content")
        analysis = self.analyzer.analyze_file(file_path)

        assert analysis.language == "unknown"
        assert len(analysis.errors) == 1
        assert "Unsupported language" in analysis.errors[0]

    def test_file_read_error(self):
        """Test handling of file read errors."""
        non_existent = self.temp_dir / "non_existent.py"
        analysis = self.analyzer.analyze_file(non_existent)

        assert analysis.language == "python"  # Detected from extension
        assert len(analysis.errors) == 1
        assert "Error reading file" in analysis.errors[0]

    def test_structured_analysis(self):
        """Test structured analysis output."""
        python_code = """
        '''Module docstring.'''
        import os

        class Calculator:
            '''A calculator class.'''

            def add(self, a, b):
                '''Add two numbers.'''
                return a + b

        def main():
            calc = Calculator()
            result = calc.add(1, 2)
        """

        file_path = self.create_test_file("structured.py", python_code)
        structured = self.analyzer.get_structured_analysis(file_path)

        # Check structure
        assert "file_info" in structured
        assert "classes" in structured
        assert "functions" in structured
        assert "variables" in structured
        assert "imports" in structured

        # Check file info
        assert structured["file_info"]["language"] == "python"
        assert structured["file_info"]["path"] == str(file_path)

        # Check classes
        assert len(structured["classes"]) >= 1
        calc_class = structured["classes"][0]
        assert calc_class["name"] == "Calculator"

        # Check functions
        assert len(structured["functions"]) >= 2  # add, main

        # Check imports
        assert len(structured["imports"]) >= 1

    def test_supported_languages(self):
        """Test getting supported languages."""
        languages = self.analyzer.get_supported_languages()

        assert isinstance(languages, list)
        assert "python" in languages
        assert "javascript" in languages
        assert "rust" in languages
        assert "go" in languages
        assert len(languages) >= 10  # Should support many languages

    def test_language_extensions(self):
        """Test getting extensions for languages."""
        python_exts = self.analyzer.get_language_extensions("python")
        assert ".py" in python_exts

        js_exts = self.analyzer.get_language_extensions("javascript")
        assert ".js" in js_exts
        assert ".jsx" in js_exts

        unknown_exts = self.analyzer.get_language_extensions("unknown")
        assert unknown_exts == []


@pytest.mark.unit
class TestCodeElement:
    """Test suite for CodeElement dataclass."""

    def test_code_element_creation(self):
        """Test creating a code element."""
        element = CodeElement(
            name="test_function",
            kind=DefinitionKind.FUNCTION,
            line=10,
            column=5,
            file_path="/path/to/file.py",
            language="python",
        )

        assert element.name == "test_function"
        assert element.kind == DefinitionKind.FUNCTION
        assert element.line == 10
        assert element.column == 5
        assert element.file_path == "/path/to/file.py"
        assert element.language == "python"
        assert element.is_definition is True
        assert element.modifiers == []
        assert element.parameters == []

    def test_code_element_string_representation(self):
        """Test string representation of code element."""
        element = CodeElement(
            name="MyClass",
            kind=DefinitionKind.CLASS,
            line=1,
            column=0,
            file_path="test.py",
            language="python",
        )

        assert str(element) == "MyClass (class)"
        assert "MyClass" in repr(element)
        assert "CLASS" in repr(element)


@pytest.mark.unit
class TestFileAnalysis:
    """Test suite for FileAnalysis dataclass."""

    def test_file_analysis_creation(self):
        """Test creating a file analysis."""
        analysis = FileAnalysis(
            file_path="/path/to/file.py",
            language="python",
            definitions=[],
            references=[],
            imports=[],
            errors=[],
        )

        assert analysis.file_path == "/path/to/file.py"
        assert analysis.language == "python"
        assert analysis.definitions == []
        assert analysis.references == []
        assert analysis.imports == []
        assert analysis.errors == []


@pytest.mark.unit
class TestDefinitionKind:
    """Test suite for DefinitionKind enum."""

    def test_definition_kinds(self):
        """Test definition kind enum values."""
        assert DefinitionKind.FUNCTION.value == "function"
        assert DefinitionKind.CLASS.value == "class"
        assert DefinitionKind.METHOD.value == "method"
        assert DefinitionKind.VARIABLE.value == "variable"
        assert DefinitionKind.CONSTANT.value == "constant"
        assert DefinitionKind.INTERFACE.value == "interface"
        assert DefinitionKind.MODULE.value == "module"
        assert DefinitionKind.STRUCT.value == "struct"
        assert DefinitionKind.ENUM.value == "enum"
        assert DefinitionKind.TRAIT.value == "trait"
        assert DefinitionKind.MACRO.value == "macro"
        assert DefinitionKind.IMPORT.value == "import"
        assert DefinitionKind.UNKNOWN.value == "unknown"
