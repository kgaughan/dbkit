"""
**dbkit** is a simple high-level database abstraction library for use on
top of DB-API 2 compatible database driver modules. It is intended to be
used in circumstances where it would be impractical or overkill to use an
ORM such as SQLAlchemy or SQLObject, but would be useful to abstract away
much of the boilerplate involved in dealing with DB-API 2 compatible
database drivers.
"""

import contextlib
import threading


__all__ = [
    'NoContext',
    'connect', 'transaction',
    'execute', 'query_row', 'query_value', 'query_column']


# DB-API 2 exceptions exposed by all drivers.
_EXCEPTIONS = [
    'StandardError',
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


class NoContext(StandardError):
    """
    You are attempting to use dbkit outside of a database context.
    """
    pass


class Context(object):
    """
    A database connection context.
    """

    __slots__ = ['module', 'conn', 'depth'] + _EXCEPTIONS
    state = threading.local()

    def __init__(self, module, conn):
        """
        Initialise a context with a given driver module and connection.
        """
        super(Context, self).__init__()
        self.module = module
        self.conn = conn
        self.depth = 0
        # Copy driver module's exception references.
        for exc in _EXCEPTIONS:
            setattr(self, exc, getattr(module, exc))

    # Context stack management {{{

    def __enter__(self):
        self._push_context(self)

    def __exit__(self, _exc_type, _exc_value, _traceback):
        self._pop_context()

    @classmethod
    def _push_context(cls, ctx):
        cls.state.__dict__.setdefault('stack', [])
        cls.state.stack.append(ctx)
        cls.state.current = ctx

    @classmethod
    def _pop_context(cls):
        if cls.current(with_exception=False) is not None:
            stack = cls.state.stack
            stack.pop()
            if len(stack) == 0:
                cls.state.current = None
            else:
                cls.state.current = stack[len(stack) - 1]

    @classmethod
    def current(cls, with_exception=True):
        """Returns the current database context."""
        current = cls.state.__dict__.setdefault('current', None)
        if with_exception and current is None:
            raise NoContext()
        return current

    # }}}

    @classmethod
    def execute(cls, query, args):
        """
        Execute a query, returning a cursor. For internal use only.
        """
        ctx = cls.current()
        cursor = ctx.conn.cursor()
        try:
            cursor.execute(query, args)
        except:
            cursor.close()
            raise
        return cursor

    def close(self):
        """
        Close the connection this context wraps.
        """
        try:
            self.conn.close()
        finally:
            self.conn = None
            self.module = None
            # Clear exception references.
            for exc in _EXCEPTIONS:
                setattr(self, exc, None)


def connect(module, *args, **kwargs):
    """
    Connect to a database using the given DB-API driver module. Returns
    a database context representing that connection.
    """
    conn = module.connect(*args, **kwargs)
    return Context(module, conn)

def context():
    """
    Returns the current database context.
    """
    return Context.current()

@contextlib.contextmanager
def transaction():
    """
    Sets up a context where all the statements within it are ran within a
    single database transaction.
    """
    ctx = Context.current()

    # The idea here is to fake the nesting of transactions. Only when we've
    # gotten back to the topmost transaction context do we actually commit
    # or rollback.
    try:
        ctx.depth += 1
        yield ctx
        ctx.depth -= 1
    except:
        cxt.depth -= 1
        if ctx.depth == 0:
            ctx.conn.rollback()
        raise
    if ctx.depth == 0:
        ctx.conn.commit()

def execute(query, args):
    """
    Execute a query. This returns an iterator of the result set.
    """
    return _result_set(Context.execute(query, args))

def query_row(query, args):
    """
    Execute a query. Returns the first row of the result set, or None.
    """
    cursor = Context.execute(query, args)
    try:
        row = cursor.fetchone()
    finally:
        cursor.close()
    return row

def query_value(query, args, default=None):
    """
    Execute a query, returning the first value in the first row of the
    result set. If the query returns no result set, a default value is
    returned, which is `None` by default.
    """
    row = query_row(query, args)
    if row is None:
       return default
    return row[0]

def query_column(query, args):
    """
    Execute a query, returning an iterable of the first column.
    """
    return _column_set(Context.execute(query, args))

def _result_set(cursor):
    """
    Iterator over a statement's results.
    """
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield row
    finally:
        cursor.close()

def _column_set(cursor):
    """
    Iterator over a statement's results.
    """
    try:
        while True:
            row = cursor.fetchone()
            if row is None:
                break
            yield row[0]
    finally:
        cursor.close()

# Utility functions {{{

def unindent_statement(query):
    """
    Strips leading whitespace from a query based on the indentation
    of the first non-empty line.
    """
    lines = query.split("\n")
    prefix = 0
    for line in lines:
        stripped = line.lstrip()
        if stripped != '':
            prefix = len(line) - len(stripped)
            break
    return "\n".join([line[prefix:] for line in lines])

# }}}

# vim:set et ai:
