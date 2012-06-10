.. _tutorial:

========
Tutorial
========

A simple application
====================

Let's start with an 'hello, world' example. It's a small application for
manipulating an SQLite database of counter. Here's the schema::

    CREATE TABLE counters (
        counter TEXT PRIMARY KEY,
        value   INTEGER
    );

You'll find that file in the `examples` directory, and it's called
`schema.sql`. Let's create the database::

    $ sqlite3 counters.sqlite < schema.sql

You should now have the database set up.

Now let's import some of the libraries we'll be needing for this project::

    from contextlib import closing
    import sqlite
    import sys

    import aaargh

    from dbkit import (
        connect, execute, query, query_value, query_column,
        transaction, transactional, tuple_set, dict_set)

    app = aaargh.App(description='A counter management tool.')

If you're wondering, `aaargh <http://pypi.python.org/pypi/aaargh/>`_ is
useful Python library for dealing with command line arguments. It's really
good!

There are a few different thing we want to be able to do to the counter,
such as setting a counter, deleting a counter, listing counters,
incrementing a counter, and getting the value of a counter. We'll need to
implement the code to do those.

One of the neat things about `dbkit` is that you don't have to worry about
passing around database connections. Instead, you create a context in
which the queries are ran, and `dbkit` itself does the work. Thus, we can
do something like this::

    value = query_value(
        'SELECT value FROM counters WHERE counter = ?',
        (counter,),
        default=0)

And we don't need to worry about the database connection we're actually
dealing with. With that in mind, here's how we'd implement setting a
counter with the :py:func:`dbkit.execute` function::

    @app.cmd(name='set')
    @app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
    @app.cmd_arg('value', type=int, nargs=1, help='Value name')
    def set_counter(counter, value):
        """Set a counter."""
        execute(
            'REPLACE INTO counters (counter, value) VALUES (?, ?)',
            (counter, value))

Deleting a counter::

    @app.cmd(name='del')
    @app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
    def delete_counter(counter):
        """Delete a counter."""
        execute(
            'DELETE FROM counters WHERE counter = ?',
            (counter,))

Getting the value of a counter, for which we need
:py:func:`dbkit.query_value`::

    @app.cmd(name='get')
    @app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
    def get_counter(counter):
        """Get the value of a counter."""
        print query_value(
            'SELECT value FROM counters WHERE counter = ?',
            (counter,),
            default=0)

`dbkit` also has ways to query for result sets. Once of these is
:py:func:`dbkit.query_column`, which returns an iterable of the first
column in the result set. Thus, to get a list of counters, we'd do this::

    @app.cmd(name='list')
    def list_counters():
        """List the names of all the stored counters."""
        print "\n".join(query_column('SELECT counter FROM counters'))

`dbkit` also makes dealing with transactions very easy. Let's pretend for
a moment that SQLite doesn't let up update a counter with a single query,
but that we have to first query the database and then update it. We want
to do this atomically as we wouldn't want somebody messing up the counter
on us. `dbkit` thus has two ways of dealing with transactions. One is a
decorator you can apply to your functions called
:py:func:`dbkit.transactional`::

    @app.cmd(name='incr')
    @app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
    @app.cmd_arg('by', type=int, nargs=1, help='Amount to change by')
    @transactional
    def increment_counter(counter, by):
        """Modify the value of a counter by a certain amount."""
        update_counter(counter, get_counter(counter) + by)

Or you can use the :py:func:`dbkit.transaction` context manager::
 
    def increment_counter2(counter, by):
        with transaction():
            update_counter(counter, get_counter(counter) + by)

Both are useful in different circumstances.

One last thing that our tool ought to be able to do is dump the contents
of the `counters` table. To do this, we can use :py:func:`dbkit.query`::

    def dump_counters():
        return query('SELECT counter, value FROM counters')

This will return a sequence of result set rows you can iterate over like
so::

    @app.cmd(name='dump')
    def print_counters_and_values():
        """List all the counters and their values."""
        for counter, value in dump_counters():
            print "%s: %d" % (counter, value)

By default, query() will use tuples for each result set row, but if you'd
prefer dictionaries, all you have to do is pass in a different row factory
when you call :py:func:`dbkit.query` using the `factory` parameter::

    def dump_counter_dict():
        return query(
            'SELECT counter, value FROM counters',
            factory=dict_set)

:py:func:`dbkit.dict_set` is a row factory that generates a result set
where each row is a dictionary. The default row factory is
:py:func:`dbkit.tuple_set`, which yields tuples for each row in the result
set. Using :py:func:`dbkit.dict_set`, we'd print the counters and values
like so::

    def print_counters_and_values2():
        for row in dump_counters_dict():
            print "%s: %d" % (row['counter'], row['value'])

Now we have enough for our counter management application, so lets start
on the subcommand function. We'll have the following subcommands: `set`,
`get`, `del`, `list`, `incr`, `list`, and `dump`. `aaargh` does all the
command dispatch for us, so all we need to create a database connection
context with :py:func:`dbkit.context`. It takes the database driver module
as its first argument, and any parameters you'd pass to that module's
`connect()` function to create a new connection as its remaining
arguments::

    if __name__ == '__main__':
        with context(sqlite, 'counters.sqlite') as ctx, closing(ctx):
            app.run()

And bingo! You now has a simple counter manipulation tool.

.. todo:: Connection pools.

.. vim:set tw=74:
