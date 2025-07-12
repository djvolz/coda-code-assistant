#!/usr/bin/env python3
"""
Automated test script for testing interactive mode and streaming responses.

This script can be used by developers and CI/CD pipelines to ensure that
the interactive chat functionality works correctly with OCI GenAI.
"""

import os
import subprocess
import time


def create_expect_script(test_name, model_number, test_message, timeout=30):
    """Create an expect script for testing interactive mode."""
    expect_script = f"""#!/usr/bin/expect -f

set timeout {timeout}
spawn uv run coda
expect "Select model number"
send "{model_number}\\r"
expect "You: "
send "{test_message}\\r"
expect "Assistant:"
sleep 5
send "exit\\r"
expect eof
"""

    script_path = f"/tmp/test_coda_{test_name}.exp"
    with open(script_path, "w") as f:
        f.write(expect_script)
    os.chmod(script_path, 0o755)
    return script_path


def run_interactive_test(test_name, model_number, test_message):
    """Run an interactive test and return results."""
    print(f"\\n=== Running test: {test_name} ===")
    print(f"Model: {model_number}, Message: '{test_message}'")

    script_path = create_expect_script(test_name, model_number, test_message)

    try:
        result = subprocess.run([script_path], capture_output=True, text=True, timeout=60)

        # Check if assistant responded
        output = result.stdout
        if "Assistant:" in output and len(output.split("Assistant:")[-1].strip()) > 10:
            print("✅ Test PASSED - Assistant responded correctly")
            return True
        else:
            print("❌ Test FAILED - No meaningful response from assistant")
            print("Output:", output[-500:])  # Last 500 chars
            return False

    except subprocess.TimeoutExpired:
        print("❌ Test FAILED - Timeout")
        return False
    except Exception as e:
        print(f"❌ Test FAILED - Exception: {e}")
        return False
    finally:
        if os.path.exists(script_path):
            os.unlink(script_path)


def test_direct_streaming():
    """Test streaming API directly."""
    print("\\n=== Testing Direct Streaming API ===")
    try:
        result = subprocess.run(
            ["uv", "run", "python", "debug_oci_streaming.py"],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if (
            "Total chunks received:" in result.stdout
            and "0" not in result.stdout.split("Total chunks received:")[-1].split("\\n")[0]
        ):
            print("✅ Direct streaming test PASSED")
            return True
        else:
            print("❌ Direct streaming test FAILED")
            print("Output:", result.stdout[-500:])
            return False
    except Exception as e:
        print(f"❌ Direct streaming test FAILED - Exception: {e}")
        return False


def run_all_tests():
    """Run all automated tests."""
    print("🚀 Starting Coda Interactive Mode Tests")
    print("=" * 50)

    tests = [
        ("simple_greeting", "1", "Hello, how are you?"),
        ("code_question", "1", "Can you help me write a Python function?"),
        ("math_question", "2", "What is 15 * 23?"),  # Different model
        ("test_question", "1", "This is a test message for automation"),
    ]

    results = []

    # Test direct streaming first
    streaming_result = test_direct_streaming()
    results.append(("direct_streaming", streaming_result))

    # Test interactive mode with different scenarios
    for test_name, model_number, test_message in tests:
        result = run_interactive_test(test_name, model_number, test_message)
        results.append((test_name, result))
        time.sleep(2)  # Brief pause between tests

    # Summary
    print("\\n" + "=" * 50)
    print("📊 TEST SUMMARY")
    print("=" * 50)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:20} {status}")

    print(f"\\nOverall: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Interactive mode is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Check the output above for details.")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    exit(exit_code)
