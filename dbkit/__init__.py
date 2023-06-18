"""
**dbkit** is a simple high-level database abstraction library for use on top of
DB-API 2 compatible database driver modules. It is intended to be used in
circumstances where it would be impractical or overkill to use an ORM such as
SQLAlchemy or SQLObject, but would be useful to abstract away much of the
boilerplate involved in dealing with DB-API 2 compatible database drivers.
"""

from __future__ import print_function

import collections
import contextlib
import functools
import itertools
import sys
import threading

__all__ = (
    "NoContextError",
    "NotSupportedError",
    "AbortTransactionError",
    "PoolBase",
    "Pool",
    "connect",
    "context",
    "transaction",
    "transactional",
    "execute",
    "query_row",
    "query_value",
    "query_column",
    "execute_proc",
    "query_proc_row",
    "query_proc_value",
    "query_proc_column",
    "DictFactory",
    "TupleFactory",
)

__version__ = "0.2.5"


# DB-API 2 exceptions exposed by all drivers.
_EXCEPTIONS = (
    "Error",
    "InterfaceError",
    "DatabaseError",
    "DataError",
    "OperationalError",
    "IntegrityError",
    "InternalError",
    "ProgrammingError",
    "NotSupportedError",
)


class NoContextError(Exception):
    """
    You are attempting to use dbkit outside of a database context.
    """


class NotSupportedError(Exception):
    """
    You are attempting something unsupported.
    """


class AbortTransactionError(Exception):
    """
    Raised to signal that code within the transaction wants to abort it.
    """


class _ContextStack(threading.local):
    """
    The context stack for the current thread.
    """

    def __init__(self):
        super().__init__()
        self.stack = []

    def push(self, ctx):
        """
        Push a context on top of this stack.
        """
        self.stack.append(ctx)

    def pop(self):
        """
        Push a context from the top of this stack.
        """
        self.stack.pop()

    def top(self):
        """
        Return the topmost element in this stack.
        """
        return self.stack[-1] if len(self.stack) > 0 else None

    def __len__(self):
        return len(self.stack)


class Context:
    """
    A database connection context.
    """

    __slots__ = _EXCEPTIONS + (
        "mdr",
        "_depth",
        "default_factory",
        "param_style",
        "last_row_count",
        "last_row_id",
    )

    stack = _ContextStack()

    def __init__(self, module, mdr):
        """
        Initialise a context with a given driver module and connection.
        """
        self.mdr = mdr
        self._depth = 0
        self.default_factory = TupleFactory
        self.last_row_count = None
        self.last_row_id = None
        self.param_style = module.paramstyle
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
        """
        Returns the current database context.
        """
        if with_exception and len(cls.stack) == 0:
            raise NoContextError()
        return cls.stack.top()

    @contextlib.contextmanager
    def transaction(self):
        """
        Sets up a context where all the statements within it are ran within a
        single database transaction. For internal use only.
        """
        # The idea here is to fake the nesting of transactions. Only when we've
        # gotten back to the topmost transaction context do we actually commit
        # or rollback.
        with self.mdr:
            try:
                self._depth += 1
                yield self
                self._depth -= 1
            except self.mdr.OperationalError:
                # We've lost the connection, so there's no sense in attempting
                # to roll back back the transaction.
                self._depth -= 1
                raise
            except Exception:
                self._depth -= 1
                if self._depth == 0:
                    self.mdr.rollback()
                raise
            if self._depth == 0:
                self.mdr.commit()

    @contextlib.contextmanager
    def cursor(self):
        """
        Get a cursor for the current connection. For internal use only.
        """
        cursor = self.mdr.cursor()
        with self.transaction():
            try:
                yield cursor
                if cursor.rowcount != -1:
                    self.last_row_count = cursor.rowcount
                self.last_row_id = getattr(cursor, "lastrowid", None)
            except Exception:
                self.last_row_count = None
                self.last_row_id = None
                _safe_close(cursor)
                raise

    def execute(self, stmt, args):
        """
        Execute a statement, returning a cursor. For internal use only.
        """
        with self.cursor() as cursor:
            cursor.execute(stmt, args)
            return cursor

    def execute_proc(self, procname, args):
        """
        Execute a stored procedure, returning a cursor. For internal use only.
        """
        with self.cursor() as cursor:
            cursor.callproc(procname, args)
            return cursor

    def close(self):
        """
        Close the connection this context wraps.
        """
        for exc in _EXCEPTIONS:
            setattr(self, exc, None)
        try:
            self.mdr.close()
        finally:
            self.mdr = None


# pylint: disable-msg=R0903
class ConnectionMediatorBase:
    """
    Mediates connection acquisition and release from/to a pool.

    Implementations should keep track of the times they've been entered and
    exited, incrementing a counter for the former and decrementing it for the
    latter. They should acquire a connection when entered with a counter value
    of 0 and release it when exited with a counter value of 0.
    """

    __slots__ = ("OperationalError", "InterfaceError", "DatabaseError", "conn", "depth")

    # pylint: disable-msg=C0103
    def __init__(self, exceptions):
        self.OperationalError = exceptions.OperationalError
        self.InterfaceError = exceptions.InterfaceError
        self.DatabaseError = exceptions.DatabaseError
        # The currently acquired connection, or None.
        self.conn = None
        # When this reaches 0, we release
        self.depth = 0

    def __enter__(self):
        raise NotImplementedError()

    def __exit__(self, _exc_type, _exc_value, _traceback):
        raise NotImplementedError()

    def cursor(self):
        """
        Get a cursor for the current connection.
        """
        raise NotImplementedError()

    def close(self):
        """
        Called to signal that any resources can be released.
        """
        raise NotImplementedError()

    def rollback(self):
        """
        Rollback the current transaction.
        """
        self.conn.rollback()

    def commit(self):
        """
        Commit the current transaction.
        """
        self.conn.commit()


class SingleConnectionMediator(ConnectionMediatorBase):
    """
    Mediates access to a single unpooled connection.
    """

    __slots__ = ("connect",)

    def __init__(self, module, connect_):
        super().__init__(module)
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
            _safe_close(self.conn)
            self.conn = None

    def cursor(self):
        try:
            cursor = self.conn.cursor()
        except (self.InterfaceError, self.DatabaseError):
            del self.conn
            self.conn = self.connect()
            cursor = self.conn.cursor()
        _ping(cursor)
        return cursor

    def close(self):
        if self.conn is not None:
            _safe_close(self.conn)
            self.conn = None


class PooledConnectionMediator(ConnectionMediatorBase):
    """
    Mediates connection acquisition and release from/to a pool.
    """

    __slots__ = ("pool",)

    def __init__(self, pool):
        super().__init__(pool)
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
        cursor = None
        try:
            cursor = self.conn.cursor()
            _ping(cursor)
        except (self.InterfaceError, self.DatabaseError):
            # Go through each of the remaining connections
            attempts_left = self.pool.get_max_reattempts()
            while attempts_left > 0:
                self.pool.discard()
                self.conn = self.pool.acquire()
                try:
                    cursor = self.conn.cursor()
                    _ping(cursor)
                    break
                except (self.InterfaceError, self.DatabaseError):
                    if attempts_left == 1:
                        raise
                attempts_left -= 1
        return cursor

    def close(self):
        # Nothing currently, but may in the future signal to pool to
        # release a connection.
        pass


