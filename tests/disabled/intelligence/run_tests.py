#!/usr/bin/env python3
"""Run comprehensive tests for tree-sitter integration."""

import subprocess
import sys
from pathlib import Path


def run_test_suite():
    """Run the complete test suite for tree-sitter integration."""
    test_dir = Path(__file__).parent
    root_dir = test_dir.parent.parent

    print("=== Running Tree-Sitter Integration Test Suite ===\n")

    test_groups = [
        {
            "name": "Unit Tests - TreeSitterQueryAnalyzer",
            "command": [
                "python",
                "-m",
                "pytest",
                str(test_dir / "test_tree_sitter_query_analyzer.py"),
                "-v",
            ],
        },
        {
            "name": "Integration Tests - RepoMap with TreeSitter",
            "command": [
                "python",
                "-m",
                "pytest",
                str(test_dir / "test_repo_map_integration.py"),
                "-v",
            ],
        },
        {
            "name": "Existing TreeSitterAnalyzer Tests",
            "command": [
                "python",
                "-m",
                "pytest",
                str(test_dir / "test_tree_sitter_analyzer.py"),
                "-v",
            ],
        },
    ]

    overall_success = True

    for test_group in test_groups:
        print(f"\n{'=' * 60}")
        print(f"Running: {test_group['name']}")
        print("=" * 60)

        result = subprocess.run(test_group["command"], cwd=root_dir, capture_output=False)

        if result.returncode != 0:
            overall_success = False
            print(f"\n❌ {test_group['name']} FAILED")
        else:
            print(f"\n✅ {test_group['name']} PASSED")

    print("\n" + "=" * 60)
    print("Test Suite Summary")
    print("=" * 60)

    if overall_success:
        print("✅ All tests passed!")
        return 0
    else:
        print("❌ Some tests failed. Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(run_test_suite())
