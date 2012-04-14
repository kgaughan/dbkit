"""
"""

import contextlib
import threading


__all__ = [
    'NoContext',
    'connect', 'transaction',
    'execute', 'execute_many',
    'query_row', 'query_value', 'query_column']


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
    pass

def execute_many():
    """
    """
    pass

def query_row(query, args):
    """
    """
    pass

def query_value(query, args):
    """
    """
    pass

def query_column(query, args):
    """
    """
    pass

# vim:set et ai:
