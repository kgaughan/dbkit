==========================
dbkit notes and to-do list
==========================


Missing functionality
=====================

- Support for executemany, nextset.
- Is there any sense in supporting Two-Phase Commit?


Missing documentation
=====================

- Documentation needs to have a 'rationale' section explaining why
  somebody would ever consider using the library, not just its features.
- The current tutorial make the library seem more 'magical' than it
  actually is. Need to work on that.
- Need to explain how to use connection pools.
- Need to explain the :py:func:`dbkit.context` function and how to use the
  `logger` and `default_factory` attributes on a context.
- Need to explain the limitations in how transaction management is
  implemented.
- Need developer documentation detailing how pools and mediators work.
- Need developer documentation detailing how to write your own result
  generator.


Connection pooling ideas
========================

Any connections that are idle in the deque for more than a certain period
of time will be closed. To do this right will likely require a daemon
thread to occasionally poke the various pools, but for now a reap method
will do.


.. vim:set textwidth=74 et lbr:
