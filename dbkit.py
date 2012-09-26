"""
**dbkit** is a simple high-level database abstraction library for use on
top of DB-API 2 compatible database driver modules. It is intended to be
used in circumstances where it would be impractical or overkill to use an
ORM such as SQLAlchemy or SQLObject, but would be useful to abstract away
much of the boilerplate involved in dealing with DB-API 2 compatible
database drivers.
"""

from __future__ import with_statement
import collections
import contextlib
import datetime
import functools
import pprint
import sys
import threading


__all__ = (
    'NoContext', 'NotSupported', 'AbortTransaction',
    'PoolBase', 'Pool',
    'connect', 'context',
    'transaction', 'transactional',
    'execute', 'query_row', 'query_value', 'query_column',
    'execute_proc', 'query_proc_row',
    'query_proc_value', 'query_proc_column',
    'dict_set', 'tuple_set',
    'unindent_statement', 'make_file_object_logger',
    'null_logger', 'stderr_logger')

__version__ = '0.1.3'
__author__ = 'Keith Gaughan'
__email__ = 'k@stereochro.me'


# DB-API 2 exceptions exposed by all drivers.
_EXCEPTIONS = (
    'Warning',
    'Error',
    'InterfaceError',
    'DatabaseError',
    'DataError',
    'OperationalError',
    'IntegrityError',
    'InternalError',
    'ProgrammingError',
    'NotSupportedError')


class NoContext(StandardError):
    """You are attempting to use dbkit outside of a database context."""
    __slots__ = ()


class NotSupported(StandardError):
    """You are attempting something unsupported."""
    __slots__ = ()


class AbortTransaction(Exception):
    """
    Raised to signal that code within the transaction wants to abort it.
    """
    __slots__ = ()


class _ContextStack(threading.local):
    """The context stack for the current thread."""

    def __init__(self):
        super(_ContextStack, self).__init__()
        self.stack = []

    def push(self, ctx):
        """Push a context on top of this stack."""
        self.stack.append(ctx)

    def pop(self):
        """Push a context from the top of this stack."""
        self.stack.pop()

    def top(self):
        """Return the topmost element in this stack."""
        return self.stack[-1] if len(self.stack) > 0 else None

    def __len__(self):
        return len(self.stack)


class Context(object):
    """A database connection context."""

    __slots__ = ('_mdr', '_depth', 'logger', 'default_factory') + _EXCEPTIONS
    stack = _ContextStack()

    def __init__(self, module, mdr):
        """
        Initialise a context with a given driver module and connection.
        """
        super(Context, self).__init__()
        self._mdr = mdr
        self._depth = 0
        self.logger = null_logger
        self.default_factory = tuple_set
        # Copy driver module's exception references.
        for exc in _EXCEPTIONS:
            setattr(self, exc, getattr(module, exc))

    def __enter__(self):
        self.stack.push(self)
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self.stack.pop()

    @classmethod
    def current(cls, with_exception=True):
        """Returns the current database context."""
        if with_exception and len(cls.stack) == 0:
            raise NoContext()
        return cls.stack.top()

    @contextlib.contextmanager
    def transaction(self):
        """
        Sets up a context where all the statements within it are ran within
        a single database transaction. For internal use only.
        """
        # The idea here is to fake the nesting of transactions. Only when
        # we've gotten back to the topmost transaction context do we actually
        # commit or rollback.
        with self._mdr:
            try:
                self._depth += 1
                yield self
                self._depth -= 1
            except self._mdr.OperationalError:
                # We've lost the connection, so there's no sense in
                # attempting to roll back back the transaction.
                self._depth -= 1
                raise
            except:
                self._depth -= 1
                if self._depth == 0:
                    self._mdr.rollback()
                raise
            if self._depth == 0:
                self._mdr.commit()

    @contextlib.contextmanager
    def cursor(self):
        """Get a cursor for the current connection. For internal use only."""
        with self._mdr:
            cursor = self._mdr.cursor()
            try:
                yield cursor
            except:
                cursor.close()
                raise

    def execute(self, stmt, args):
        """Execute a statement, returning a cursor. For internal use only."""
        self.logger(stmt, args)
        with self.cursor() as cursor:
            cursor.execute(stmt, args)
            return cursor

    def execute_proc(self, procname, args):
        """
        Execute a stored procedure, returning a cursor. For internal use
        only.
        """
        self.logger(procname, args)
        with self.cursor() as cursor:
            cursor.callproc(procname, args)
            return cursor

    def close(self):
        """Close the connection this context wraps."""
        self.logger = None
        for exc in _EXCEPTIONS:
            setattr(self, exc, None)
        try:
            self._mdr.close()
        finally:
            self._mdr = None


# pylint: disable-msg=R0903
class ConnectionMediatorBase(object):
    """
    Mediates connection acquisition and release from/to a pool.

    Implementations should keep track of the times they've been entered and
    exited, incrementing a counter for the former and decrementing it for
    the latter. They should acquire a connection when entered with a
    counter value of 0 and release it when exited with a counter value of
    0.
    """

    __slots__ = (
        'OperationalError', 'InterfaceError',
        'conn', 'depth')

    def __init__(self, exceptions):
        super(ConnectionMediatorBase, self).__init__()
        # pylint: disable-msg=C0103
        self.OperationalError = exceptions.OperationalError
        # pylint: disable-msg=C0103
        self.InterfaceError = exceptions.InterfaceError
        # The currently acquired connection, or None.
        self.conn = None
        # When this reaches 0, we release
        self.depth = 0

    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        raise NotImplementedError()

    def cursor(self):
        """Get a cursor for the current connection."""
        raise NotImplementedError()

    def close(self):
        """Called to signal that any resources can be released."""
        raise NotImplementedError()

    def rollback(self):
        """Rollback the current transaction."""
        self.conn.rollback()

    def commit(self):
        """Commit the current transaction."""
        self.conn.commit()


class SingleConnectionMediator(ConnectionMediatorBase):
    """Mediates access to a single unpooled connection."""

    __slots__ = ('connect',)

    def __init__(self, module, connect_):
        super(SingleConnectionMediator, self).__init__(module)
        self.connect = connect_

    def __enter__(self):
        if self.conn is None:
            assert self.depth == 0, "Can only connect outside a transaction."
            self.conn = self.connect()
        self.depth += 1
        return self.conn

    def __exit__(self, exc_type, _exc_value, _traceback):
        self.depth -= 1
        if exc_type is self.OperationalError:
            # pylint: disable-msg=W0702
            try:
                self.conn.close()
            except:  # pragma: no cover
                pass
            self.conn = None

    def cursor(self):
        try:
            return self.conn.cursor()
        except self.InterfaceError:
            self.conn = self.connect()
            return self.conn.cursor()

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None


class PooledConnectionMediator(ConnectionMediatorBase):
    """Mediates connection acquisition and release from/to a pool."""

    __slots__ = ('pool',)

    def __init__(self, pool):
        super(PooledConnectionMediator, self).__init__(pool)
        self.pool = pool

    def __enter__(self):
        if self.depth == 0:
            self.conn = self.pool.acquire()
        self.depth += 1
        return self.conn

    def __exit__(self, exc_type, _exc_value, _traceback):
        self.depth -= 1
        if self.conn is not None:
            if exc_type is self.OperationalError:
                self.pool.discard()
                self.conn = None
            elif self.depth == 0:
                self.pool.release(self.conn)
                self.conn = None

    def cursor(self):
        try:
            return self.conn.cursor()
        except self.InterfaceError:
            # Go through each of the remaining connections
            attempts_left = self.pool.get_max_reattempts()
            while attempts_left > 0:
                self.pool.discard()
                self.conn = self.pool.acquire()
                try:
                    return self.conn.cursor()
                except self.InterfaceError:
                    if attempts_left == 1:
                        raise
                attempts_left -= 1

    def close(self):
        # Nothing currently, but may in the future signal to pool to
        # release a connection.
        pass


# pylint: disable-msg=R0922
class PoolBase(object):
    """Abstract base class for all connection pools."""

    __slots__ = _EXCEPTIONS + (
        'module', 'logger', 'default_factory',
        '_connect')

    def __init__(self, module, threadsafety, args, kwargs):
        if not hasattr(module, 'threadsafety'):
            raise NotSupported("Cannot determine driver threadsafety.")
        if module.threadsafety < threadsafety:
            raise NotSupported("Driver is not sufficiently threadsafe.")
        super(PoolBase, self).__init__()
        self.module = module
        self.logger = null_logger
        self.default_factory = tuple_set
        self._connect = _make_connect(module, args, kwargs)
        for exc in _EXCEPTIONS:
            setattr(self, exc, getattr(module, exc))

    def acquire(self):
        """
        Acquire a connection from the pool and returns it.

        This is intended for internal use only.
        """
        raise NotImplementedError()

    def release(self, conn):
        """
        Release a previously acquired connection back to the pool.

        This is intended for internal use only.
        """
        raise NotImplementedError()

    def discard(self):
        """
        Signal to the pool that a connection has been discarded.

        This is intended for internal use only.
        """
        raise NotImplementedError()

    def finalise(self):
        """
        Shut this pool down. Call this or have it called when you're
        finished with the pool.

        Please note that it is only guaranteed to complete after all
        connections have been returned to the pool for finalisation.
        """
        raise NotImplementedError()

    def connect(self):
        """Returns a context that uses this pool as a connection source."""
        ctx = Context(self.module, PooledConnectionMediator(self))
        ctx.logger = self.logger
        ctx.default_factory = self.default_factory
        return ctx

    # pylint: disable-msg=R0201
    def get_max_reattempts(self):
        """
        Number of times this pool should be reattempted when attempting to
        get a fresh connection.
        """
        return 1


