#!/usr/bin/env python3
"""Test Ctrl+P command palette functionality."""

from coda.cli.tui_integrated import IntegratedTUICLI

class CtrlPTestApp(IntegratedTUICLI):
    """Test app that verifies Ctrl+P command palette works."""
    
    def on_mount(self):
        """Add instructions on startup."""
        super().on_mount()
        
        # Add Ctrl+P test instructions
        self.add_message("System", 
            "🎛️ **Ctrl+P Command Palette Test**\n\n"
            "**Test Steps:**\n"
            "1. Press **Ctrl+P** to open command palette\n"
            "2. Try typing different commands:\n"
            "   - Type 'mode' to see mode switching commands\n"
            "   - Type 'clear' to see clear command\n"
            "   - Type 'export' to see export commands\n"
            "3. Press **Escape** to close the palette\n\n"
            "**Expected**: No crashes, smooth operation\n"
            "**Previous Issue**: App would crash when pressing Ctrl+P"
        )

def run_ctrl_p_test():
    """Run the Ctrl+P command palette test."""
    print("Starting Ctrl+P command palette test...")
    print("Press Ctrl+P to test the command palette functionality!")
    
    app = CtrlPTestApp()
    app.run()

if __name__ == "__main__":
    run_ctrl_p_test()