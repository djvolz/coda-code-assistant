#!/usr/bin/env python3
"""Runner script for web UI tests with proper dependency checking."""

import subprocess
import sys
from pathlib import Path


def check_dependencies():
    """Check if web testing dependencies are available."""
    try:
        import pytest
        import selenium

        return True
    except ImportError:
        return False


def install_test_dependencies():
    """Install web testing dependencies."""
    print("📦 Installing web testing dependencies...")
    result = subprocess.run(
        ["uv", "sync", "--extra", "test-web"], cwd=Path(__file__).parent.parent.parent
    )
    return result.returncode == 0


def run_backend_tests():
    """Run backend integration tests (no browser required)."""
    print("🧪 Running backend integration tests...")
    result = subprocess.run(
        ["uv", "run", "pytest", "tests/web/test_backend_integration.py", "-v"],
        cwd=Path(__file__).parent.parent.parent,
    )
    return result.returncode == 0


def run_browser_tests():
    """Run browser-based tests."""
    print("🌐 Running browser-based tests...")
    print("⚠️  Note: These tests require Chrome or Firefox WebDriver")

    result = subprocess.run(
        [
            "uv",
            "run",
            "pytest",
            "tests/web/test_navigation.py",
            "tests/web/test_functionality.py",
            "-v",
            "--tb=short",
        ],
        cwd=Path(__file__).parent.parent.parent,
    )
    return result.returncode == 0


def main():
    """Main test runner."""
    print("🚀 Coda Web UI Test Runner")
    print("=" * 40)

    # Check if dependencies are available
    if not check_dependencies():
        print("❌ Web testing dependencies not found")
        response = input("Install them now? (y/n): ").lower().strip()

        if response in ["y", "yes"]:
            if not install_test_dependencies():
                print("❌ Failed to install dependencies")
                sys.exit(1)
            print("✅ Dependencies installed")
        else:
            print("❌ Cannot run tests without dependencies")
            sys.exit(1)

    print("✅ Dependencies available")

    # Run tests in order of complexity
    tests_passed = 0
    total_tests = 2

    # 1. Backend tests (fast, no browser required)
    print("\n" + "=" * 40)
    if run_backend_tests():
        print("✅ Backend tests passed")
        tests_passed += 1
    else:
        print("❌ Backend tests failed")

    # 2. Browser tests (slower, require WebDriver)
    print("\n" + "=" * 40)
    try:
        if run_browser_tests():
            print("✅ Browser tests passed")
            tests_passed += 1
        else:
            print("❌ Browser tests failed")
    except Exception as e:
        print(f"❌ Browser tests failed with error: {e}")
        print("💡 Make sure Chrome or Firefox WebDriver is installed")

    # Summary
    print("\n" + "=" * 40)
    print(f"📊 Test Results: {tests_passed}/{total_tests} test suites passed")

    if tests_passed == total_tests:
        print("🎉 All web UI tests passed!")
        return True
    else:
        print("❌ Some tests failed - check output above")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
