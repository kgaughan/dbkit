"""
"""

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

    __slots__ = ['module', 'conn']
    state = threading.local()

    def __init__(self, module, conn):
        super(Context, self).__init__()
        self.module = module
        self.conn = conn

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
        if cls._current() is not None:
            stack = cls.state.stack
            stack.pop()
            if len(stack) == 0:
                cls.state.current = None
            else:
                cls.state.current = stack[len(stack) - 1]

    @classmethod
    def _current(cls):
        return cls.state.__dict__.setdefault('current', None)

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

def transaction():
    """
    """
    pass

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
