#!/usr/bin/env python3
"""
Summary test script to verify all tool tests are properly set up.

This script runs a subset of tests to verify the test infrastructure is working.
"""

import subprocess
import sys


def run_test_command(description, command):
    """Run a test command and report results."""
    print(f"\n{'=' * 60}")
    print(f"Testing: {description}")
    print(f"Command: {command}")
    print("=" * 60)

    result = subprocess.run(command, shell=True, capture_output=True, text=True)

    if result.returncode == 0:
        print("✅ PASSED")
        # Extract summary line
        for line in result.stdout.split("\n"):
            if "passed" in line and "failed" in line:
                print(f"   {line.strip()}")
    else:
        print("❌ FAILED")
        # Show last few lines of output
        lines = result.stdout.split("\n")
        for line in lines[-10:]:
            if line.strip():
                print(f"   {line}")

    return result.returncode == 0


def main():
    """Run test summary."""
    print("CODA Tools Test Summary")
    print("=" * 60)

    tests = [
        (
            "Tool Registry",
            "uv run python -m pytest tests/test_tools.py::TestToolRegistry -v --tb=short",
        ),
        (
            "File Tools",
            "uv run python -m pytest tests/test_tools.py::TestFileTools -v --tb=short -k 'test_read_file_tool or test_write_file_tool'",
        ),
        (
            "Tool System with Mock Provider",
            "uv run python -m pytest tests/tools/test_tools_with_mock_provider.py::TestToolSystemWithMockProvider -v --tb=short",
        ),
        (
            "Session Storage Models",
            "uv run python -m pytest tests/tools/test_session_storage.py::TestToolInvocation -v --tb=short",
        ),
        (
            "MCP Message Handling",
            "uv run python -m pytest tests/tools/test_mcp_server.py::TestMCPMessage -v --tb=short",
        ),
    ]

    passed = 0
    failed = 0

    for description, command in tests:
        if run_test_command(description, command):
            passed += 1
        else:
            failed += 1

    print(f"\n{'=' * 60}")
    print(f"SUMMARY: {passed} test groups passed, {failed} test groups failed")
    print("=" * 60)

    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
