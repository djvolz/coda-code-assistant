#!/usr/bin/env python3
"""Test script to verify web UI functionality."""

import subprocess
import sys
import time


def test_imports():
    """Test that all required imports work."""
    print("🧪 Testing imports...")

    try:
        from coda.configuration import get_config
        from coda.providers.registry import get_provider_registry
        from coda.session.manager import SessionManager
        from coda.web.app import main
        from coda.web.components.chat_widget import render_chat_interface
        from coda.web.components.file_manager import render_file_upload_widget
        from coda.web.components.model_selector import render_model_selector
        from coda.web.pages import chat, dashboard, sessions, settings

        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False


def test_cli_commands():
    """Test CLI commands."""
    print("\n🧪 Testing CLI commands...")

    try:
        # Test help command
        result = subprocess.run(
            ["uv", "run", "coda", "--help"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and "web" in result.stdout:
            print("✅ CLI help works and includes web command")
        else:
            print(f"❌ CLI help failed: {result.stderr}")
            return False

        # Test web command help
        result = subprocess.run(
            ["uv", "run", "coda", "web", "--help"], capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            print("✅ Web command help works")
        else:
            print(f"❌ Web command help failed: {result.stderr}")
            return False

        return True
    except Exception as e:
        print(f"❌ CLI test error: {e}")
        return False


def test_web_startup():
    """Test web UI startup."""
    print("\n🧪 Testing web UI startup...")

    try:
        cmd = [
            "uv",
            "run",
            "streamlit",
            "run",
            "coda/web/app.py",
            "--server.headless",
            "true",
            "--server.port",
            "8508",
        ]

        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        time.sleep(5)

        if proc.poll() is None:
            print("✅ Web UI starts successfully")
            proc.terminate()
            proc.wait()
            return True
        else:
            stdout, stderr = proc.communicate()
            print(f"❌ Web UI startup failed: {stderr[:200]}")
            return False

    except Exception as e:
        print(f"❌ Web startup test error: {e}")
        return False


def main():
    """Run all tests."""
    print("🚀 Phase 7 Web UI Test Suite")
    print("=" * 50)

    tests = [
        test_imports,
        test_cli_commands,
        test_web_startup,
    ]

    passed = 0
    total = len(tests)

    for test in tests:
        if test():
            passed += 1

    print(f"\n📊 Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Phase 7 Web UI is ready!")
        print("\n🚀 To start the web UI, run:")
        print("   uv run coda web")
    else:
        print("❌ Some tests failed. Please check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main()
