==========================
dbkit notes and to-do list
==========================


Missing functionality
=====================

- Support for executemany, nextset.
- Is there any sense in supporting Two-Phase Commit?


Additional functionality
========================

- Connection pooling


Connection pooling ideas
========================

Having thought about it, I don't think I can easily make dbkit compatible
with DBUtils to provide connection pooling without introducing a
dependency on DBUtils. That I don't want as I'd like dbkit to be useable
without DBUtils. This sucks. If I think of a way around this in the
meantime, consider all this stuff scrapped.

Three implementations: one for type one connections that localise
connections to the current thread, and another for type two and three
connections, which allow sharing of connections. The third one is a null
pool which is context affine. This means that in the default case, things
behave as they currently do.

For an idea of what the access methods of a pool would look like, here's a
rough sketch of the null pool::

    class NullPool(object):
        __slots__ = ['conn']
        def __init__(self, conn):
            self.conn = conn
        def acquire(self):
            return self.conn
        def release(self, conn):
            # Nothing to release.
            pass
        def finalise(self):
            self.conn.close()

Anything using NullPool would have its own instance, anything using a pool
would share a common pool instance.

I don't think there would be any need to change the way that exceptions
are handled. The current reference copying method should do just fine.

I think contexts should hold onto connections until the context is exited.
That seems to be the safest method. Trying to tie it into the row
generation code could be tricky. This might lead to higher resource usage,
but it's probably not enough to justify complicating things.

The connect() function will stay the same. Another function, called pool()
or something like that, will be added. I haven't decided yet whether this
will return a pool for a given set of connection details which will in
turn have a connect() method that will return contexts, or if it'll
maintain the pools implicitly and return contexts. The former is the most
likely as while that means users will need to make an extra call, it's
vastly simpler to implement and is much less likely to leave me painted
into a corner. There's one other benefit: the pool could also have
exception references, which would be nice.

The implementation should be simple enough the pool itself can be
implemented by as either a list or a deque (it'll use a deque) and access
can be controlled using a condition variable.

Because actual control of the pool is managed by the pool itself and any
associated contexts, we can cheat a bit: it's up to the contexts to
acquire and release connections. The act is completely hidden from the
rest of the code.

Connections will be initially created on-demand up to a given limit. As
connections are released, they'll be pushed onto one end of the deque, and
as they're acquired, they'll be pulled off the other end. As they're
pushed on, they'll be pushed on with a timestamp. Any connections that are
idle in the deque for more than a certain period of time will be closed.
To do this right will likely require a daemon thread to occasionally poke
the various pools, but for now a reap method will do.


.. vim:set textwidth=74 et:
