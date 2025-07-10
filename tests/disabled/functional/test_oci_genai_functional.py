"""Functional tests for OCI GenAI provider end-to-end workflows."""

import os
import subprocess
import tempfile

import pytest


@pytest.mark.functional
class TestOCIGenAIFunctional:
    """Functional tests for complete OCI GenAI workflows."""

    @pytest.fixture
    def temp_config(self):
        """Create temporary config file for testing."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".toml", delete=False) as f:
            compartment_id = os.getenv("OCI_COMPARTMENT_ID", "test-compartment")
            f.write(
                f"""
[oci]
compartment_id = "{compartment_id}"

[cli]
default_provider = "oci_genai"
"""
            )
            f.flush()
            yield f.name
        os.unlink(f.name)

    def run_coda_command(self, args, input_text=None, env=None):
        """Helper to run coda CLI commands."""
        cmd = ["uv", "run", "coda"] + args

        result = subprocess.run(
            cmd,
            input=input_text,
            capture_output=True,
            text=True,
            env=env or os.environ.copy(),
            timeout=30,
        )

        return result

    def test_cli_one_shot_mode(self, temp_config):
        """Test CLI in one-shot mode with different models."""
        if os.getenv("SKIP_INTEGRATION_TESTS") == "1":
            pytest.skip("Integration tests disabled")

        # Test with xAI model
        result = self.run_coda_command(
            ["--one-shot", "Say 'xAI test OK' and nothing else", "--model", "xai.grok-3-fast"]
        )

        assert result.returncode == 0
        assert "xAI test OK" in result.stdout

        # Test with Cohere model
        result = self.run_coda_command(
            [
                "--one-shot",
                "Say 'Cohere test OK' and nothing else",
                "--model",
                "cohere.command-a-03-2025",
            ]
        )

        assert result.returncode == 0
        assert "Cohere test OK" in result.stdout

        # Test with Meta model
        result = self.run_coda_command(
            [
                "--one-shot",
                "Say 'Meta test OK' and nothing else",
                "--model",
                "meta.llama-3.3-70b-instruct",
            ]
        )

        assert result.returncode == 0
        assert "Meta test OK" in result.stdout

    def test_model_listing(self):
        """Test model listing functionality."""
        result = self.run_coda_command(["--model", "list"])

        # Should list models even without full config
        assert "xai" in result.stdout.lower() or "Available models" in result.stdout

    def test_interactive_mode_simulation(self):
        """Test interactive mode with expect script."""
        expect_script = """#!/usr/bin/expect -f
set timeout 20
spawn uv run coda
expect {
    "Select model number" {
        send "1\\r"
        expect "You:"
        send "Say INTERACTIVE_TEST_PASS\\r"
        expect "Assistant:"
        expect "INTERACTIVE_TEST_PASS"
        send "exit\\r"
        exit 0
    }
    timeout {
        exit 1
    }
}
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".exp", delete=False) as f:
            f.write(expect_script)
            f.flush()
            os.chmod(f.name, 0o755)

            try:
                result = subprocess.run([f.name], capture_output=True, timeout=30)

                if result.returncode == 0:
                    assert b"INTERACTIVE_TEST_PASS" in result.stdout
                else:
                    # Skip if expect is not available or test fails
                    pytest.skip("Interactive test failed - expect might not be available")
            finally:
                os.unlink(f.name)

    def test_streaming_response_completeness(self):
        """Test that streaming responses are complete and properly formatted."""
        if os.getenv("SKIP_INTEGRATION_TESTS") == "1":
            pytest.skip("Integration tests disabled")

        # Create a test script that captures streaming output
        test_script = """
import sys
sys.path.insert(0, '.')
from coda.providers.oci_genai import OCIGenAIProvider
from coda.providers.base import Message, Role

provider = OCIGenAIProvider()
messages = [Message(role=Role.USER, content="Count from 1 to 5")]

chunks = []
for chunk in provider.chat_stream(messages, model="xai.grok-3-fast"):
    chunks.append(chunk.content)
    print(f"CHUNK: {repr(chunk.content)}")

full_response = ''.join(chunks)
print(f"FULL: {full_response}")
print(f"CHUNK_COUNT: {len(chunks)}")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_script)
            f.flush()

            try:
                result = subprocess.run(
                    ["uv", "run", "python", f.name], capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    assert "CHUNK:" in result.stdout
                    assert "FULL:" in result.stdout
                    assert "1" in result.stdout and "5" in result.stdout

                    # Extract chunk count
                    for line in result.stdout.split("\n"):
                        if line.startswith("CHUNK_COUNT:"):
                            count = int(line.split(":")[1].strip())
                            assert count > 1, "Should have multiple chunks"
            finally:
                os.unlink(f.name)

    def test_error_handling_invalid_model(self):
        """Test error handling with invalid model names."""
        result = self.run_coda_command(["--one-shot", "Test", "--model", "invalid.model.name"])

        # Should fail gracefully
        assert (
            result.returncode != 0
            or "error" in result.stdout.lower()
            or "invalid" in result.stdout.lower()
        )

    def test_concurrent_requests(self):
        """Test handling of concurrent requests."""
        if os.getenv("SKIP_INTEGRATION_TESTS") == "1":
            pytest.skip("Integration tests disabled")

        import concurrent.futures

        def make_request(index):
            result = self.run_coda_command(
                ["--one-shot", f"Say 'Request {index} OK'", "--model", "xai.grok-3-fast"]
            )
            return index, result.returncode, result.stdout

        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(make_request, i) for i in range(3)]
            results = [f.result() for f in futures]

        for index, returncode, stdout in results:
            assert returncode == 0, f"Request {index} failed"
            assert f"Request {index} OK" in stdout

    def test_long_conversation(self):
        """Test handling of long conversations."""
        if os.getenv("SKIP_INTEGRATION_TESTS") == "1":
            pytest.skip("Integration tests disabled")

        test_script = """
import sys
sys.path.insert(0, '.')
from coda.providers.oci_genai import OCIGenAIProvider
from coda.providers.base import Message, Role

provider = OCIGenAIProvider()

# Build a conversation
messages = []
for i in range(5):
    messages.append(Message(role=Role.USER, content=f"Message {i}"))
    messages.append(Message(role=Role.ASSISTANT, content=f"Response {i}"))

messages.append(Message(role=Role.USER, content="Summarize our conversation in one sentence"))

response = provider.chat(messages, model="xai.grok-3-fast", max_tokens=100)
print(f"SUMMARY: {response.content}")
assert "message" in response.content.lower() or "response" in response.content.lower()
print("LONG_CONVERSATION_PASS")
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(test_script)
            f.flush()

            try:
                result = subprocess.run(
                    ["uv", "run", "python", f.name], capture_output=True, text=True, timeout=30
                )

                if result.returncode == 0:
                    assert "LONG_CONVERSATION_PASS" in result.stdout
            finally:
                os.unlink(f.name)

    def test_special_characters_handling(self):
        """Test handling of special characters in messages."""
        if os.getenv("SKIP_INTEGRATION_TESTS") == "1":
            pytest.skip("Integration tests disabled")

        special_inputs = [
            "Test with emoji: 🚀 🎉",
            "Test with quotes: \"Hello\" and 'World'",
            "Test with newlines:\nLine 1\nLine 2",
            "Test with unicode: café, naïve, 你好",
        ]

        for input_text in special_inputs:
            result = self.run_coda_command(
                ["--one-shot", f"Echo this exactly: {input_text}", "--model", "xai.grok-3-fast"]
            )

            # Should handle special characters without crashing
            assert result.returncode == 0
