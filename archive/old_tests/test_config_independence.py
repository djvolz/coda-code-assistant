"""Test that config module maintains independence from other Coda modules."""

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


def test_config_module_independence():
    """Ensure config module has no Coda dependencies."""
    config_dir = Path(__file__).parent.parent / "coda" / "base" / "config"

    # Files to check
    files_to_check = [
        config_dir / "__init__.py",
        config_dir / "manager.py",
        config_dir / "models.py",
    ]

    forbidden_imports = [
        "coda.",  # No imports from coda package
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
                if imp.startswith(forbidden) and not imp.startswith("coda.base.config"):
                    print(f"❌ Forbidden import in {filepath.name}: {imp}")
                    all_good = False

            # Check for non-stdlib imports (basic check)
            if "." in imp and not imp.startswith("coda.base.config"):
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
                    "tomllib",
                    "tomli",
                    "tomli_w",
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
                    "configparser",
                    "tempfile",
                }
                if base_module not in stdlib_modules:
                    print(f"⚠️  Possible external dependency in {filepath.name}: {imp}")

    if all_good:
        print("✅ Config module has no Coda dependencies")
        print("✅ Module can be safely copied to other projects")
    else:
        print("❌ Config module has dependencies that need to be removed")

    return all_good


def test_config_basic_functionality():
    """Test basic config functionality."""
    import sys

    sys.path.insert(0, str(Path(__file__).parent.parent))

    from coda.base.config import Config

    # Test basic functionality
    config = Config(
        app_name="test",
        defaults={
            "debug": False,
            "server": {"host": "localhost", "port": 8080},
        },
    )

    assert not config.get_bool("debug")
    assert config.get_string("server.host") == "localhost"
    assert config.get_int("server.port") == 8080

    # Test runtime set
    config.set("test.value", 42)
    assert config.get_int("test.value") == 42

    print("✅ Config basic functionality works")
    return True


def test_config_copy_paste():
    """Test that config module works when copy-pasted."""
    import shutil
    import subprocess
    import tempfile

    config_dir = Path(__file__).parent.parent / "coda" / "base" / "config"

    with tempfile.TemporaryDirectory() as tmpdir:
        # Copy config module
        dest = Path(tmpdir) / "config"
        shutil.copytree(config_dir, dest)

        # Create test script
        test_script = Path(tmpdir) / "test_standalone.py"
        test_script.write_text(
            """
from config import Config

config = Config(
    app_name="test",
    defaults={"key": "value"}
)

assert config.get_string("key") == "value"
print("✓ Standalone config works!")
"""
        )

        # Run test
        result = subprocess.run(
            [sys.executable, str(test_script)], cwd=tmpdir, capture_output=True, text=True
        )

        if result.returncode == 0:
            print("✅ Config module works when copy-pasted")
            return True
        else:
            print(f"❌ Copy-paste test failed: {result.stderr}")
            return False


if __name__ == "__main__":
    import sys

    print("Testing Config Module Independence...\n")

    test1 = test_config_module_independence()
    print()

    test2 = test_config_basic_functionality()
    print()

    test3 = test_config_copy_paste()
    print()

    if test1 and test2 and test3:
        print("\n✅ All tests passed! Config module is ready.")
    else:
        print("\n❌ Some tests failed. Please fix the issues.")
        sys.exit(1)
