"""Version information for Coda.

Uses year.month.day.build versioning format.
The build number is the hour and minute (HHMM) of the release.
"""

from datetime import UTC, datetime

# Version format: year.month.day.build
# Example: 2025.1.3.1430 for January 3, 2025 at 14:30 UTC
__version__ = "2025.7.12.0441"  # Auto-updated


def get_current_version():
    """Generate current version based on UTC time."""
    now = datetime.now(UTC)
    return f"{now.year}.{now.month}.{now.day}.{now.hour:02d}{now.minute:02d}"


def update_version():
    """Update the version to current timestamp."""
    new_version = get_current_version()

    # Read the current file
    with open(__file__) as f:
        lines = f.readlines()

    # Update the version line
    for i, line in enumerate(lines):
        if line.startswith("__version__ = "):
            lines[i] = f'__version__ = "{new_version}"  # Auto-updated\n'
            break

    # Write back
    with open(__file__, "w") as f:
        f.writelines(lines)

    return new_version


if __name__ == "__main__":
    # When run directly, update the version
    new_version = update_version()
    print(f"Updated version to: {new_version}")
