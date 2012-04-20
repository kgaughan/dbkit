"""
**dbkit** is a simple high-level database abstraction library for use on
top of DB-API 2 compatible database driver modules. It is intended to be
used in circumstances where it would be impractical or overkill to use an
ORM such as SQLAlchemy or SQLObject, but would be useful to abstract away
much of the boilerplate involved in dealing with DB-API 2 compatible
database drivers.
"""

import contextlib
import datetime
import pprint
import sys
import threading


__all__ = [
    'NoContext',
    'connect', 'context', 'transaction', 'set_logger',
    'execute', 'query_row', 'query_value', 'query_column',
    'dict_set', 'tuple_set',
    'unindent_statement',
    'null_logger', 'stderr_logger']


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


class NoContext(StandardError):
    """
    You are attempting to use dbkit outside of a database context.
    """
    pass


class Context(object):
    """
    A database connection context.
    """

    __slots__ = ['module', 'conn', 'depth', 'log', 'factory'] + _EXCEPTIONS
    state = threading.local()

    def __init__(self, module, conn):
        """
        Initialise a context with a given driver module and connection.
        """
        super(Context, self).__init__()
        self.module = module
        self.conn = conn
        self.depth = 0
        self.log = null_logger
        self.factory = tuple_set
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

    @classmethod
    def execute(cls, stmt, args):
        """
        Execute a query, returning a cursor. For internal use only.
        """
        ctx = cls.current()
        ctx.log(stmt, args)
        cursor = ctx.conn.cursor()
        try:
            cursor.execute(stmt, args)
        except:
            cursor.close()
            raise
        return cursor

    @classmethod
    def execute_proc(cls, procname, args):
        """
        Execute a stored procedure, returning a cursor. For internal use only.
        """
        ctx = cls.current()
        ctx.log(procname, args)
        cursor = ctx.conn.cursor()
        try:
            cursor.callproc(procname, args)
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
            # Clear references to let the garbage collector do its job.
            self.conn = None
            self.module = None
            self.log = None
            for exc in _EXCEPTIONS:
                setattr(self, exc, None)


def connect(module, *args, **kwargs):
    """
    Connect to a database using the given DB-API driver module. Returns
    a database context representing that connection. Any arguments or
    keyword arguments are passed the module's `connect` function.
    """
    conn = module.connect(*args, **kwargs)
    return Context(module, conn)

def context():
    """
    Returns the current database context.
    """
    return Context.current()

def set_logger(logger):
    """
    Set the function used for logging statements and their arguments.

    The logging function should take two arguments: the query and a
    sequence of query arguments.

    There are two supplied logging functions: `null_logger` logs nothing,
    while `stderr_logger` logs its arguments to stderr.
    """
    Context.current().log = logger

def set_factory(factory):
    """
    Set the row factory used for generating rows from `query` and
    `query_row`.

    The factory function should take a cursor an return an iterable
    over the current resultset.
    """
    Context.current().factory = factory

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
        ctx.depth -= 1
        if ctx.depth == 0:
            ctx.conn.rollback()
        raise
    if ctx.depth == 0:
        ctx.conn.commit()

# SQL statement support {{{

def execute(stmt, args=()):
    """
    Execute an SQL statement.
    """
    Context.execute(stmt, args).close()

def query(stmt, args=(), factory=None):
    """
    Execute a query. This returns an iterator of the result set.
    """
    if factory is None:
        factory = Context.current().factory
    return factory(Context.execute(stmt, args))

def query_row(stmt, args=(), factory=None):
    """
    Execute a query. Returns the first row of the result set, or None.
    """
    for row in query(stmt, args, factory):
        return row
    return None

def query_value(stmt, args=(), default=None):
    """
    Execute a query, returning the first value in the first row of the
    result set. If the query returns no result set, a default value is
    returned, which is `None` by default.
    """
    row = query_row(stmt, args)
    if row is None:
        return default
    return row[0]

def query_column(stmt, args=()):
    """
    Execute a query, returning an iterable of the first column.
    """
    return column_set(Context.execute(stmt, args))

# }}}

# Stored procedure support {{{

def execute_proc(procname, args=()):
    """
    Execute a stored procedure.
    """
    Context.execute_proc(procname, args).close()

def query_proc(procname, args=(), factory=None):
    """
    Execute a stored procedure. This returns an iterator of the result set.
    """
    if factory is None:
        factory = Context.current().factory
    return factory(Context.execute_proc(procname, args))

def query_proc_row(procname, args=(), factory=None):
    """
    Execute a stored procedure. Returns the first row of the result set,
    or None.
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
    row = query_proc_row(procname, args)
    if row is None:
        return default
    return row[0]

def query_proc_column(procname, args=()):
    """
    Execute a stored procedure, returning an iterable of the first column.
    """
    return column_set(Context.execute_proc(procname, args))

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
