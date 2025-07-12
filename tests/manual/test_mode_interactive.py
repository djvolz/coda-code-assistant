#!/usr/bin/env python3
"""Test /mode command interactively using pexpect."""

import sys
import time

import pexpect

try:
    # Start coda in interactive mode
    print("Starting Coda interactive mode...")
    child = pexpect.spawn("uv run coda", encoding="utf-8", timeout=10)

    # Wait for model selection or prompt
    print("Waiting for initial prompt...")
    index = child.expect(["Select Model", "❯"])

    if index == 0:
        # We're in model selection, pick the first model
        print("In model selection, pressing Enter...")
        child.send("\r")  # Press Enter to select first model
        child.expect("❯")  # Wait for prompt

    print("At prompt, sending /mode command...")
    # Send /mode command
    child.send("/mode\r")

    # Wait for mode selector to appear
    print("Waiting for mode selector...")
    child.expect("Select Developer Mode")

    # Try to move down with arrow key
    print("Sending DOWN arrow...")
    child.send("\x1b[B")  # ESC[B is down arrow
    time.sleep(0.5)

    # Try again
    print("Sending another DOWN arrow...")
    child.send("\x1b[B")
    time.sleep(0.5)

    # Try with 'j' key
    print("Trying 'j' key for down...")
    child.send("j")
    time.sleep(0.5)

    # Send Escape to cancel
    print("Sending ESC to cancel...")
    child.send("\x1b")

    # Wait for prompt again
    child.expect("❯")

    # Exit
    child.send("/exit\r")
    child.expect(pexpect.EOF)

    print("\nTest completed. Check if arrow keys moved the selection.")

except pexpect.TIMEOUT:
    print("\nTIMEOUT: Current buffer:")
    print(child.before)
    sys.exit(1)

except Exception as e:
    print(f"\nERROR: {e}")
    if "child" in locals():
        print("Current buffer:")
        print(child.before)
    sys.exit(1)
