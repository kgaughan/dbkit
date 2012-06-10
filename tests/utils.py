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
