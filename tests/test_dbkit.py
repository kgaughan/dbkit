from contextlib import closing
import sqlite3
import types

import dbkit


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


def test_good_connect():
    ctx = dbkit.connect(sqlite3, ':memory:')
    assert isinstance(ctx, dbkit.Context)
    ctx.close()

def test_bad_connect():
    try:
        dbkit.connect(sqlite3, '/nonexistent.db')
        assert False, "Should not have been able to open database."
    except sqlite3.OperationalError:
        pass

def test_context():
    assert dbkit.Context.current(with_exception=False) is None
    with dbkit.connect(sqlite3, ':memory:') as ctx, closing(ctx):
        assert dbkit.Context.current(with_exception=False) is ctx
        assert ctx.conn is not None
        assert ctx.module is not None
        assert ctx.log is not None
    assert dbkit.Context.current(with_exception=False) is None
    assert ctx.conn is None
    assert ctx.module is None
    assert ctx.log is None

def test_create_table():
    with dbkit.connect(sqlite3, ':memory:'):
        result = dbkit.query_column(LIST_TABLES)
        assert isinstance(result, types.GeneratorType)
        assert len(list(result)) == 0
        dbkit.execute(SCHEMA)
        result = dbkit.query_column(LIST_TABLES)
        assert isinstance(result, types.GeneratorType)
        assert list(result) == [u'counters']

def test_bad_drop_table():
    with dbkit.connect(sqlite3, ':memory:') as ctx:
        dbkit.execute(SCHEMA)
        try:
            dbkit.execute("DROP TABLE kownturs")
            assert False, "Should have triggered an exception."
        except ctx.OperationalError:
            pass

def test_transaction():
    with dbkit.connect(sqlite3, ':memory:'):
        dbkit.execute(SCHEMA)

        # First, make sure the normal case behaves correctly.
        assert dbkit.context().depth == 0
        with dbkit.transaction():
            assert dbkit.context().depth == 1
            dbkit.execute(TEST_DATA)
        assert dbkit.context().depth == 0
        value = dbkit.query_value(GET_COUNTER, ('foo',))
        assert value == 42

        # Now, ensure transactions are rolled back in case of exceptions.
        exception_caught = False
        try:
            with dbkit.transaction():
                dbkit.execute(UPDATE_COUNTER, (13, 'foo'))
                raise Exception()
            assert False, "Should've raised an exception."
        except:
            exception_caught = True
        assert exception_caught
        value = dbkit.query_value(GET_COUNTER, ('foo',))
        assert value == 42

def test_factory():
    with dbkit.connect(sqlite3, ':memory:'):
        dbkit.execute(SCHEMA)
        with dbkit.transaction():
            dbkit.execute(TEST_DATA)

        dbkit.set_factory(dbkit.dict_set)
        row = dbkit.query_row("""
            SELECT counter, value FROM counters WHERE counter = ?
            """, ('foo',))
        assert isinstance(row, dict)
        assert len(row) == 2
        assert 'counter' in row
        assert 'value' in row
        assert row['counter'] == 'foo'
        assert row['value'] == 42

def test_unindent_statement():
    assert dbkit.unindent_statement("foo\nbar") == "foo\nbar"
    assert dbkit.unindent_statement(" foo\n bar") == "foo\nbar"
    assert dbkit.unindent_statement("  foo\n  bar") == "foo\nbar"
    assert dbkit.unindent_statement(" foo\n  bar") == "foo\n bar"
    assert dbkit.unindent_statement("  foo\n bar") == "foo\nar"

# vim:set et ai:
