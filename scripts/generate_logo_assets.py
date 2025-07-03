#!/usr/bin/env python3
"""Generate logo assets in various formats and sizes from the SVG source."""

import subprocess
import os
from pathlib import Path

# Define paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "logos"
SVG_FILE = ASSETS_DIR / "coda-terminal-logo.svg"

# PNG sizes to generate
PNG_SIZES = [64, 128, 256, 512, 1024]

def check_dependencies():
    """Check if required tools are installed."""
    try:
        subprocess.run(["convert", "--version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("ImageMagick is required but not installed.")
        print("Install with: brew install imagemagick")
        return False

def generate_png_files():
    """Generate PNG files in various sizes."""
    if not check_dependencies():
        return False
    
    print("Generating PNG files...")
    for size in PNG_SIZES:
        # Maintain aspect ratio (200:140 = 10:7)
        height = int(size * 0.7)
        output_file = ASSETS_DIR / f"coda-terminal-logo-{size}x{height}.png"
        
        cmd = [
            "convert",
            "-background", "none",
            "-density", "300",
            str(SVG_FILE),
            "-resize", f"{size}x{height}",
            str(output_file)
        ]
        
        try:
            subprocess.run(cmd, check=True)
            print(f"  ✓ Generated {output_file.name}")
        except subprocess.CalledProcessError as e:
            print(f"  ✗ Failed to generate {output_file.name}: {e}")
            return False
    
    return True

def generate_ico_file():
    """Generate ICO file for favicon."""
    if not check_dependencies():
        return False
    
    print("Generating ICO file...")
    ico_file = ASSETS_DIR / "coda-terminal-logo.ico"
    
    # Create multiple sizes for ICO
    ico_sizes = [16, 32, 48]
    temp_files = []
    
    try:
        # Generate temporary PNG files for ICO
        for size in ico_sizes:
            height = int(size * 0.7)
            temp_file = ASSETS_DIR / f"temp-{size}.png"
            temp_files.append(temp_file)
            
            cmd = [
                "convert",
                "-background", "none",
                "-density", "300",
                str(SVG_FILE),
                "-resize", f"{size}x{height}",
                str(temp_file)
            ]
            subprocess.run(cmd, check=True)
        
        # Combine into ICO
        cmd = ["convert"] + [str(f) for f in temp_files] + [str(ico_file)]
        subprocess.run(cmd, check=True)
        print(f"  ✓ Generated {ico_file.name}")
        
        # Clean up temp files
        for temp_file in temp_files:
            temp_file.unlink()
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ✗ Failed to generate ICO: {e}")
        # Clean up temp files on error
        for temp_file in temp_files:
            if temp_file.exists():
                temp_file.unlink()
        return False

def main():
    """Generate all logo assets."""
    print("Coda Logo Asset Generator")
    print("=" * 40)
    
    if not SVG_FILE.exists():
        print(f"Error: SVG source file not found at {SVG_FILE}")
        return 1
    
    success = True
    
    # Generate PNG files
    if not generate_png_files():
        success = False
    
    # Generate ICO file
    if not generate_ico_file():
        success = False
    
    if success:
        print("\n✅ All assets generated successfully!")
        print(f"\nFiles created in: {ASSETS_DIR}")
    else:
        print("\n❌ Some assets failed to generate.")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())