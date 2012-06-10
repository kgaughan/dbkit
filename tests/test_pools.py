from __future__ import with_statement

import dbkit
from tests import fakedb


POOL = dbkit.Pool(fakedb, 2, fakedb.INVALID_CURSOR)


def test_check_pool():
    assert isinstance(POOL, dbkit.Pool)
    assert POOL.module is fakedb
    assert POOL.OperationalError is fakedb.OperationalError
    assert POOL._allocated == 0
    assert len(POOL._pool) == 0

def test_lazy_connect():
    assert len(POOL._pool) == 0
    with POOL.connect() as ctx:
        assert isinstance(ctx._mdr, dbkit.PooledConnectionMediator)
        assert POOL._allocated == 0
        assert len(POOL._pool) == 0
    assert POOL._allocated == 0
    assert len(POOL._pool) == 0

def test_real_connect():
    with POOL.connect():
        with dbkit.transaction():
            assert POOL._allocated == 1
            assert len(POOL._pool) == 0
    assert POOL._allocated == 1
    assert len(POOL._pool) == 1

def test_bad_query():
    with POOL.connect() as ctx:
        try:
            assert POOL._allocated == 1
            dbkit.execute("some query")
            assert False, "Should've got an OperationalError"
        except ctx.OperationalError:
            # An operational error will close the connection it occurs on.
            assert POOL._allocated == 0
