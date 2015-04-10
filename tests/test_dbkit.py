from __future__ import with_statement

import sqlite3
import StringIO
import types

import dbkit
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


def setup():
    """Creates a context fit for testing."""
    with dbkit.connect(sqlite3, ':memory:') as ctx:
        dbkit.execute(SCHEMA)
        with dbkit.transaction():
            dbkit.execute(TEST_DATA)
            assert ctx.last_row_count == 1
    return ctx


def test_good_connect():
    ctx = dbkit.connect(sqlite3, ':memory:')
    assert isinstance(ctx, dbkit.Context)
    ctx.close()


def test_bad_connect():
    try:
        with dbkit.connect(sqlite3, '/nonexistent.db') as ctx:
            # Wouldn't do this in real code as the mediator is private.
            with ctx.mdr:
                pass
        assert False, "Should not have been able to open database."
    except sqlite3.OperationalError:
        pass


def test_context():
    assert dbkit.Context.current(with_exception=False) is None
    ctx = dbkit.connect(sqlite3, ':memory:')

    with ctx:
        # Check nesting.
        assert len(ctx.stack) == 1
        with ctx:
            assert len(ctx.stack) == 2
        assert len(ctx.stack) == 1

        assert dbkit.Context.current(with_exception=False) is ctx
        assert ctx.mdr is not None
        assert ctx.logger is not None
    ctx.close()
    try:
        dbkit.context()
        assert False, "Should not have been able to access context."
    except:
        pass
    assert ctx.mdr is None
    assert ctx.logger is None
    assert len(ctx.stack) == 0


def test_create_table():
    with dbkit.connect(sqlite3, ':memory:'):
        result = dbkit.query_column(LIST_TABLES)
        assert hasattr(result, '__iter__')
        assert len(list(result)) == 0
        dbkit.execute(SCHEMA)
        result = dbkit.query_column(LIST_TABLES)
        assert hasattr(result, '__iter__')
        assert list(result) == [u'counters']


def test_bad_drop_table():
    with setup() as ctx:
        try:
            dbkit.execute("DROP TABLE kownturs")
            assert False, "Should have triggered an exception."
        except ctx.OperationalError:
            pass


def test_transaction():
    with dbkit.connect(sqlite3, ':memory:'):
        dbkit.execute(SCHEMA)

        # First, make sure the normal case behaves correctly.
        assert dbkit.context()._depth == 0
        with dbkit.transaction():
            assert dbkit.context()._depth == 1
            dbkit.execute(TEST_DATA)
        assert dbkit.context()._depth == 0
        assert dbkit.query_value(GET_COUNTER, ('foo',)) == 42
        assert dbkit.query_value(GET_COUNTER, ('bar',)) is None

        # Now, ensure transactions are rolled back in case of exceptions.
        exception_caught = False
        try:
            with dbkit.transaction():
                dbkit.execute(UPDATE_COUNTER, (13, 'foo'))
                raise dbkit.AbortTransaction()
            assert False, "Should've raised an exception."
        except dbkit.AbortTransaction:
            exception_caught = True
        assert exception_caught
        value = dbkit.query_value(GET_COUNTER, ('foo',))
        assert value == 42


def test_transaction_decorator():
    @dbkit.transactional
    def update_counter_and_fail(name, value):
        dbkit.execute(UPDATE_COUNTER, (value, name))
        raise dbkit.AbortTransaction()

    with setup():
        exception_caught = False
        try:
            update_counter_and_fail('foo', 13)
        except dbkit.AbortTransaction:
            exception_caught = True
        assert exception_caught
        value = dbkit.query_value(GET_COUNTER, ('foo',))
        assert value == 42


def test_factory():
    with setup() as ctx:
        ctx.default_factory = dbkit.dict_set
        row = dbkit.query_row("""
            SELECT counter, value FROM counters WHERE counter = ?
            """, ('foo',))
        assert isinstance(row, dict)
        assert len(row) == 2
        assert 'counter' in row
        assert 'value' in row
        assert row['counter'] == 'foo'
        assert row['value'] == 42
        row = dbkit.query_row("""
            SELECT counter, value FROM counters WHERE counter = ?
            """, ('bar',))
        assert row is None


def test_unpooled_disconnect():
    ctx = setup()

    # Test rollback of connection.
    try:
        with ctx:
            try:
                with dbkit.transaction():
                    assert ctx.mdr.depth == 1
                    assert ctx.mdr.conn is not None
                    assert dbkit.query_value(GET_COUNTER, ('foo',)) == 42
                    raise ctx.OperationalError("Simulating disconnect")
            except:
                assert ctx.mdr.depth == 0
                assert ctx.mdr.conn is None
                raise
        assert False, "Should've raised OperationalError"
    except ctx.OperationalError, exc:
        assert ctx.mdr.depth == 0
        assert ctx.mdr.conn is None
        assert str(exc) == "Simulating disconnect"

    # Test reconnect. As we're running this all against an in-memory DB,
    # everything in it will have been throttled, thus the only query we can
    # do is query the list of tables, which will be empty.
    with ctx:
        assert len(list(dbkit.query_column(LIST_TABLES))) == 0
        assert ctx.mdr.conn is not None

    ctx.close()


def test_make_file_object_logger():
    captured = StringIO.StringIO()
    logger = dbkit.make_file_object_logger(captured)
    logger("STATEMENT", (23, 42))
    # When we get the value, we want to skip the first line, which changes
    # with every call as it contains a date.
    value = utils.skip_first_line(captured.getvalue())
    captured.close()
    assert value == "STATEMENT\nArguments:\n(23, 42)\n"


def test_logging():
    with dbkit.connect(sqlite3, ':memory:') as ctx:
        captured = StringIO.StringIO()
        ctx.logger = dbkit.make_file_object_logger(captured)
        dbkit.query_column(LIST_TABLES)
    value = utils.skip_first_line(captured.getvalue())
    captured.close()
    assert value == "%s\nArguments:\n()\n" % (LIST_TABLES,)


def test_procs():
    with dbkit.connect(fakedb, 'db') as ctx:
        dbkit.execute_proc('execute_proc')
        dbkit.query_proc_row('query_proc_row')
        dbkit.query_proc_value('query_proc_value')
        list(dbkit.query_proc_column('query_proc_column'))
        conn = ctx.mdr.conn
    assert conn.executed == 4
    assert conn.session == [
        'cursor', 'proc:execute_proc', 'cursor-close',
        'cursor', 'proc:query_proc_row', 'cursor-close',
        'cursor', 'proc:query_proc_value', 'cursor-close',
        'cursor', 'proc:query_proc_column', 'cursor-close']


def test_to_dict_nothing():
    result = dbkit.to_dict('foo', [])
    assert isinstance(result, dict) and len(result) == 0


def test_to_dict_bad_key():
    try:
        dbkit.to_dict('foo', [{'bar': 'fred', 'baz': 'barney'}])
        assert False, 'Expected KeyError'
    except KeyError:
        pass


def test_to_dict_happy_path():
    row = {'bar': 'fred', 'baz': 'barney'}
    result = dbkit.to_dict('baz', [row])
    assert len(result) == 1
    assert 'barney' in result
    assert result['barney'] is row


def test_to_dict_sequence():
    row = ('fred', 'barney')
    result = dbkit.to_dict(1, [row])
    assert len(result) == 1
    assert 'barney' in result
    assert result['barney'] is row


def test_make_placeholders():
    with dbkit.connect(fakedb, 'db') as ctx:
        try:
            dbkit.make_placeholders([])
            assert False, "Expected ValueError"
        except ValueError:
            pass

    with utils.set_temporarily(fakedb, 'paramstyle', 'qmark'):
        with dbkit.connect(fakedb, 'db') as ctx:
            assert dbkit.make_placeholders([0]) == '?'
            assert dbkit.make_placeholders([0, 1]) == '?, ?'
            assert dbkit.make_placeholders([0, 1, 4]) == '?, ?, ?'

    for style in ('format', 'pyformat'):
        with utils.set_temporarily(fakedb, 'paramstyle', style):
            with dbkit.connect(fakedb, 'db') as ctx:
                assert dbkit.make_placeholders([0]) == '%s'
                assert dbkit.make_placeholders([0, 2]) == '%s, %s'
                assert dbkit.make_placeholders([0, 2, 7]) == '%s, %s, %s'

    with utils.set_temporarily(fakedb, 'paramstyle', 'numeric'):
        with dbkit.connect(fakedb, 'db') as ctx:
            assert dbkit.make_placeholders([0], 7) == ':7'
            assert dbkit.make_placeholders([0, 1], 7) == ':7, :8'
            assert dbkit.make_placeholders([0, 1, 4], 7) == ':7, :8, :9'

    def sort_fields(fields):
        """Helper to ensure named fields are sorted for the test."""
        return ', '.join(sorted(field.lstrip() for field in fields.split(',')))

    def make_sorted(seq):
        """Wrap repetitive code for the next few checks."""
        return sort_fields(dbkit.make_placeholders(seq))

    with utils.set_temporarily(fakedb, 'paramstyle', 'pyformat'):
        with dbkit.connect(fakedb, 'db') as ctx:
            assert make_sorted({'foo': None}) == '%(foo)s'
            assert make_sorted({'foo': None, 'bar': None}) == '%(bar)s, %(foo)s'
            assert make_sorted({'foo': None, 'bar': None, 'baz': None}) == '%(bar)s, %(baz)s, %(foo)s'

    with utils.set_temporarily(fakedb, 'paramstyle', 'named'):
        with dbkit.connect(fakedb, 'db') as ctx:
            assert make_sorted({'foo': None}) == ':foo'
            assert make_sorted({'foo': None, 'bar': None}) == ':bar, :foo'
            assert make_sorted({'foo': None, 'bar': None, 'baz': None}) == ':bar, :baz, :foo'

    with utils.set_temporarily(fakedb, 'paramstyle', 'qmark'):
        with dbkit.connect(fakedb, 'db') as ctx:
            try:
                print dbkit.make_placeholders({'foo': None})
                assert False, "Should've got 'NotSupported' exception."
            except dbkit.NotSupported, exc:
                assert str(exc) == "Param style 'qmark' does not support sequence type 'dict'"

    with utils.set_temporarily(fakedb, 'paramstyle', 'named'):
        with dbkit.connect(fakedb, 'db') as ctx:
            try:
                print dbkit.make_placeholders(['foo'])
                assert False, "Should've got 'NotSupported' exception."
            except dbkit.NotSupported, exc:
                assert str(exc) == "Param style 'named' does not support sequence type 'list'"

# vim:set et ai:
