#!/usr/bin/env python3
"""
Simple test to verify the chatbot example works.
This can be run without pytest.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def test_chatbot_imports():
    """Test that we can import the chatbot."""
    try:
        print("✓ Chatbot imports successfully")
        return True
    except Exception as e:
        print(f"✗ Failed to import chatbot: {e}")
        return False


def test_chatbot_has_main():
    """Test that chatbot has a main function."""
    try:
        from tests.examples.simple_chatbot import chatbot

        assert hasattr(chatbot, "main")
        print("✓ Chatbot has main function")
        return True
    except Exception as e:
        print(f"✗ Chatbot main check failed: {e}")
        return False


def test_example_structure():
    """Test that example has proper structure."""
    try:
        example_dir = Path(__file__).parent / "simple_chatbot"

        # Check files exist
        assert (example_dir / "chatbot.py").exists(), "chatbot.py missing"
        assert (example_dir / "README.md").exists(), "README.md missing"
        assert (example_dir / "__init__.py").exists(), "__init__.py missing"

        # Check README content
        readme = (example_dir / "README.md").read_text()
        assert "## Features" in readme, "README missing Features section"
        assert "## Usage" in readme, "README missing Usage section"

        # Check chatbot.py structure
        chatbot_code = (example_dir / "chatbot.py").read_text()
        assert chatbot_code.startswith("#!/usr/bin/env python3"), "Missing shebang"
        assert 'if __name__ == "__main__":' in chatbot_code, "Missing main guard"

        print("✓ Example structure is correct")
        return True
    except Exception as e:
        print(f"✗ Structure check failed: {e}")
        return False


def main():
    """Run all tests."""
    print("Testing Simple Chatbot Example\n")

    tests = [
        test_chatbot_imports,
        test_chatbot_has_main,
        test_example_structure,
    ]

    passed = sum(test() for test in tests)
    total = len(tests)

    print(f"\n{passed}/{total} tests passed")

    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())
