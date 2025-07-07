#!/usr/bin/env python3
"""Generate logo assets in various formats and sizes from the SVG sources."""

import subprocess
from pathlib import Path

# Define paths
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
ASSETS_DIR = PROJECT_ROOT / "assets" / "logos"

# Logo variants with their aspect ratios
LOGO_VARIANTS = {
    "main": {
        "file": "coda-terminal-logo.svg",
        "aspect_ratio": 10 / 7,  # 200:140
        "sizes": [64, 128, 256, 512, 1024],
    },
    "compact": {
        "file": "coda-terminal-logo-compact.svg",
        "aspect_ratio": 4 / 3,  # 120:90
        "sizes": [64, 128, 256, 512],
    },
    "icon": {
        "file": "coda-terminal-logo-icon.svg",
        "aspect_ratio": 1 / 1,  # 80:80 (square)
        "sizes": [16, 32, 48, 64, 128, 256, 512],
    },
}


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
    """Generate PNG files for all variants in various sizes."""
    if not check_dependencies():
        return False

    print("Generating PNG files...")

    for variant_name, variant_info in LOGO_VARIANTS.items():
        svg_file = ASSETS_DIR / variant_info["file"]
        if not svg_file.exists():
            print(f"  ✗ SVG source not found: {svg_file}")
            continue

        print(f"\n  {variant_name.capitalize()} variant:")

        for size in variant_info["sizes"]:
            # Calculate height based on aspect ratio
            height = (
                int(size / variant_info["aspect_ratio"])
                if variant_info["aspect_ratio"] != 1
                else size
            )

            # Generate filename based on variant
            if variant_name == "main":
                output_file = ASSETS_DIR / f"coda-terminal-logo-{size}x{height}.png"
            else:
                output_file = ASSETS_DIR / f"coda-terminal-logo-{variant_name}-{size}x{height}.png"

            cmd = [
                "convert",
                "-background",
                "none",
                "-density",
                "300",
                str(svg_file),
                "-resize",
                f"{size}x{height}",
                str(output_file),
            ]

            try:
                subprocess.run(cmd, check=True)
                print(f"    ✓ Generated {output_file.name}")
            except subprocess.CalledProcessError as e:
                print(f"    ✗ Failed to generate {output_file.name}: {e}")
                return False

    return True


def generate_ico_file():
    """Generate ICO file for favicon using the icon variant."""
    if not check_dependencies():
        return False

    print("\nGenerating ICO file...")
    ico_file = ASSETS_DIR / "coda-terminal-logo.ico"
    icon_svg = ASSETS_DIR / "coda-terminal-logo-icon.svg"

    # Use icon variant for ICO, multiple sizes
    ico_sizes = [16, 32, 48, 64]
    temp_files = []

    try:
        # Generate temporary PNG files for ICO
        for size in ico_sizes:
            temp_file = ASSETS_DIR / f"temp-ico-{size}.png"
            temp_files.append(temp_file)

            cmd = [
                "convert",
                "-background",
                "none",
                "-density",
                "300",
                str(icon_svg),
                "-resize",
                f"{size}x{size}",
                str(temp_file),
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

    # Check that all SVG source files exist
    missing_files = []
    for _variant_name, variant_info in LOGO_VARIANTS.items():
        svg_file = ASSETS_DIR / variant_info["file"]
        if not svg_file.exists():
            missing_files.append(svg_file)

    if missing_files:
        print("Error: Missing SVG source files:")
        for f in missing_files:
            print(f"  - {f}")
        return 1

    success = True

    # Generate PNG files for all variants
    if not generate_png_files():
        success = False

    # Generate ICO file from icon variant
    if not generate_ico_file():
        success = False

    if success:
        print("\n✅ All assets generated successfully!")
        print(f"\nFiles created in: {ASSETS_DIR}")
        print("\nVariants generated:")
        print("  - Main: Full terminal logo")
        print("  - Compact: Small terminal logo")
        print("  - Icon: Square app icon")
    else:
        print("\n❌ Some assets failed to generate.")
        return 1

    return 0


if __name__ == "__main__":
    exit(main())
