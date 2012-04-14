"""
"""

import contextlib
import threading


__all__ = [
    'NoContext',
    'connect', 'transaction',
    'execute', 'query_row', 'query_value', 'query_column']


class NoContext(StandardError):
    """You are attempting to use dbkit outside of a database context."""
    pass


class Context(object):
    """
    """

    __slots__ = ['module', 'conn', 'depth']
    state = threading.local()

    def __init__(self, module, conn):
        super(Context, self).__init__()
        self.module = module
        self.conn = conn
        self.depth = 0

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
        current = cls.state.__dict__.setdefault('current', None)
        if with_exception and current is None:
            raise NoContext()
        return current

    # }}}

    @classmethod
    def execute(cls, query, args)
        ctx = cls.current()
        cursor = ctx.conn.cursor()
        try:
            cursor.execute(query, args)
        except:
            cursor.close()
            raise
        return cursor

    def close(self):
        try:
            self.conn.close()
        finally:
            self.conn = None
            self.module = None


def connect(module, *args, **kwargs):
    """
    """
    conn = module.connect(*args, **kwargs)
    return Context(module, conn)

@contextmanager
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
    """
    return _result_set(Context.execute(query, args))

def query_row(query, args):
    """
    """
    cursor = Context.execute(query, args)
    try:
        row = cursor.fetchone()
    finally:
        cursor.close()
    return row

def query_value(query, args, default=None):
    """
    """
    row = query_row(query, args)
    if row is None:
       return default
    return row[0]

def query_column(query, args):
    """
    """
    return _column_set(Context.execute(query, args))

def _result_set(cursor):
    """Iterator over a statement's results."""
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        yield row
    cursor.close()

def _column_set(cursor):
    """Iterator over a statement's results."""
    while True:
        row = cursor.fetchone()
        if row is None:
            break
        yield row[0]
    cursor.close()

# vim:set et ai:
