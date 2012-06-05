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
import logging
import pprint
import sys
import threading


__all__ = [
    'NoContext', 'NotSupported', 'AbortTransaction',
    'PoolBase', 'Pool',
    'connect', 'context',
    'transaction', 'transactional',
    'execute', 'query_row', 'query_value', 'query_column',
    'execute_proc', 'query_proc_row', 'query_proc_value', 'query_proc_column',
    'dict_set', 'tuple_set',
    'unindent_statement',
    'null_logger', 'stderr_logger']

__version__ = '0.1.0'


# DB-API 2 exceptions exposed by all drivers.
_EXCEPTIONS = [
    'Warning',
    'Error',
    'InterfaceError',
    'DatabaseError',
    'DataError',
    'OperationalError',
    'IntegrityError',
    'InternalError',
    'ProgrammingError',
    'NotSupportedError']

# For the module's own internal logging.
LOG = logging.getLogger(__name__)


class NoContext(StandardError):
    """
    You are attempting to use dbkit outside of a database context.
    """
    pass


class NotSupported(StandardError):
    """
    You are attempting something unsupported.
    """
    pass


class AbortTransaction(Exception):
    """
    Raised to signal that code within the transaction wants to abort it.
    """
    pass

# Contexts {{{

class Context(object):
    """
    A database connection context.
    """

    __slots__ = ['mdr', 'depth', 'logger', 'default_factory'] + _EXCEPTIONS
    state = threading.local()

    def __init__(self, module, mdr):
        """
        Initialise a context with a given driver module and connection.
        """
        super(Context, self).__init__()
        self.mdr = mdr
        self.depth = 0
        self.logger = null_logger
        self.default_factory = tuple_set
        # Copy driver module's exception references.
        for exc in _EXCEPTIONS:
            setattr(self, exc, getattr(module, exc))

    # Context stack management {{{

    def __enter__(self):
        self._push_context(self)
        return self

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self._pop_context()

    @classmethod
    def _push_context(cls, ctx):
        """Push a context onto the context stack."""
        cls.state.__dict__.setdefault('stack', [])
        cls.state.stack.append(ctx)
        cls.state.current = ctx

    @classmethod
    def _pop_context(cls):
        """Pop the topmost context from the context stack."""
        if cls.current(with_exception=False) is not None:
            stack = cls.state.stack
            stack.pop()
            if len(stack) == 0:
                cls.state.current = None
            else:
                cls.state.current = stack[len(stack) - 1]

    @classmethod
    def current(cls, with_exception=True):
        """
        Returns the current database context.
        """
        current = cls.state.__dict__.setdefault('current', None)
        if with_exception and current is None:
            raise NoContext()
        return current

    # }}}

    @contextlib.contextmanager
    def transaction(self):
        """
        Sets up a context where all the statements within it are ran within
        a single database transaction. For internal use only.
        """
        # The idea here is to fake the nesting of transactions. Only when
        # we've gotten back to the topmost transaction context do we actually
        # commit or rollback.
        with self.mdr as conn:
            try:
                self.depth += 1
                yield self
                self.depth -= 1
            except self.mdr.OperationalError:
                # We've lost the connection, so there's no sense in
                # attempting to roll back back the transaction.
                self.depth -= 1
                raise
            except:
                self.depth -= 1
                if self.depth == 0:
                    conn.rollback()
                raise
            if self.depth == 0:
                conn.commit()

    @contextlib.contextmanager
    def cursor(self):
        """
        Get a cursor for the current connection. For internal use only.
        """
        with self.mdr as conn:
            cursor = conn.cursor()
            try:
                yield cursor
            except:
                cursor.close()
                raise

    def execute(self, stmt, args):
        """
        Execute a statement, returning a cursor. For internal use only.
        """
        self.logger(stmt, args)
        with self.cursor() as cursor:
            cursor.execute(stmt, args)
            return cursor

    def query(self, stmt, args, factory):
        """
        Executes a statement, returning a factory. For internal use only.
        """
        factory = self.default_factory if factory is None else factory
        return factory(self.execute(stmt, args))

    def execute_proc(self, procname, args):
        """
        Execute a stored procedure, returning a cursor. For internal use
        only.
        """
        self.logger(procname, args)
        with self.cursor() as cursor:
            cursor.callproc(procname, args)
            return cursor

    def query_proc(self, procname, args, factory):
        """
        Execute a stored procedure, returning a factory. For internal use
        only.
        """
        factory = self.default_factory if factory is None else factory
        return factory(self.execute_proc(procname, args))

    def close(self):
        """
        Close the connection this context wraps.
        """
        self.logger = None
        for exc in _EXCEPTIONS:
            setattr(self, exc, None)
        try:
            self.mdr.close()
        finally:
            self.mdr = None

# }}}

# Connection access mediation {{{

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

    __slots__ = ['OperationalError', 'conn', 'depth']

    def __init__(self, exceptions):
        super(ConnectionMediatorBase, self).__init__()
        # pylint: disable-msg=C0103
        self.OperationalError = exceptions.OperationalError
        # The currently acquired connection, or None.
        self.conn = None
        # When this reaches 0, we release
        self.depth = 0

    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        raise NotImplementedError()

    def close(self):
        """
        Called to signal that any resources can be released.
        """
        raise NotImplementedError()


class SingleConnectionMediator(ConnectionMediatorBase):
    """
    Mediates access to a single unpooled connection.
    """

    __slots__ = ['connect']

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
            except:
                pass
            self.conn = None

    def close(self):
        if self.conn is not None:
            try:
                self.conn.close()
            finally:
                self.conn = None