class Pool(PoolBase):
    """A very simple connection pool."""

    __slots__ = ('_pool', '_cond', '_max_conns', '_allocated')

    def __init__(self, module, max_conns, *args, **kwargs):
        super(Pool, self).__init__(module, 2, args, kwargs)
        self._pool = collections.deque()
        self._cond = threading.Condition()
        self._max_conns = max_conns
        self._allocated = 0

    def acquire(self):
        self._cond.acquire()
        try:
            while True:
                if len(self._pool) > 0:
                    conn = self._pool.popleft()
                    break
                elif self._allocated < self._max_conns:
                    # XXX If the user didn't pass in enough arguments for
                    # the connect function, this will throw a TypeError.
                    # It would probably be wise to catch this and convert
                    # the error to something more apt.
                    conn = self._connect()
                    self._allocated += 1
                    break
                else:
                    self._cond.wait()
        finally:
            self._cond.release()
        return conn

    def release(self, conn):
        self._cond.acquire()
        self._pool.append(conn)
        self._cond.notify()
        self._cond.release()

    def discard(self):
        self._cond.acquire()
        self._allocated -= 1
        self._cond.release()

    def finalise(self):
        self._cond.acquire()
        # This is a terribly naive way to wait until all connections have
        # been returned to the pool. That said, if it *doesn't* work, then
        # there's something very odd going on with the client.
        while len(self._pool) < self._allocated:
            self._cond.wait()
        for conn in self._pool:
            # pylint: disable-msg=W0702
            try:
                self._allocated -= 1
                conn.close()
            except:  # pragma: no cover
                pass
        self._pool.clear()
        self._cond.release()

    def get_max_reattempts(self):
        return min(self._allocated + 1, self._max_conns)


def _make_connect(module, args, kwargs):
    """
    Returns a function capable of making connections with a particular
    driver given the supplied credentials.
    """
    # pylint: disable-msg=W0142
    return functools.partial(module.connect, *args, **kwargs)


def connect(module, *args, **kwargs):
    """
    Connect to a database using the given DB-API driver module. Returns
    a database context representing that connection. Any arguments or
    keyword arguments are passed the module's :py:func:`connect` function.
    """
    mdr = SingleConnectionMediator(
        module, _make_connect(module, args, kwargs))
    return Context(module, mdr)


def create_pool(module, max_conns, *args, **kwargs):
    """
    Create a connection pool appropriate to the driver module's capabilities.
    """
    if not hasattr(module, 'threadsafety'):
        raise NotSupported("Cannot determine driver threadsafety.")
    if max_conns < 1:
        raise ValueError("Minimum number of connections is 1.")
    if module.threadsafety >= 2:
        return Pool(module, max_conns, *args, **kwargs)
    raise ValueError("Bad threadsafety level: %d", module.threadsafety)


def context():
    """Returns the current database context."""
    return Context.current()


def transaction():
    """
    Sets up a context where all the statements within it are ran within a
    single database transaction.

    Here's a rough example of how you'd use it::

        import sqlite3
        import sys
        from dbkit import connect, transaction, query_value, execute

        # ...do some stuff...

        with connect(sqlite3, '/path/to/my.db') as ctx:
            try:
                change_ownership(page_id, new_owner_id)
            catch ctx.IntegrityError:
                print >> sys.stderr, "Naughty!"

        def change_ownership(page_id, new_owner_id):
            with transaction():
                old_owner_id = query_value(
                    "SELECT owner_id FROM pages WHERE page_id = ?",
                    (page_id,))
                execute(
                    "UPDATE users SET owned = owned - 1 WHERE id = ?",
                    (old_owner_id,))
                execute(
                    "UPDATE users SET owned = owned + 1 WHERE id = ?",
                    (new_owner_id,))
                execute(
                    "UPDATE pages SET owner_id = ? WHERE page_id = ?",
                    (new_owner_id, page_id))
    """
    return Context.current().transaction()


