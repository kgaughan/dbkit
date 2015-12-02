from __future__ import with_statement

import contextlib
import sqlite3
import unittest

import dbkit
import six

from tests import utils, fakedb


SCHEMA = """
CREATE TABLE counters (
    counter TEXT PRIMARY KEY,
    value   INTEGER
)
"""

LIST_TABLES = """
SELECT tbl_name
FROM   sqlite_master
WHERE  type = 'table'
ORDER BY tbl_name
"""

TEST_DATA = """
INSERT INTO counters (counter, value)
VALUES ('foo', 42)
"""

GET_COUNTER = """
SELECT value FROM counters WHERE counter = ?
"""

UPDATE_COUNTER = """
UPDATE counters SET value = ? WHERE counter = ?
"""


class TestBasics(unittest.TestCase):

    def test_good_connect(self):
        with contextlib.closing(dbkit.connect(sqlite3, ':memory:')) as ctx:
            self.assertTrue(isinstance(ctx, dbkit.Context))

    def test_bad_connect(self):
        try:
            with dbkit.connect(sqlite3, '/nonexistent.db') as ctx:
                # Wouldn't do this in real code as the mediator is private.
                with ctx.mdr:
                    pass
            self.fail("Should not have been able to open database.")
        except sqlite3.OperationalError:
            pass

    def test_context(self):
        self.assertTrue(dbkit.Context.current(with_exception=False) is None)
        ctx = dbkit.connect(sqlite3, ':memory:')

        with ctx:
            # Check nesting.
            self.assertEqual(len(ctx.stack), 1)
            with ctx:
                self.assertEqual(len(ctx.stack), 2)
            self.assertEqual(len(ctx.stack), 1)

            self.assertTrue(dbkit.Context.current(with_exception=False) is ctx)
            self.assertTrue(ctx.mdr is not None)
            self.assertTrue(ctx.logger is not None)
        ctx.close()
        try:
            dbkit.context()
            self.fail("Should not have been able to access context.")
        except:
            pass
        self.assertTrue(ctx.mdr is None)
        self.assertTrue(ctx.logger is None)
        self.assertEqual(len(ctx.stack), 0)

    def test_create_table(self):
        with dbkit.connect(sqlite3, ':memory:'):
            result = dbkit.query_column(LIST_TABLES)
            self.assertTrue(hasattr(result, '__iter__'))
            self.assertEqual(len(list(result)), 0)
            dbkit.execute(SCHEMA)
            result = dbkit.query_column(LIST_TABLES)
            self.assertTrue(hasattr(result, '__iter__'))
            self.assertEqual(list(result), [u'counters'])

    def test_transaction(self):
        with dbkit.connect(sqlite3, ':memory:'):
            dbkit.execute(SCHEMA)

            # First, make sure the normal case behaves correctly.
            self.assertEqual(dbkit.context()._depth, 0)
            with dbkit.transaction():
                self.assertEqual(dbkit.context()._depth, 1)
                dbkit.execute(TEST_DATA)
            self.assertEqual(dbkit.context()._depth, 0)
            self.assertEqual(dbkit.query_value(GET_COUNTER, ('foo',)), 42)
            self.assertTrue(dbkit.query_value(GET_COUNTER, ('bar',)) is None)

            # Now, ensure transactions are rolled back in case of exceptions.
            exception_caught = False
            try:
                with dbkit.transaction():
                    dbkit.execute(UPDATE_COUNTER, (13, 'foo'))
                    raise dbkit.AbortTransaction()
                self.fail("Should've raised an exception.")
            except dbkit.AbortTransaction:
                exception_caught = True
            self.assertTrue(exception_caught)
            self.assertEqual(dbkit.query_value(GET_COUNTER, ('foo',)), 42)

    def test_make_file_object_logger(self):
        captured = six.StringIO()
        logger = dbkit.make_file_object_logger(captured)
        logger("STATEMENT", (23, 42))
        # When we get the value, we want to skip the first line, which changes
        # with every call as it contains a date.
        value = utils.skip_first_line(captured.getvalue())
        captured.close()
        self.assertEqual(value, "STATEMENT\nArguments:\n(23, 42)\n")

    def test_logging(self):
        with dbkit.connect(sqlite3, ':memory:') as ctx:
            captured = six.StringIO()
            ctx.logger = dbkit.make_file_object_logger(captured)
            dbkit.query_column(LIST_TABLES)
        value = utils.skip_first_line(captured.getvalue())
        captured.close()
        self.assertEqual(value, "%s\nArguments:\n()\n" % (LIST_TABLES,))

    def test_procs(self):
        def expected(*args):
            result = []
            for arg in args:
                result += ['cursor', arg, 'commit', 'cursor-close']
            return result

        with dbkit.connect(fakedb, 'db') as ctx:
            dbkit.execute_proc('execute_proc')
            dbkit.query_proc_row('query_proc_row')
            dbkit.query_proc_value('query_proc_value')
            list(dbkit.query_proc_column('query_proc_column'))
            conn = ctx.mdr.conn
        self.assertEqual(conn.executed, 4)
        self.assertEqual(conn.session,
                         expected('proc:execute_proc',
                                  'proc:query_proc_row',
                                  'proc:query_proc_value',
                                  'proc:query_proc_column'))

    def test_to_dict_nothing(self):
        result = dbkit.to_dict('foo', [])
        self.assertTrue(isinstance(result, dict))
        self.assertEqual(len(result), 0)

    def test_to_dict_bad_key(self):
        try:
            dbkit.to_dict('foo', [{'bar': 'fred', 'baz': 'barney'}])
            self.fail('Expected KeyError')
        except KeyError:
            pass

    def test_to_dict_happy_path(self):
        row = {'bar': 'fred', 'baz': 'barney'}
        result = dbkit.to_dict('baz', [row])
        self.assertEqual(len(result), 1)
        self.assertTrue('barney' in result)
        self.assertTrue(result['barney'] is row)

    def test_to_dict_sequence(self):
        row = ('fred', 'barney')
        result = dbkit.to_dict(1, [row])
        self.assertEqual(len(result), 1)
        self.assertTrue('barney' in result)
        self.assertTrue(result['barney'] is row)

    def test_make_placeholders(self):
        with dbkit.connect(fakedb, 'db'):
            try:
                dbkit.make_placeholders([])
                self.fail("Expected ValueError")
            except ValueError:
                pass

        with utils.set_temporarily(fakedb, 'paramstyle', 'qmark'):
            with dbkit.connect(fakedb, 'db'):
                self.assertEqual(dbkit.make_placeholders([0]), '?')
                self.assertEqual(dbkit.make_placeholders([0, 1]), '?, ?')
                self.assertEqual(dbkit.make_placeholders([0, 1, 4]), '?, ?, ?')

        for style in ('format', 'pyformat'):
            with utils.set_temporarily(fakedb, 'paramstyle', style):
                with dbkit.connect(fakedb, 'db'):
                    self.assertEqual(dbkit.make_placeholders([0]), '%s')
                    self.assertEqual(dbkit.make_placeholders([0, 2]), '%s, %s')
                    self.assertEqual(dbkit.make_placeholders([0, 2, 7]), '%s, %s, %s')

        with utils.set_temporarily(fakedb, 'paramstyle', 'numeric'):
            with dbkit.connect(fakedb, 'db'):
                self.assertEqual(dbkit.make_placeholders([0], 7), ':7')
                self.assertEqual(dbkit.make_placeholders([0, 1], 7), ':7, :8')
                self.assertEqual(dbkit.make_placeholders([0, 1, 4], 7), ':7, :8, :9')

        def make_sorted(seq):
            """Wrap repetitive code for the next few checks."""
            return utils.sort_fields(dbkit.make_placeholders(seq))

        with utils.set_temporarily(fakedb, 'paramstyle', 'pyformat'):
            with dbkit.connect(fakedb, 'db'):
                self.assertEqual(make_sorted({'foo': None}), '%(foo)s')
                self.assertEqual(make_sorted({'foo': None, 'bar': None}), '%(bar)s, %(foo)s')
                self.assertEqual(make_sorted({'foo': None, 'bar': None, 'baz': None}), '%(bar)s, %(baz)s, %(foo)s')

        with utils.set_temporarily(fakedb, 'paramstyle', 'named'):
            with dbkit.connect(fakedb, 'db'):
                self.assertEqual(make_sorted({'foo': None}), ':foo')
                self.assertEqual(make_sorted({'foo': None, 'bar': None}), ':bar, :foo')
                self.assertEqual(make_sorted({'foo': None, 'bar': None, 'baz': None}), ':bar, :baz, :foo')

        with utils.set_temporarily(fakedb, 'paramstyle', 'qmark'):
            with dbkit.connect(fakedb, 'db'):
                try:
                    dbkit.make_placeholders({'foo': None})
                    self.assertFail("Should've got 'NotSupported' exception.")
                except dbkit.NotSupported as exc:
                    self.assertEqual(str(exc), "Param style 'qmark' does not support sequence type 'dict'")

        with utils.set_temporarily(fakedb, 'paramstyle', 'named'):
            with dbkit.connect(fakedb, 'db'):
                try:
                    dbkit.make_placeholders(['foo'])
                    self.fail("Should've got 'NotSupported' exception.")
                except dbkit.NotSupported as exc:
                    self.assertEqual(str(exc), "Param style 'named' does not support sequence type 'list'")


class TestAgainstDB(unittest.TestCase):

    ctx = None

    def setUp(self):
        """Creates a context fit for testing."""
        self.ctx = dbkit.connect(sqlite3, ':memory:')
        with self.ctx:
            dbkit.execute(SCHEMA)
            with dbkit.transaction():
                dbkit.execute(TEST_DATA)
                self.assertEqual(self.ctx.last_row_count, 1)

    def tearDown(self):
        self.ctx.close()
        self.ctx = None

    def test_bad_drop_table(self):
        with self.ctx:
            try:
                dbkit.execute("DROP TABLE kownturs")
                self.fail("Should have triggered an exception.")
            except self.ctx.OperationalError:
                pass

    def test_transaction_decorator(self):
        @dbkit.transactional
        def update_counter_and_fail(name, value):
            dbkit.execute(UPDATE_COUNTER, (value, name))
            raise dbkit.AbortTransaction()

        with self.ctx:
            exception_caught = False
            try:
                update_counter_and_fail('foo', 13)
            except dbkit.AbortTransaction:
                exception_caught = True
            self.assertTrue(exception_caught)
            self.assertEqual(dbkit.query_value(GET_COUNTER, ('foo',)), 42)

    def test_factory(self):
        self.ctx.default_factory = dbkit.dict_set
        with self.ctx:
            row = dbkit.query_row("""
                SELECT counter, value FROM counters WHERE counter = ?
                """, ('foo',))
            self.assertTrue(isinstance(row, dict))
            self.assertEqual(len(row), 2)
            self.assertTrue('counter' in row)
            self.assertTrue('value' in row)
            self.assertEqual(row['counter'], 'foo')
            self.assertEqual(row['value'], 42)
            row = dbkit.query_row("""
                SELECT counter, value FROM counters WHERE counter = ?
                """, ('bar',))
            self.assertTrue(row is None)

    def test_unpooled_disconnect(self):
        # Test rollback of connection.
        try:
            with self.ctx:
                try:
                    with dbkit.transaction():
                        self.assertEqual(self.ctx.mdr.depth, 1)
                        self.assertTrue(self.ctx.mdr.conn is not None)
                        self.assertEqual(
                            dbkit.query_value(GET_COUNTER, ('foo',)), 42)
                        raise self.ctx.OperationalError("Simulating disconnect")
                except:
                    self.assertEqual(self.ctx.mdr.depth, 0)
                    self.assertTrue(self.ctx.mdr.conn is None)
                    raise
            self.fail("Should've raised OperationalError")
        except self.ctx.OperationalError as exc:
            self.assertEqual(self.ctx.mdr.depth, 0)
            self.assertTrue(self.ctx.mdr.conn is None)
            self.assertEqual(str(exc), "Simulating disconnect")

        # Test reconnect. As we're running this all against an in-memory DB,
        # everything in it will have been throttled, thus the only query we can
        # do is query the list of tables, which will be empty.
        with self.ctx:
            self.assertEqual(len(list(dbkit.query_column(LIST_TABLES))), 0)
            self.assertTrue(self.ctx.mdr.conn is not None)


if __name__ == '__main__':
    unittest.main()

# vim:set et ai:
