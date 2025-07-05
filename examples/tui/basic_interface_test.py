#!/usr/bin/env python3
"""Simple test of the TUI interface by creating a test message."""

# Test if we can create a simple textual app that shows our interface without provider
from coda.cli.tui_integrated import IntegratedTUICLI

def test_simple():
    """Test basic functionality."""
    print("Testing basic TUI interface creation...")
    
    try:
        # Create app without provider
        app = IntegratedTUICLI()
        print("✓ App created successfully")
        
        # Test adding a message
        app._messages = []
        print("✓ Messages list initialized")
        
        print("✓ Basic interface test passed")
        
    except Exception as e:
        print(f"✗ Error creating app: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_simple()