def transactional(wrapped):
    """
    A decorator to denote that the content of the decorated function or
    method is to be ran in a transaction.

    The following code is equivalent to the example for
    :py:func:`dbkit.transaction`::

        import sqlite3
        import sys
        from dbkit import connect, transactional, query_value, execute

        # ...do some stuff...

        with connect(sqlite3, '/path/to/my.db') as ctx:
            try:
                change_ownership(page_id, new_owner_id)
            catch ctx.IntegrityError:
                print >> sys.stderr, "Naughty!"

        @transactional
        def change_ownership(page_id, new_owner_id):
            old_owner_id = query_value(
                "SELECT owner_id FROM pages WHERE page_id = ?",
                (page_id,))
            execute(
                "UPDATE users SET owned = owned - 1 WHERE id = ?",
                (old_owner_id,))
            execute(
                "UPDATE users SET owned = owned + 1 WHERE id = ?",
                (new_owner_id,))
            execute(
                "UPDATE pages SET owner_id = ? WHERE page_id = ?",
                (new_owner_id, page_id))
    """
    # pylint: disable-msg=C0111
    def wrapper(*args, **kwargs):
        with Context.current().transaction():
            return wrapped(*args, **kwargs)
    return functools.update_wrapper(wrapper, wrapped)


def execute(stmt, args=()):
    """Execute an SQL statement."""
    Context.current().execute(stmt, args).close()


def query(stmt, args=(), factory=None):
    """Execute a query. This returns an iterator of the result set."""
    ctx = Context.current()
    factory = ctx.default_factory if factory is None else factory
    return factory(ctx.execute(stmt, args))


def query_row(stmt, args=(), factory=None):
    """Execute a query. Returns the first row of the result set, or `None`."""
    for row in query(stmt, args, factory):
        return row
    return None


def query_value(stmt, args=(), default=None):
    """
    Execute a query, returning the first value in the first row of the
    result set. If the query returns no result set, a default value is
    returned, which is `None` by default.
    """
    for row in query(stmt, args, tuple_set):
        return row[0]
    return default


def query_column(stmt, args=()):
    """Execute a query, returning an iterable of the first column."""
    return query(stmt, args, column_set)


def execute_proc(procname, args=()):
    """Execute a stored procedure."""
    Context.current().execute_proc(procname, args).close()


def query_proc(procname, args=(), factory=None):
    """
    Execute a stored procedure. This returns an iterator of the result set.
    """
    ctx = Context.current()
    factory = ctx.default_factory if factory is None else factory
    return factory(ctx.execute_proc(procname, args))


def query_proc_row(procname, args=(), factory=None):
    """
    Execute a stored procedure. Returns the first row of the result set,
    or `None`.
    """
    for row in query_proc(procname, args, factory):
        return row
    return None


def query_proc_value(procname, args=(), default=None):
    """
    Execute a stored procedure, returning the first value in the first row
    of the result set. If it returns no result set, a default value is
    returned, which is `None` by default.
    """
    for row in query_proc(procname, args, tuple_set):
        return row[0]
    return default


def query_proc_column(procname, args=()):
    """
    Execute a stored procedure, returning an iterable of the first column.
    """
    return query_proc(procname, args, column_set)


def dict_set(cursor):
    """Iterator over a statement's results as a dict."""
    columns = [col[0] for col in cursor.description]
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield AttrDict(zip(columns, row))
    finally:
        cursor.close()


def tuple_set(cursor):
    """Iterator over a statement's results where each row is a tuple."""
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield row
    finally:
        cursor.close()


def column_set(cursor):
    """Iterator over the first column of a statement's results."""
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield row[0]
    finally:
        cursor.close()


class AttrDict(dict):
    """A dict whose elements may be accessed like object attributes."""

    __slots__ = ()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError, exc:
            raise AttributeError(exc)

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError, exc:
            raise AttributeError(exc)

    def __repr__(self):
        return '<AttrDict ' + dict.__repr__(self) + '>'


def unindent_statement(stmt):
    """
    Strips leading whitespace from a query based on the indentation
    of the first non-empty line.

    This is for use in logging functions for cleaning up query formatting.
    """
    lines = stmt.split("\n")
    prefix = 0
    for line in lines:
        stripped = line.lstrip()
        if stripped != '':
            prefix = len(line) - len(stripped)
            break
    return "\n".join(line[prefix:] for line in lines)


def null_logger(_stmt, _args):
    """A logger that discards everything sent to it."""
    pass


def make_file_object_logger(fh):
    """Make a logger that logs to the given file object."""
    def logger(stmt, args, fh=fh):
        """A logger that logs everything sent to a file object."""
        now = datetime.datetime.now()
        print >> fh, "Executing (%s):" % now.isoformat()
        print >> fh, unindent_statement(stmt)
        print >> fh, "Arguments:"
        pprint.pprint(args, fh)
    return logger


# pylint:disable-msg=C0103
stderr_logger = make_file_object_logger(sys.stderr)

# vim:set et ai:
