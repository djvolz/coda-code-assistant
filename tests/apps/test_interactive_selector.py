"""Test interactive selector functionality using pexpect."""

import os
import time

import pexpect
import pytest


class TestInteractiveSelector:
    """Test the interactive selector UI functionality."""

    @pytest.fixture
    def coda_command(self):
        """Get the command to run Coda."""
        # Use uv run to ensure we're using the right environment
        return "uv run coda"

    def test_mode_selector_arrow_keys(self, coda_command):
        """Test that arrow keys work in the /mode selector."""
        # Start Coda
        child = pexpect.spawn(coda_command, encoding="utf-8", timeout=10)

        try:
            # Wait for initial prompt (might show model selection first)
            index = child.expect(["Select Model", "❯"])

            if index == 0:
                # We're in model selection, select the first model
                child.send("\r")  # Press Enter
                child.expect("❯")  # Wait for prompt

            # Send /mode command
            child.send("/mode\r")

            # Wait for mode selector to appear
            child.expect("Select Developer Mode")

            # The initial selection should be on "general"
            child.expect("▶ general")

            # Press down arrow
            child.send("\x1b[B")  # ESC[B is down arrow
            time.sleep(0.1)

            # Should now be on "code"
            child.expect("▶ code")

            # Press down again
            child.send("\x1b[B")
            time.sleep(0.1)

            # Should now be on "debug"
            child.expect("▶ debug")

            # Press up arrow
            child.send("\x1b[A")  # ESC[A is up arrow
            time.sleep(0.1)

            # Should be back on "code"
            child.expect("▶ code")

            # Test 'j' and 'k' keys
            child.send("j")  # j for down
            time.sleep(0.1)
            child.expect("▶ debug")

            child.send("k")  # k for up
            time.sleep(0.1)
            child.expect("▶ code")

            # Select the current option
            child.send("\r")  # Enter

            # Should see confirmation
            child.expect("Mode set to: code")

            # Exit
            child.send("/exit\r")
            child.expect(pexpect.EOF)

        except pexpect.TIMEOUT:
            print(f"TIMEOUT - Buffer contents:\n{child.before}")
            raise
        except Exception as e:
            print(f"ERROR: {e}")
            print(f"Buffer contents:\n{child.before}")
            raise
        finally:
            child.close()

    def test_theme_selector_with_search(self, coda_command):
        """Test theme selector with search functionality."""
        child = pexpect.spawn(coda_command, encoding="utf-8", timeout=10)

        try:
            # Handle initial setup
            index = child.expect(["Select Model", "❯"])
            if index == 0:
                child.send("\r")
                child.expect("❯")

            # Send /theme command
            child.send("/theme\r")

            # Wait for theme selector
            child.expect("Select Theme")

            # Type to search
            child.send("dark")
            time.sleep(0.2)

            # Should filter to themes containing "dark"
            child.expect("Filter: dark")

            # Press down to select a dark theme
            child.send("\x1b[B")
            time.sleep(0.1)

            # Press Enter to select
            child.send("\r")

            # Should see theme change confirmation
            child.expect("Theme changed to")

            # Exit
            child.send("/exit\r")
            child.expect(pexpect.EOF)

        except pexpect.TIMEOUT:
            print(f"TIMEOUT - Buffer contents:\n{child.before}")
            raise
        finally:
            child.close()

    def test_export_selector(self, coda_command):
        """Test export format selector."""
        child = pexpect.spawn(coda_command, encoding="utf-8", timeout=10)

        try:
            # Handle initial setup
            index = child.expect(["Select Model", "❯"])
            if index == 0:
                child.send("\r")
                child.expect("❯")

            # Send /export command
            child.send("/export\r")

            # Wait for export selector
            child.expect("Select Export Format")

            # Should show export options
            child.expect("json")
            child.expect("markdown")

            # Move down to markdown
            child.send("\x1b[B")
            time.sleep(0.1)

            # Cancel with Escape
            child.send("\x1b")  # ESC

            # Should go back to prompt
            child.expect("Export cancelled")
            child.expect("❯")

            # Exit
            child.send("/exit\r")
            child.expect(pexpect.EOF)

        except pexpect.TIMEOUT:
            print(f"TIMEOUT - Buffer contents:\n{child.before}")
            raise
        finally:
            child.close()

    def test_model_selector_navigation(self, coda_command):
        """Test model selector if it appears on startup."""
        child = pexpect.spawn(coda_command, encoding="utf-8", timeout=10)

        try:
            # Check if we get model selector
            index = child.expect(["Select Model", "❯"])

            if index == 0:
                # We're in model selection
                # Test arrow navigation
                child.send("\x1b[B")  # Down arrow
                time.sleep(0.1)

                # Press Enter to select
                child.send("\r")

                # Should proceed to prompt
                child.expect("❯")

            # Exit
            child.send("/exit\r")
            child.expect(pexpect.EOF)

        except pexpect.TIMEOUT:
            print(f"TIMEOUT - Buffer contents:\n{child.before}")
            raise
        finally:
            child.close()


@pytest.mark.skipif(
    os.environ.get("CI") == "true", reason="Interactive tests don't work well in CI environments"
)
class TestInteractiveSelectorCI:
    """Additional tests that might not work in CI."""

    def test_session_selector(self, coda_command):
        """Test session command selector."""
        # This test might fail in CI due to terminal emulation issues
        pass
