#!/usr/bin/env python3
"""Test text input functionality in the TUI interface."""

from coda.cli.tui_integrated import IntegratedTUICLI

class InputTestApp(IntegratedTUICLI):
    """Test app focused on text input functionality."""
    
    def on_mount(self):
        """Add instructions on startup."""
        super().on_mount()
        
        # Add input test instructions
        self.add_message("System", 
            "🖋️ **Text Input Test**\n\n"
            "**Test Steps:**\n"
            "1. Type normal text - should work smoothly\n"
            "2. Try typing 'hello world' and press Enter\n"
            "3. Test backspace, arrows, home/end keys\n"
            "4. Try Tab completion with '/mode'\n"
            "5. Test Ctrl+P command palette\n\n"
            "**Expected**: All typing should work normally\n"
            "**Previous Issue**: Could not enter any text"
        )

def run_input_test():
    """Run the input functionality test."""
    print("Starting text input test...")
    print("Try typing in the input field - should work now!")
    
    app = InputTestApp()
    app.run()

if __name__ == "__main__":
    run_input_test()