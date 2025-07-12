"""
Test module independence for all base modules.

This is the most critical test - ensures base modules don't depend on higher layers.
"""

import ast
from pathlib import Path


def get_imports_from_file(filepath: Path) -> set[str]:
    """Extract all import statements from a Python file."""
    imports = set()

    try:
        with open(filepath, encoding="utf-8") as f:
            tree = ast.parse(f.read(), filename=str(filepath))
    except Exception:
        # Skip files that can't be parsed
        return imports

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)

    return imports


def get_all_imports_in_module(module_path: Path) -> set[str]:
    """Get all imports used anywhere in a module."""
    all_imports = set()

    for py_file in module_path.rglob("*.py"):
        # Skip test files and __pycache__
        if "__pycache__" in str(py_file) or "test_" in py_file.name:
            continue

        file_imports = get_imports_from_file(py_file)
        all_imports.update(file_imports)

    return all_imports


def check_forbidden_imports(imports: set[str], module_name: str) -> list[str]:
    """Check if any imports are from forbidden modules."""
    forbidden_patterns = [
        "coda.services",
        "coda.apps",
    ]

    violations = []
    for imp in imports:
        for forbidden in forbidden_patterns:
            if imp.startswith(forbidden):
                violations.append(f"{module_name}: Forbidden import '{imp}'")

    return violations


def test_config_module_independence():
    """Test that config module has no service/app dependencies."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base" / "config"
    imports = get_all_imports_in_module(base_path)

    violations = check_forbidden_imports(imports, "config")
    assert not violations, "\n".join(violations)

    # Check that it only imports from allowed modules
    coda_imports = {imp for imp in imports if imp.startswith("coda.")}
    allowed_prefixes = ["coda.base."]

    for imp in coda_imports:
        assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
            f"config: Unexpected import '{imp}'"
        )


def test_theme_module_independence():
    """Test that theme module has no service/app dependencies."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base" / "theme"
    imports = get_all_imports_in_module(base_path)

    violations = check_forbidden_imports(imports, "theme")
    assert not violations, "\n".join(violations)

    # Check that it only imports from allowed modules
    coda_imports = {imp for imp in imports if imp.startswith("coda.")}
    allowed_prefixes = ["coda.base."]

    for imp in coda_imports:
        assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
            f"theme: Unexpected import '{imp}'"
        )


def test_providers_module_independence():
    """Test that providers module has no service/app dependencies."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base" / "providers"
    imports = get_all_imports_in_module(base_path)

    violations = check_forbidden_imports(imports, "providers")
    assert not violations, "\n".join(violations)

    # Check that it only imports from allowed modules
    coda_imports = {imp for imp in imports if imp.startswith("coda.")}
    allowed_prefixes = ["coda.base."]

    for imp in coda_imports:
        assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
            f"providers: Unexpected import '{imp}'"
        )


def test_search_module_independence():
    """Test that search module has no service/app dependencies."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base" / "search"
    imports = get_all_imports_in_module(base_path)

    violations = check_forbidden_imports(imports, "search")
    assert not violations, "\n".join(violations)

    # Check that it only imports from allowed modules
    coda_imports = {imp for imp in imports if imp.startswith("coda.")}
    allowed_prefixes = ["coda.base."]

    for imp in coda_imports:
        assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
            f"search: Unexpected import '{imp}'"
        )


def test_session_module_independence():
    """Test that session module has no service/app dependencies."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base" / "session"
    imports = get_all_imports_in_module(base_path)

    violations = check_forbidden_imports(imports, "session")
    assert not violations, "\n".join(violations)

    # Check that it only imports from allowed modules
    coda_imports = {imp for imp in imports if imp.startswith("coda.")}
    allowed_prefixes = ["coda.base."]

    for imp in coda_imports:
        assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
            f"session: Unexpected import '{imp}'"
        )


def test_observability_module_independence():
    """Test that observability module has no service/app dependencies."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base" / "observability"
    imports = get_all_imports_in_module(base_path)

    violations = check_forbidden_imports(imports, "observability")
    assert not violations, "\n".join(violations)

    # Check that it only imports from allowed modules
    coda_imports = {imp for imp in imports if imp.startswith("coda.")}
    allowed_prefixes = ["coda.base."]

    for imp in coda_imports:
        assert any(imp.startswith(prefix) for prefix in allowed_prefixes), (
            f"observability: Unexpected import '{imp}'"
        )


def test_all_base_modules_found():
    """Ensure we're testing all base modules."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base"

    # Get all subdirectories in base/
    actual_modules = {
        d.name
        for d in base_path.iterdir()
        if d.is_dir() and not d.name.startswith("__") and not d.name.startswith(".")
    }

    # Modules we're testing
    tested_modules = {"config", "theme", "providers", "search", "session", "observability"}

    # Make sure we're not missing any
    missing = actual_modules - tested_modules
    assert not missing, f"Missing independence tests for modules: {missing}"

    # Make sure we're not testing modules that don't exist
    extra = tested_modules - actual_modules
    assert not extra, f"Testing non-existent modules: {extra}"


def test_no_circular_imports_in_base():
    """Test that base modules don't have circular imports between each other."""
    base_path = Path(__file__).parent.parent.parent / "coda" / "base"

    # Map module name to its imports
    module_imports = {}

    for module_dir in base_path.iterdir():
        if (
            module_dir.is_dir()
            and not module_dir.name.startswith("__")
            and not module_dir.name.startswith(".")
        ):
            imports = get_all_imports_in_module(module_dir)
            # Filter to only base module imports
            base_imports = {
                imp.replace("coda.base.", "").split(".")[0]
                for imp in imports
                if imp.startswith("coda.base.") and "." in imp.replace("coda.base.", "")
            }
            # Remove self-imports (e.g., config importing from config)
            base_imports.discard(module_dir.name)
            module_imports[module_dir.name] = base_imports

    # Check for circular dependencies
    def has_circular_dep(module: str, target: str, visited: set[str]) -> bool:
        if module in visited:
            return module == target

        visited.add(module)

        for dep in module_imports.get(module, set()):
            if dep == target or has_circular_dep(dep, target, visited.copy()):
                return True

        return False

    circular_deps = []
    for module in module_imports:
        if has_circular_dep(module, module, set()):
            circular_deps.append(module)

    assert not circular_deps, f"Circular dependencies found in modules: {circular_deps}"


if __name__ == "__main__":
    # Run all tests
    import pytest

    pytest.main([__file__, "-v"])
