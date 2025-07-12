"""Test that constants module maintains independence from other Coda modules."""

import ast
from pathlib import Path


def get_imports_from_file(filepath):
    """Extract all import statements from a Python file."""
    with open(filepath) as f:
        tree = ast.parse(f.read())

    imports = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            imports.append(module)

    return imports


def test_constants_module_independence():
    """Ensure constants module has no Coda dependencies."""
    constants_dir = Path(__file__).parent.parent / "coda" / "constants"

    # Files to check
    files_to_check = [
        constants_dir / "__init__.py",
        constants_dir / "definitions.py",
        constants_dir / "models.py",
    ]

    forbidden_imports = [
        "coda.",  # No imports from coda package
        # No imports from other coda modules
    ]

    all_good = True

    for filepath in files_to_check:
        if not filepath.exists():
            print(f"❌ File not found: {filepath}")
            all_good = False
            continue

        imports = get_imports_from_file(filepath)

        for imp in imports:
            # Skip relative imports within the module
            if imp.startswith(".") or imp == "":
                continue

            # Check for forbidden imports
            for forbidden in forbidden_imports:
                if imp.startswith(forbidden) and not imp.startswith("coda.constants"):
                    print(f"❌ Forbidden import in {filepath.name}: {imp}")
                    all_good = False

            # Check for non-stdlib imports (basic check)
            if "." in imp and not imp.startswith("coda.constants"):
                # Could be a third-party import
                base_module = imp.split(".")[0]
                stdlib_modules = {
                    "os",
                    "sys",
                    "pathlib",
                    "typing",
                    "enum",
                    "collections",
                    "json",
                    "yaml",
                    "toml",
                    "dataclasses",
                    "abc",
                    "functools",
                    "itertools",
                    "datetime",
                    "time",
                    "re",
                    "math",
                    "random",
                    "warnings",
                    "traceback",
                    "inspect",
                    "importlib",
                }
                if base_module not in stdlib_modules:
                    print(f"⚠️  Possible external dependency in {filepath.name}: {imp}")

    if all_good:
        print("✅ Constants module has no Coda dependencies")
        print("✅ Module can be safely copied to other projects")
    else:
        print("❌ Constants module has dependencies that need to be removed")

    return all_good


def test_constants_immutability():
    """Test that constants cannot be modified."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from coda.constants import UI

    # Test immutability
    try:
        UI.MAX_LINE_LENGTH = 100
        print("❌ Constants are mutable - this is a problem!")
        return False
    except AttributeError:
        print("✅ Constants are properly immutable")
        return True


def test_constants_api():
    """Test the constants API works as documented."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from coda.constants import (
        API,
        APP,
        DEFAULTS,
        ERRORS,
        PROVIDERS,
        UI,
    )
    from coda.constants.models import (
        ProviderType,
        ThemeType,
    )

    tests_passed = True

    # Test basic access
    assert APP.NAME == "coda"
    assert UI.MAX_LINE_LENGTH == 80
    assert API.TIMEOUT == 30
    assert DEFAULTS.PROVIDER == "oci_genai"

    # Test lists
    assert isinstance(PROVIDERS.ALL, list)
    assert "ollama" in PROVIDERS.ALL

    # Test enums
    assert ProviderType.OLLAMA.value == "ollama"
    assert ThemeType.DARK.value == "dark"

    # Test error formatting
    error = ERRORS.PROVIDER_NOT_FOUND.format(provider="test")
    assert "test" in error

    print("✅ Constants API works as documented")
    return tests_passed


if __name__ == "__main__":
    print("Testing Constants Module Independence...\n")

    test1 = test_constants_module_independence()
    print()

    test2 = test_constants_immutability()
    print()

    test3 = test_constants_api()
    print()

    if test1 and test2 and test3:
        print("\n✅ All tests passed! Constants module is ready.")
    else:
        print("\n❌ Some tests failed. Please fix the issues.")
        exit(1)
