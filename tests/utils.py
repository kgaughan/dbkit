"""
Utility functions used by the tests.
"""

import contextlib
import StringIO
import sys

def skip_first_line(value):
    """Returns everything after the first newline in the string."""
    parts = value.split("\n", 1)
    return parts[1] if len(parts) == 2 else ''
