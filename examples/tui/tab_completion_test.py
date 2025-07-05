#!/usr/bin/env python3
"""Test tab completion in the TUI interface."""

from coda.cli.tui_integrated import IntegratedTUICLI

class TabCompletionTestApp(IntegratedTUICLI):
    """Test app that demonstrates tab completion."""
    
    def on_mount(self):
        """Add instructions on startup."""
        super().on_mount()
        
        # Add tab completion instructions
        self.add_message("System", 
            "🔧 **Tab Completion Test**\n\n"
            "Try these tab completion examples:\n\n"
            "1. Type `/` and press **Tab** - shows all commands\n"
            "2. Type `/m` and press **Tab** - completes to `/mode`\n"
            "3. Type `/mode ` and press **Tab** - shows mode options\n"
            "4. Type `/mode g` and press **Tab** - completes to `/mode general`\n"
            "5. Type `~/` and press **Tab** - shows home directory files\n\n"
            "**Pro tip**: Press **Tab** multiple times to cycle through options!"
        )

def run_tab_completion_test():
    """Run the tab completion test."""
    print("Starting TUI tab completion test...")
    print("Try the tab completion examples shown in the interface!")
    
    app = TabCompletionTestApp()
    app.run()

if __name__ == "__main__":
    run_tab_completion_test()