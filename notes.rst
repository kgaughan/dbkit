==========================
dbkit notes and to-do list
==========================


Missing functionality
=====================

- Support for executemany, nextset.
- Is there any sense in supporting Two-Phase Commit?


Connection pooling ideas
========================

Any connections that are idle in the deque for more than a certain period
of time will be closed. To do this right will likely require a daemon
thread to occasionally poke the various pools, but for now a reap method
will do.


.. vim:set textwidth=74 et:
