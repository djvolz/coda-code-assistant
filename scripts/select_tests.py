#!/usr/bin/env python3
"""
Test selection script for optimized CI/CD pipeline.
Selects relevant tests based on changed files.
"""

import argparse
import json
import sys
from pathlib import Path


class TestSelector:
    """Intelligent test selection based on file changes."""

    def __init__(
        self, mapping_file: str = "docs/plans/test-infrastructure/module-test-mapping.json"
    ):
        """Initialize with module-to-test mapping."""
        self.mapping_file = Path(mapping_file)
        if not self.mapping_file.exists():
            print(f"Warning: Mapping file {mapping_file} not found", file=sys.stderr)
            self.mapping = {}
        else:
            with open(self.mapping_file) as f:
                self.mapping = json.load(f)

    def get_tests_for_changes(self, changed_files: list[str]) -> tuple[set[str], set[str]]:
        """
        Get unit and integration tests for changed files.

        Returns:
            Tuple of (unit_tests, integration_tests)
        """
        unit_tests = set()
        integration_tests = set()

        for file in changed_files:
            # Skip non-Python files unless they're critical
            if not file.endswith(".py") and not self._is_critical_file(file):
                continue

            # Direct module mapping
            if file in self.mapping:
                module_info = self.mapping[file]
                unit_tests.update(module_info.get("unit_tests", []))
                integration_tests.update(module_info.get("integration_tests", []))

            # Check if changed file is a dependency
            for _module, info in self.mapping.items():
                for dep in info.get("dependencies", []):
                    if file.startswith(dep):
                        unit_tests.update(info.get("unit_tests", []))
                        # Only add integration tests if the dependency is critical
                        if self._is_critical_dependency(dep):
                            integration_tests.update(info.get("integration_tests", []))

        return unit_tests, integration_tests

    def get_affected_modules(self, changed_files: list[str]) -> set[str]:
        """Get high-level modules affected by changes."""
        modules = set()

        for file in changed_files:
            if (
                file.startswith("coda/agents/")
                or file in self.mapping
                and "agent" in self.mapping[file].get("markers", [])
            ):
                modules.add("agents")
            if (
                file.startswith("coda/cli/")
                or file in self.mapping
                and "cli" in self.mapping[file].get("markers", [])
            ):
                modules.add("cli")
            if (
                file.startswith("coda/web/")
                or file in self.mapping
                and "web" in self.mapping[file].get("markers", [])
            ):
                modules.add("web")
            if (
                file.startswith("coda/providers/")
                or file in self.mapping
                and "providers" in self.mapping[file].get("markers", [])
            ):
                modules.add("providers")
            if (
                file.startswith("coda/observability/")
                or file in self.mapping
                and "observability" in self.mapping[file].get("markers", [])
            ):
                modules.add("observability")
            if (
                file.startswith("coda/session/")
                or file in self.mapping
                and "session" in self.mapping[file].get("markers", [])
            ):
                modules.add("session")

        return modules

    def get_markers_for_changes(self, changed_files: list[str]) -> set[str]:
        """Get pytest markers for changed files."""
        markers = set()

        for file in changed_files:
            if file in self.mapping:
                markers.update(self.mapping[file].get("markers", []))

        # Always include fast and unit for PR validation
        if markers:
            markers.add("fast")
            markers.add("unit")

        return markers

    def should_run_all_tests(self, changed_files: list[str]) -> bool:
        """Determine if all tests should run based on changes."""
        critical_patterns = [
            "pyproject.toml",
            "requirements.txt",
            "Makefile",
            ".github/workflows/",
            "scripts/test",
            "conftest.py",
            "pytest.ini",
            "tox.ini",
        ]

        for file in changed_files:
            for pattern in critical_patterns:
                if pattern in file:
                    return True

        return False

    def _is_critical_file(self, file: str) -> bool:
        """Check if a non-Python file is critical for testing."""
        critical_extensions = {".yml", ".yaml", ".toml", ".ini", ".json"}
        critical_names = {"Makefile", "Dockerfile", "docker-compose.yml"}

        path = Path(file)
        return (
            path.suffix in critical_extensions
            or path.name in critical_names
            or ".github" in file
            or "scripts" in file
        )

    def _is_critical_dependency(self, dep: str) -> bool:
        """Check if a dependency is critical enough to trigger integration tests."""
        critical_deps = [
            "coda/providers/base.py",
            "coda/session/database.py",
            "coda/observability/manager.py",
            "coda/agents/agent.py",
        ]
        return any(dep.endswith(critical) for critical in critical_deps)

    def format_output(self, tests: set[str], format_type: str = "space") -> str:
        """Format test list for different consumers."""
        if not tests:
            return ""

        sorted_tests = sorted(tests)

        if format_type == "space":
            return " ".join(sorted_tests)
        elif format_type == "newline":
            return "\n".join(sorted_tests)
        elif format_type == "json":
            return json.dumps(sorted_tests)
        elif format_type == "github":
            # GitHub Actions output format
            return " ".join(sorted_tests)
        else:
            return " ".join(sorted_tests)

    def get_test_command(self, changed_files: list[str], test_type: str = "all") -> str:
        """Generate pytest command for changed files."""
        if self.should_run_all_tests(changed_files):
            return "pytest tests/ -m 'not slow' --maxfail=5"

        unit_tests, integration_tests = self.get_tests_for_changes(changed_files)
        markers = self.get_markers_for_changes(changed_files)

        if test_type == "unit" and unit_tests:
            tests = self.format_output(unit_tests)
            marker_str = " and ".join(markers) if markers else "unit"
            return f"pytest {tests} -m '{marker_str}' --maxfail=1"
        elif test_type == "integration" and integration_tests:
            tests = self.format_output(integration_tests)
            return f"pytest {tests} -m 'integration' --maxfail=1"
        elif test_type == "all" and (unit_tests or integration_tests):
            all_tests = unit_tests.union(integration_tests)
            tests = self.format_output(all_tests)
            return f"pytest {tests} --maxfail=1"
        else:
            # No specific tests found, run smoke tests
            return "pytest -m 'smoke' --maxfail=1"


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Select tests based on changed files")
    parser.add_argument(
        "--changed-files", required=True, help="Space-separated list of changed files"
    )
    parser.add_argument(
        "--mapping-file",
        default="docs/plans/test-infrastructure/module-test-mapping.json",
        help="Path to module-test mapping file",
    )
    parser.add_argument(
        "--output-format",
        choices=["space", "newline", "json", "github", "command"],
        default="space",
        help="Output format for test list",
    )
    parser.add_argument(
        "--test-type",
        choices=["unit", "integration", "all"],
        default="all",
        help="Type of tests to select",
    )
    parser.add_argument(
        "--github-output", action="store_true", help="Output in GitHub Actions format"
    )

    args = parser.parse_args()

    # Parse changed files
    changed_files = args.changed_files.strip().split() if args.changed_files.strip() else []

    if not changed_files:
        print("No changed files detected", file=sys.stderr)
        sys.exit(0)

    # Initialize selector
    selector = TestSelector(args.mapping_file)

    # Check if we should run all tests
    if selector.should_run_all_tests(changed_files):
        if args.github_output:
            import os

            if os.environ.get("GITHUB_OUTPUT"):
                with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                    f.write("all-tests=true\n")
                    f.write("command=pytest tests/ -m 'not slow' --maxfail=5\n")
            else:
                print("all-tests=true")
                print("command=pytest tests/ -m 'not slow' --maxfail=5")
        else:
            print("ALL_TESTS")
        sys.exit(0)

    # Get tests
    unit_tests, integration_tests = selector.get_tests_for_changes(changed_files)
    markers = selector.get_markers_for_changes(changed_files)
    modules = selector.get_affected_modules(changed_files)

    # Output based on format
    if args.output_format == "command":
        command = selector.get_test_command(changed_files, args.test_type)
        print(command)
    elif args.github_output:
        # GitHub Actions format
        all_tests = unit_tests.union(integration_tests)
        import os

        # Generate command
        command = selector.get_test_command(changed_files, args.test_type)

        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as f:
                f.write(f"tests={selector.format_output(all_tests, 'github')}\n")
                f.write(f"unit-tests={selector.format_output(unit_tests, 'github')}\n")
                f.write(
                    f"integration-tests={selector.format_output(integration_tests, 'github')}\n"
                )
                f.write(f"markers={' '.join(markers)}\n")
                f.write(f"modules={' '.join(modules)}\n")
                f.write(f"skip-tests={'true' if not all_tests else 'false'}\n")
                f.write(f"run-integration={'true' if integration_tests else 'false'}\n")
                f.write(f"command={command}\n")
        else:
            print(f"tests={selector.format_output(all_tests, 'github')}")
            print(f"unit-tests={selector.format_output(unit_tests, 'github')}")
            print(f"integration-tests={selector.format_output(integration_tests, 'github')}")
            print(f"markers={' '.join(markers)}")
            print(f"modules={' '.join(modules)}")
            print(f"skip-tests={'true' if not all_tests else 'false'}")
            print(f"run-integration={'true' if integration_tests else 'false'}")
            print(f"command={command}")
    else:
        # Standard output
        if args.test_type == "unit":
            output = selector.format_output(unit_tests, args.output_format)
        elif args.test_type == "integration":
            output = selector.format_output(integration_tests, args.output_format)
        else:
            all_tests = unit_tests.union(integration_tests)
            output = selector.format_output(all_tests, args.output_format)

        if output:
            print(output)


if __name__ == "__main__":
    main()
