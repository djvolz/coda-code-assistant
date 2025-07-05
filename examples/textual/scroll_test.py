#!/usr/bin/env python3
"""Test scrolling in the Textual interface by adding many messages."""

from coda.cli.textual_integrated import IntegratedTextualCLI
import asyncio

class ScrollTestApp(IntegratedTextualCLI):
    """Test app that adds many messages to test scrolling."""
    
    def on_mount(self):
        """Add many messages on startup to test scrolling."""
        super().on_mount()
        
        # Add many messages to test scrolling
        for i in range(20):
            if i % 3 == 0:
                role = "You"
                content = f"This is user message {i+1}. Let's make it long enough to test how the interface handles longer messages and whether scrolling works properly."
            elif i % 3 == 1:
                role = "Assistant"
                content = f"This is assistant response {i+1}. I'm providing a helpful response to your question with enough detail to make this message span multiple lines and test the scrolling behavior."
            else:
                role = "System"
                content = f"System message {i+1}: Connection status, mode changes, or other system notifications go here."
            
            self.add_message(role, content)
        
        # Add final message about scrolling
        self.add_message("System", 
            "📜 Scroll test complete!\n\n"
            "Try these scroll commands:\n"
            "- Page Up/Down: Scroll up/down\n"
            "- Home: Go to top\n"
            "- End: Go to bottom\n"
            "- Type messages and see auto-scroll\n\n"
            "You should be auto-scrolled to this bottom message."
        )

def run_scroll_test():
    """Run the scroll test."""
    print("Starting Textual scroll test...")
    print("The interface will open with many messages to test scrolling.")
    print("Use Page Up/Down, Home/End to test manual scrolling.")
    print("Type messages to test auto-scrolling.")
    
    app = ScrollTestApp()
    app.run()

if __name__ == "__main__":
    run_scroll_test()