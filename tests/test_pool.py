from __future__ import with_statement

import threading
import unittest


import dbkit
from tests import fakedb, utils


class TestPool(unittest.TestCase):

    def setUp(self):
        self.pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)

    def test_check_pool(self):
        self.assertTrue(isinstance(self.pool, dbkit.Pool))
        self.assertTrue(self.pool.module is fakedb)
        self.assertTrue(self.pool.OperationalError is fakedb.OperationalError)
        self.assertEqual(self.pool._allocated, 0)
        self.assertEqual(len(self.pool._pool), 0)

    def test_lazy_connect(self):
        self.assertEqual(len(self.pool._pool), 0)
        with self.pool.connect() as ctx:
            self.assertTrue(isinstance(ctx.mdr, dbkit.PooledConnectionMediator))
            self.assertEqual(self.pool._allocated, 0)
            self.assertEqual(len(self.pool._pool), 0)
        self.assertEqual(self.pool._allocated, 0)
        self.assertEqual(len(self.pool._pool), 0)

    def test_real_connect(self):
        with self.pool.connect():
            with dbkit.transaction():
                self.assertEqual(self.pool._allocated, 1)
                self.assertEqual(len(self.pool._pool), 0)
        self.assertEqual(self.pool._allocated, 1)
        self.assertEqual(len(self.pool._pool), 1)

    def test_bad_query(self):
        with self.pool.connect() as ctx:
            try:
                dbkit.execute("some query")
                self.fail("Should've got an OperationalError")
            except ctx.OperationalError:
                # An operational error will close the connection it occurs on.
                self.assertEqual(self.pool._allocated, 0)


class TestPoolConcurrency(unittest.TestCase):

    def test_pool_contention(self):
        pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)
        # Here, we're testing that the pool behaves properly when it hits its
        # maximum number of connections and a thread it waiting for another one
        # to release the connection it's currently using.
        release = threading.Event()
        spawn = threading.Event()

        def hog_connection():
            with pool.connect():
                with dbkit.transaction():
                    spawn.set()
                    release.wait()

        def wait_on_connection():
            with pool.connect():
                spawn.wait()
                # Request the other thread to release the connection after a
                # short period, enough to ensure the conditional variable
                # managing the pool is waited on by this thread. Basically
                # nearly any pause should be long enough, though 1/100 of a
                # second seems like a reasonable balance.
                #
                # We do this because we want to deterministically introduce a
                # wait on the condition variable that signals when there's a
                # free connection. In normal operation, this happens in a
                # nondeterministic manner. This pause and the use of the
                # release and spawn events ensure that the threads proceed in
                # lockstep to produce the behaviour we need to set.
                threading.Timer(1.0 / 100, lambda: release.set()).start()
                with dbkit.transaction():
                    pass

        utils.spawn([wait_on_connection, hog_connection])

        self.assertEqual(pool._allocated, 1)
        self.assertEqual(len(pool._pool), 1)
        pool.finalise()
        self.assertEqual(pool._allocated, 0)
        self.assertEqual(len(pool._pool), 0)


class TestPropagation(unittest.TestCase):

    def test_setting_propagation(self):
        pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)
        try:
            self.assertTrue(pool.default_factory is dbkit.TupleFactory)
            self.assertTrue(pool.logger is dbkit.null_logger)
            with pool.connect() as ctx:
                self.assertTrue(ctx.default_factory is dbkit.TupleFactory)
                self.assertTrue(ctx.logger is dbkit.null_logger)
        finally:
            pool.finalise()

        pool = dbkit.create_pool(fakedb, 1, fakedb.INVALID_CURSOR)
        try:
            self.assertTrue(pool.default_factory is dbkit.TupleFactory)
            self.assertTrue(pool.logger is dbkit.null_logger)
            pool.default_factory = None
            pool.logger = None
            with pool.connect() as ctx:
                self.assertTrue(ctx.default_factory is None)
                self.assertTrue(ctx.logger is None)
        finally:
            pool.finalise()
