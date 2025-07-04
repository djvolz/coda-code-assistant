#!/usr/bin/env python3
"""Update version to current timestamp.

This script updates the version in coda/__version__.py to the current
timestamp in year.month.day.HHMM format.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coda.__version__ import update_version

if __name__ == "__main__":
    new_version = update_version()
    print(f"Updated version to: {new_version}")
