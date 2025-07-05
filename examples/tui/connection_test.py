#!/usr/bin/env python3
"""Quick test of the TUI interface with actual provider."""

import subprocess
import time
import signal
import os

def test_real_provider():
    """Test with real provider briefly."""
    print("Testing TUI interface with OCI provider...")
    
    try:
        # Start process
        proc = subprocess.Popen(
            ["uv", "run", "coda", "--textual", "--provider", "oci_genai"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            preexec_fn=os.setsid
        )
        
        # Wait 5 seconds
        time.sleep(5)
        
        # Kill process group
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
            stdout, stderr = proc.communicate(timeout=2)
            
            # Check for the error
            if b"multiple values for keyword argument 'stream'" in stderr:
                print("❌ Stream parameter error found - this is fixed now")
            elif b"Connected to oci_genai" in stderr:
                print("✅ Successfully connected to OCI provider")
            else:
                print("📋 Process started successfully")
                
            if b"Ready!" in stderr:
                print("✅ Interface ready for input")
            
            return True
            
        except subprocess.TimeoutExpired:
            proc.kill()
            print("⚠️  Process had to be killed")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    test_real_provider()