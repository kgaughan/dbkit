"""
Utility functions used by the tests.
"""

import contextlib
import threading


def skip_first_line(value):
    """Returns everything after the first newline in the string."""
    parts = value.split("\n", 1)
    return parts[1] if len(parts) == 2 else ''


def spawn(targets):
    """Spawns a bunch of threads for given targets and waits on them."""
    threads = []
    for target in targets:
        thread = threading.Thread(target=target)
        thread.start()
        threads.append(thread)
    for thread in threads:
        thread.join()


@contextlib.contextmanager
def set_temporarily(obj, attr, value):
    """Temporarily change the value of an object's attribute."""
    try:
        original = getattr(obj, attr)
        setattr(obj, attr, value)
        yield
    finally:
        setattr(obj, attr, original)
