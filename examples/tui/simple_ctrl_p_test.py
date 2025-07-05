#!/usr/bin/env python3
"""Simple test to verify Ctrl+P command palette works without crashing."""

import sys
from textual.app import App, ComposeResult
from textual.command import Hit, Hits, Provider as CommandProvider
from textual.widgets import Static

class TestCommandProvider(CommandProvider):
    """Test command provider for the command palette."""
    
    async def search(self, query: str) -> Hits:
        """Search for test commands."""
        matcher = self.matcher(query)
        
        test_commands = [
            ("test:hello", "Say hello"),
            ("test:quit", "Quit the application"),
            ("test:clear", "Clear the screen"),
        ]
        
        for cmd_id, description in test_commands:
            if matcher.match(cmd_id) or matcher.match(description):
                yield Hit(
                    description,
                    lambda: print(f"Command: {cmd_id}"),
                    cmd_id
                )

class SimpleCtrlPTestApp(App):
    """Simple app to test Ctrl+P command palette functionality."""
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+p", "command_palette", "Commands"),
    ]
    
    COMMANDS = {TestCommandProvider}
    
    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Static("""
🎛️ Ctrl+P Command Palette Test

Instructions:
1. Press Ctrl+P to open command palette
2. Type 'test' to see test commands
3. Press Escape to close palette
4. Press Ctrl+C to exit

Expected: No crashes when pressing Ctrl+P
        """, id="instructions")

def run_simple_test():
    """Run the simple Ctrl+P test."""
    print("Testing Ctrl+P command palette...")
    print("Press Ctrl+P in the app to test (should not crash)")
    
    app = SimpleCtrlPTestApp()
    try:
        app.run()
        print("✓ Test completed successfully - no crashes!")
        return True
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        return False

if __name__ == "__main__":
    success = run_simple_test()
    sys.exit(0 if success else 1)