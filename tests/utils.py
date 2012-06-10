"""
Utility functions used by the tests.
"""

import contextlib
import StringIO
import sys


@contextlib.contextmanager
def capture_stderr():
    """Patch sys.stderr to capture anything written to it."""
    captured = StringIO.StringIO()
    old_stderr = sys.stderr
    sys.stderr = captured
    try:
        yield captured
    finally:
        sys.stderr = old_stderr

def skip_first_line(value):
    """Returns everything after the first newline in the string."""
    parts = value.split("\n", 1)
    return parts[1] if len(parts) == 2 else ''
