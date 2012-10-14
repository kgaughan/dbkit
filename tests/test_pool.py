from __future__ import with_statement
import threading

import dbkit
from tests import fakedb, utils


POOL = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)


def test_check_pool():
    assert isinstance(POOL, dbkit.Pool)
    assert POOL.module is fakedb
    assert POOL.OperationalError is fakedb.OperationalError
    assert POOL._allocated == 0
    assert len(POOL._pool) == 0


def test_lazy_connect():
    assert len(POOL._pool) == 0
    with POOL.connect() as ctx:
        assert isinstance(ctx.mdr, dbkit.PooledConnectionMediator)
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


def test_pool_contention():
    pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)
    # Here, we're testing that the pool behaves properly when it hits its
    # maximum number of connections and a thread it waiting for another one
    # to release the connection it's currently using.
    release = threading.Event()
    spawn = threading.Event()

    def hog_connection():
        with pool.connect() as ctx:
            with dbkit.transaction():
                spawn.set()
                release.wait()

    def wait_on_connection():
        with pool.connect() as ctx:
            spawn.wait()
            # Request the other thread to release the connection after a
            # short period, enough to ensure the conditional variable
            # managing the pool is waited on by this thread. Basically
            # nearly any pause should be long enough, though 1/100 of a
            # second seems like a reasonable balance.
            #
            # We do this because we want to deterministically introduce a
            # wait on the condition variable that signals when there's a free
            # connection. In normal operation, this happens in a
            # nondeterministic manner. This pause and the use of the release
            # and spawn events ensure that the threads proceed in lockstep
            # to produce the behaviour we need to set.
            threading.Timer(1.0 / 100, lambda: release.set()).start()
            with dbkit.transaction():
                pass
    utils.spawn([wait_on_connection, hog_connection])

    assert pool._allocated == 1
    assert len(pool._pool) == 1
    pool.finalise()
    assert pool._allocated == 0
    assert len(pool._pool) == 0


def test_setting_propagation():
    pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)
    try:
        assert pool.default_factory is dbkit.TupleFactory
        assert pool.logger is dbkit.null_logger
        with pool.connect() as ctx:
            assert ctx.default_factory is dbkit.TupleFactory
            assert ctx.logger is dbkit.null_logger
    finally:
        pool.finalise()

    pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)
    try:
        assert pool.default_factory is dbkit.TupleFactory
        assert pool.logger is dbkit.null_logger
        pool.default_factory = None
        pool.logger = None
        with pool.connect() as ctx:
            assert ctx.default_factory is None
            assert ctx.logger is None
    finally:
        pool.finalise()