class PoolBase:
    """
    Abstract base class for all connection pools.
    """

    __slots__ = _EXCEPTIONS + ("module", "default_factory", "_connect")

    def __init__(self, module, threadsafety, args, kwargs):
        if not hasattr(module, "threadsafety"):
            raise NotSupportedError("Cannot determine driver threadsafety.")
        if module.threadsafety < threadsafety:
            raise NotSupportedError("Driver is not sufficiently threadsafe.")
        self.module = module
        self.default_factory = TupleFactory
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
        Shut this pool down. Call this or have it called when you're finished
        with the pool.

        Please note that it is only guaranteed to complete after all
        connections have been returned to the pool for finalisation.
        """
        raise NotImplementedError()

    def create_mediator(self):
        """
        Create a suitable mediator for this pool.
        """
        return PooledConnectionMediator(self)

    def connect(self):
        """
        Returns a context that uses this pool as a connection source.
        """
        ctx = Context(self.module, self.create_mediator())
        ctx.default_factory = self.default_factory
        return ctx

    def get_max_reattempts(self):
        """
        Number of times this pool should be reattempted when attempting to get
        a fresh connection.
        """
        return 1


class Pool(PoolBase):
    """
    A very simple connection pool.
    """

    __slots__ = ("_pool", "_cond", "_max_conns", "_allocated")

    def __init__(self, module, max_conns, *args, **kwargs):
        super().__init__(module, 2, args, kwargs)
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
                if self._allocated < self._max_conns:
                    # XXX If the user didn't pass in enough arguments for the
                    # connect function, this will throw a TypeError. It would
                    # probably be wise to catch this and convert the error to
                    # something more apt.
                    conn = self._connect()
                    self._allocated += 1
                    break
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
        # This is a terribly naive way to wait until all connections have been
        # returned to the pool. That said, if it *doesn't* work, then there's
        # something very odd going on with the client.
        while len(self._pool) < self._allocated:
            self._cond.wait()
        for conn in self._pool:
            self._allocated -= 1
            _safe_close(conn)
        self._pool.clear()
        self._cond.release()

    def get_max_reattempts(self):
        # We retry one extra time to ensure that if the pool is exhausted, we
        # create a fresh connection instead.
        return self._max_conns + 1


class DummyPool(PoolBase):
    """
    A dummy pool that creates a new connection on each acquire and closes it
    upon release.
    """

    __slots__ = ()

    def __init__(self, module, *args, **kwargs):
        super().__init__(module, 1, args, kwargs)

    def acquire(self):
        return self._connect()

    def release(self, conn):
        _safe_close(conn)

    def discard(self):
        pass

    def finalise(self):
        pass

    def get_max_reattempts(self):
        # If we can't connect first time, we can't connect at all.
        return 0


def _make_connect(module, args, kwargs):
    """
    Returns a function capable of making connections with a particular driver
    given the supplied credentials.
    """
    return functools.partial(module.connect, *args, **kwargs)


def connect(module, *args, **kwargs):
    """
    Connect to a database using the given DB-API driver module. Returns a
    database context representing that connection. Any arguments or keyword
    arguments are passed the module's :py:func:`connect` function.
    """
    mdr = SingleConnectionMediator(module, _make_connect(module, args, kwargs))
    return Context(module, mdr)


def create_pool(module, max_conns, *args, **kwargs):
    """
    Create a connection pool appropriate to the driver module's capabilities.
    """
    if not hasattr(module, "threadsafety"):
        raise NotSupportedError("Cannot determine driver threadsafety.")
    if max_conns < 1:
        raise ValueError("Minimum number of connections is 1.")
    if module.threadsafety >= 2:
        return Pool(module, max_conns, *args, **kwargs)
    if module.threadsafety >= 1:
        return DummyPool(module, *args, **kwargs)
    raise ValueError(f"Bad threadsafety level: {module.threadsafety}")


def context():
    """
    Returns the current database context.
    """
    return Context.current()


def transaction():
    """
    Sets up a context where all the statements within it are ran within a
    single database transaction.

    Here's a rough example of how you'd use it:

    ```python
    import sqlite3
    import sys
    from dbkit import connect, transaction, query_value, execute

    # ...do some stuff...

    with connect(sqlite3, '/path/to/my.db') as ctx:
        try:
            change_ownership(page_id, new_owner_id)
        catch ctx.IntegrityError:
            print("Naughty!", file=sys.stderr)

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
    ```
    """
    return Context.current().transaction()


def transactional(wrapped):
    """
    A decorator to denote that the content of the decorated function or method
    is to be ran in a transaction.

    The following code is equivalent to the example for
    [dbkit.transaction]:

    ```python
    import sqlite3
    import sys
    from dbkit import connect, transactional, query_value, execute

    # ...do some stuff...

    with connect(sqlite3, '/path/to/my.db') as ctx:
        try:
            change_ownership(page_id, new_owner_id)
        catch ctx.IntegrityError:
            print("Naughty!", file=sys.stderr)

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
    ```
    """

    # pylint: disable-msg=C0111
    def wrapper(*args, **kwargs):
        with Context.current().transaction():
            return wrapped(*args, **kwargs)

    return functools.update_wrapper(wrapper, wrapped)


def last_row_id():
    """
    Return the row ID of the last (insert) statement.
    """
    return Context.current().last_row_id


def execute(stmt, args=()):
    """
    Execute an SQL statement. Returns the number of affected rows.
    """
    ctx = Context.current()
    with ctx.mdr:
        cursor = ctx.execute(stmt, args)
        row_count = cursor.rowcount
        _safe_close(cursor)
    return row_count


def query(stmt, args=(), factory=None):
    """
    Execute a query. This returns an iterator of the result set.
    """
    ctx = Context.current()
    factory = ctx.default_factory if factory is None else factory
    with ctx.mdr:
        return factory(ctx.execute(stmt, args), ctx.mdr)


def query_row(stmt, args=(), factory=None):
    """
    Execute a query. Returns the first row of the result set, or `None`.
    """
    for row in query(stmt, args, factory):
        return row
    return None


def query_value(stmt, args=(), default=None):
    """
    Execute a query, returning the first value in the first row of the result
    set. If the query returns no result set, a default value is returned, which
    is `None` by default.
    """
    for row in query(stmt, args, TupleFactory):
        return row[0]
    return default


def query_column(stmt, args=()):
    """
    Execute a query, returning an iterable of the first column.
    """
    return query(stmt, args, ColumnFactory)


def execute_proc(procname, args=()):
    """
    Execute a stored procedure. Returns the number of affected rows.
    """
    ctx = Context.current()
    with ctx.mdr:
        cursor = ctx.execute_proc(procname, args)
        row_count = cursor.rowcount
        _safe_close(cursor)
    return row_count


def query_proc(procname, args=(), factory=None):
    """
    Execute a stored procedure. This returns an iterator of the result set.
    """
    ctx = Context.current()
    factory = ctx.default_factory if factory is None else factory
    with ctx.mdr:
        return factory(ctx.execute_proc(procname, args), ctx.mdr)


def query_proc_row(procname, args=(), factory=None):
    """
    Execute a stored procedure. Returns the first row of the result set, or
    `None`.
    """
    for row in query_proc(procname, args, factory):
        return row
    return None


def query_proc_value(procname, args=(), default=None):
    """
    Execute a stored procedure, returning the first value in the first row of
    the result set. If it returns no result set, a default value is returned,
    which is `None` by default.
    """
    for row in query_proc(procname, args, TupleFactory):
        return row[0]
    return default


def query_proc_column(procname, args=()):
    """
    Execute a stored procedure, returning an iterable of the first column.
    """
    return query_proc(procname, args, ColumnFactory)


class FactoryBase:
    """
    Base class for row factories.
    """

    __slots__ = ("cursor", "mdr")

    def __init__(self, cursor, mdr):
        self.cursor = cursor
        self.mdr = mdr
        self.mdr.__enter__()

    def __del__(self):
        self.close()

    def close(self):
        """
        Release all resources associated with this factory.
        """
        if self.mdr is None:
            return
        exc = (None, None, None)
        try:
            self.cursor.close()
        except Exception:
            exc = sys.exc_info()
        try:
            if self.mdr.__exit__(*exc):
                exc = (None, None, None)
        except Exception:
            exc = sys.exc_info()
        self.mdr = None
        self.cursor = None
        if exc != (None, None, None):
            tp, value, tb = exc
            # Taken from six.reraise:
            try:
                if value is None:
                    value = tp()  # pylint: disable=E1102
                if value.__traceback__ is not tb:
                    raise value.with_traceback(tb)
                raise value
            finally:
                value = None
                tb = None

    def __iter__(self):
        return self

    def __next__(self):
        """
        Iterator method to return next row().
        """
        try:
            return self.fetch()
        except Exception:
            self.close()
            raise

    def fetch(self):
        """
        Fetches the next row.
        """
        raise NotImplementedError()


class DictFactory(FactoryBase):
    """
    Iterator over a statement's results as a dict.
    """

    __slots__ = ("columns",)

    def __init__(self, cursor, mdr):
        super().__init__(cursor, mdr)
        self.columns = [col[0] for col in cursor.description]

    def fetch(self):
        row = self.cursor.fetchone()
        if row is None:
            raise StopIteration
        return AttrDict(zip(self.columns, row))


class TupleFactory(FactoryBase):
    """
    Iterator over a statement's results where each row is a tuple.
    """

    __slots__ = ()

    def fetch(self):
        row = self.cursor.fetchone()
        if row is None:
            raise StopIteration
        return row


class ColumnFactory(FactoryBase):
    """
    Iterator over the first column of a statement's results.
    """

    __slots__ = ()

    def fetch(self):
        row = self.cursor.fetchone()
        if row is None:
            raise StopIteration
        return row[0]


class AttrDict(dict):
    """
    A dict whose elements may be accessed like object attributes.
    """

    __slots__ = ()

    def __getattr__(self, key):
        try:
            return self[key]
        except KeyError as exc:
            raise AttributeError(f"Unknown field: {key}") from exc

    def __setattr__(self, key, value):
        self[key] = value

    def __delattr__(self, key):
        try:
            del self[key]
        except KeyError as exc:
            raise AttributeError(f"Unknown field: {key}") from exc

    def __repr__(self):
        return f"<AttrDict {dict.__repr__(self)}>"


def _ping(cursor):
    """
    Ping a connection (given a cursor) in a cross-platform manner.
    """
    cursor.execute("SELECT 1")
    cursor.fetchall()


def _safe_close(obj):
    """
    Call the close method on an object safely.
    """
    # pylint: disable-msg=W0702
    with contextlib.suppress(Exception):
        obj.close()


def to_dict(key, resultset):
    """
    Convert a resultset into a dictionary keyed off of one of its columns.
    """
    return {row[key]: row for row in resultset}


def make_placeholders(seq, start=1):
    """
    Generate placeholders for the given sequence.
    """
    if len(seq) == 0:
        raise ValueError("Sequence must have at least one element.")
    param_style = Context.current().param_style
    placeholders = None
    if isinstance(seq, dict):
        if param_style in ("named", "pyformat"):
            template = ":%s" if param_style == "named" else "%%(%s)s"
            placeholders = (template % key for key in seq.keys())
    elif isinstance(seq, (list, tuple)):
        if param_style == "numeric":
            placeholders = (f":{i}" for i in range(start, start + len(seq)))
        elif param_style in ("qmark", "format", "pyformat"):
            placeholders = itertools.repeat(
                "?" if param_style == "qmark" else "%s", len(seq)
            )
    if placeholders is None:
        raise NotSupportedError(
            f"Param style '{param_style}' does not support sequence type '{seq.__class__.__name__}'"
        )
    return ", ".join(placeholders)


# vim:set et ai:
