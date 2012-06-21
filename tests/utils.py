"""
Utility functions used by the tests.
"""

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
