#!/usr/bin/env python3
"""Manual tab testing script - launches web UI for hands-on verification."""

import subprocess
import sys
import time
import webbrowser


def test_web_ui_tabs():
    """Launch web UI and provide manual testing instructions."""
    print("🚀 Phase 7 Web UI - Manual Tab Verification")
    print("=" * 50)

    port = 8530
    url = f"http://localhost:{port}"

    print(f"🌐 Starting web UI on {url}")

    # Start the web UI
    proc = subprocess.Popen(
        ["uv", "run", "coda", "web", "--port", str(port)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    # Wait for startup
    print("⏳ Waiting for server to start...")
    time.sleep(8)

    if proc.poll() is not None:
        stdout, stderr = proc.communicate()
        print("❌ Failed to start web UI")
        print(f"Error: {stderr}")
        return False

    print("✅ Web UI started successfully!")
    print(f"🌐 Opening browser to {url}")

    # Open browser (if possible)
    try:
        webbrowser.open(url)
    except:
        pass

    print("\n" + "=" * 60)
    print("📋 MANUAL VERIFICATION CHECKLIST")
    print("=" * 60)
    print("Please verify each tab works correctly:\n")

    print("📊 DASHBOARD TAB:")
    print("  □ Page loads without errors")
    print("  □ Shows 'Quick Stats' metrics in sidebar")
    print("  □ Displays provider status table")
    print("  □ Shows pie chart for model distribution")
    print("  □ Shows line chart for usage trends")
    print("  □ Charts render without errors\n")

    print("💬 CHAT TAB:")
    print("  □ Page loads without errors")
    print("  □ Provider dropdown shows options")
    print("  □ Model dropdown populates when provider selected")
    print("  □ Chat input box is present")
    print("  □ 'Files' expander opens file upload widget")
    print("  □ 'Download' expander shows download options")
    print("  □ Clear Chat button is visible\n")

    print("📁 SESSIONS TAB:")
    print("  □ Page loads without errors")
    print("  □ Shows search and filter controls")
    print("  □ Displays existing sessions (or 'No sessions found')")
    print("  □ Session expandables show details")
    print("  □ Load/Export/Delete buttons present")
    print("  □ No errors in session listing\n")

    print("⚙️ SETTINGS TAB:")
    print("  □ Page loads without errors")
    print("  □ Shows provider configuration tabs")
    print("  □ OCI/Ollama/LiteLLM sections visible")
    print("  □ Enable/disable checkboxes work")
    print("  □ Configuration forms show fields")
    print("  □ Save buttons are present\n")

    print("🔄 NAVIGATION:")
    print("  □ Sidebar navigation between tabs works")
    print("  □ Page transitions are smooth")
    print("  □ No 404 errors or broken links")
    print("  □ Refresh button in sidebar works")

    print("\n" + "=" * 60)
    print("⌨️  CONTROLS:")
    print("  Press ENTER when done testing")
    print("  Or Ctrl+C to stop immediately")
    print("=" * 60)

    try:
        # Keep server running until user input
        input("\n🔍 Test each tab above, then press ENTER when finished...\n")
        print("✅ Manual testing completed!")

    except KeyboardInterrupt:
        print("\n⚠️  Testing interrupted by user")

    finally:
        # Clean shutdown
        print("\n🛑 Stopping web UI...")
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()
        print("✅ Web UI stopped")

    return True


def main():
    """Main function."""
    try:
        test_web_ui_tabs()
        print("\n🎉 Manual tab verification completed!")
        print("📝 Please report any issues found during testing.")
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