class PooledConnectionMediator(ConnectionMediatorBase):
    """
    Mediates connection acquisition and release from/to a pool.
    """

    __slots__ = ['pool']

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

    def close(self):
        # Nothing currently, but may in the future signal to pool to
        # release a connection.
        pass

# }}}

# Pools {{{

# pylint: disable-msg=R0922
class PoolBase(object):
    """
    Abstract base class for all connection pools.
    """

    __slots__ = ['module'] + _EXCEPTIONS

    def __init__(self, module):
        super(PoolBase, self).__init__()
        self.module = module
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
        Signal to the pool that a connect has been discarded.

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
        """
        Returns a context that uses this pool as a connection source.
        """
        return Context(self.module, PooledConnectionMediator(self))


class Pool(PoolBase):
    """
    A very simple connection pool.
    """

    __slots__ = [
        '_pool', '_cond',
        '_max_conns', '_allocated',
        '_connect']

    def __init__(self, module, max_conns, *args, **kwargs):
        try:
            if module.threadsafety not in (2, 3):
                raise NotSupported(
                    "Connection pooling requires a threadsafe driver.")
        except AttributeError:
            raise NotSupported("Cannot determine driver threadsafety.")
        super(Pool, self).__init__(module)
        self._pool = collections.deque()
        self._cond = threading.Condition()
        self._max_conns = max_conns
        self._allocated = 0
        self._connect = _make_connect(module, args, kwargs)

    def acquire(self):
        self._cond.acquire()
        try:
            while True:
                if len(self._pool) > 0:
                    conn = self._pool.popleft()
                    break
                elif self._allocated < self._max_conns:
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
            except:
                pass
        self._cond.release()

# }}}

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
    keyword arguments are passed the module's `connect` function.
    """
    mdr = SingleConnectionMediator(
            module,
            _make_connect(module, args, kwargs))
    return Context(module, mdr)

def context():
    """
    Returns the current database context.
    """
    return Context.current()

def transaction():
    """
    Sets up a context where all the statements within it are ran within a
    single database transaction.

    Here's a rough example of how you'd use it::

        import sqlite3
        import sys
        from dbkit import connect, transaction, query_value, execute, context

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

    The following code is equivalent to the example for `transaction`::

        import sqlite3
        import sys
        from dbkit import connect, transactional, query_value, execute, context

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

# SQL statement support {{{

def execute(stmt, args=()):
    """
    Execute an SQL statement.
    """
    Context.current().execute(stmt, args).close()

def query(stmt, args=(), factory=None):
    """
    Execute a query. This returns an iterator of the result set.
    """
    return Context.current().query(stmt, args, factory)

def query_row(stmt, args=(), factory=None):
    """
    Execute a query. Returns the first row of the result set, or `None`
    """
    for row in Context.current().query(stmt, args, factory):
        return row
    return None

def query_value(stmt, args=(), default=None):
    """
    Execute a query, returning the first value in the first row of the
    result set. If the query returns no result set, a default value is
    returned, which is `None` by default.
    """
    for row in Context.current().query(stmt, args, tuple_set):
        return row[0]
    return default

def query_column(stmt, args=()):
    """
    Execute a query, returning an iterable of the first column.
    """
    return Context.current().query(stmt, args, column_set)

# }}}

# Stored procedure support {{{

def execute_proc(procname, args=()):
    """
    Execute a stored procedure.
    """
    Context.current().execute_proc(procname, args).close()

def query_proc(procname, args=(), factory=None):
    """
    Execute a stored procedure. This returns an iterator of the result set.
    """
    return Context.current().query_proc(procname, args, factory)

def query_proc_row(procname, args=(), factory=None):
    """
    Execute a stored procedure. Returns the first row of the result set,
    or `None`.
    """
    for row in Context.current().query(procname, args, factory):
        return row
    return None

def query_proc_value(procname, args=(), default=None):
    """
    Execute a stored procedure, returning the first value in the first row
    of the result set. If it returns no result set, a default value is
    returned, which is `None` by default.
    """
    for row in Context.current().query_proc(procname, args, tuple_set):
        return row[0]
    return default

def query_proc_column(procname, args=()):
    """
    Execute a stored procedure, returning an iterable of the first column.
    """
    return Context.current().query_proc(procname, args, column_set)

# }}}

# Result generators {{{

def dict_set(cursor):
    """
    Iterator over a statement's results as a dict.
    """
    columns = [col[0] for col in cursor.description]
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield dict(zip(columns, row))
    finally:
        cursor.close()

def tuple_set(cursor):
    """
    Iterator over a statement's results where each row is a tuple.
    """
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield row
    finally:
        cursor.close()

def column_set(cursor):
    """
    Iterator over the first column of a statement's results.
    """
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield row[0]
    finally:
        cursor.close()

# }}}

# Utility functions {{{

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
    return "\n".join([line[prefix:] for line in lines])

# }}}

# Logging support {{{

def null_logger(_stmt, _args):
    """
    A logger that discards everything sent to it.
    """
    pass

def stderr_logger(stmt, args):
    """
    A logger that logs everything sent to it to standard error.
    """
    now = datetime.datetime.now()
    print >> sys.stderr, "Executing (%s):" % now.isoformat()
    print >> sys.stderr, unindent_statement(stmt)
    print >> sys.stderr, "Arguments:"
    pprint.pprint(args, sys.stderr)

# }}}

# vim:set et ai:
