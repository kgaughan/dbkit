.. _tutorial:

========
Tutorial
========

A simple application
====================

Let's start with an 'hello, world' example. It's a small application for
manipulating an SQLite database of counter. Here's the schema:

.. literalinclude:: ../examples/schema.sql
   :language: sql

You'll find that file in the `examples` directory, and it's called
`schema.sql`. Let's create the database::

    $ sqlite3 counters.sqlite < schema.sql

You should now have the database set up.

Now let's import some of the libraries we'll be needing for this project:

.. literalinclude:: ../examples/counters.py
   :lines: 3-8

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
counter with the :py:func:`dbkit.execute` function:

.. literalinclude:: ../examples/counters.py
   :pyobject: set_counter

Deleting a counter:

.. literalinclude:: ../examples/counters.py
   :pyobject: delete_counter

Getting the value of a counter, for which we need
:py:func:`dbkit.query_value`:

.. literalinclude:: ../examples/counters.py
   :pyobject: get_counter

`dbkit` also has ways to query for result sets. Once of these is
:py:func:`dbkit.query_column`, which returns an iterable of the first
column in the result set. Thus, to get a list of counters, we'd do this:

.. literalinclude:: ../examples/counters.py
   :pyobject: list_counters

`dbkit` also makes dealing with transactions very easy. Let's pretend for
a moment that SQLite doesn't let up update a counter with a single query,
but that we have to first query the database and then update it. We want
to do this atomically as we wouldn't want somebody messing up the counter
on us. `dbkit` thus has two ways of dealing with transactions. One is a
context manager you can use to delimit a transaction called
:py:func:`dbkit.transaction`:

.. literalinclude:: ../examples/counters.py
   :pyobject: increment_counter

Or you can use the :py:func:`dbkit.transactional` decorator::

    @transactional
    def increment_counter(counter, by):
        set_counter(counter, get_counter(counter) + by)

Both are useful in different circumstances.

One last thing that our tool ought to be able to do is dump the contents
of the `counters` table. To do this, we can use :py:func:`dbkit.query`:

.. literalinclude:: ../examples/counters.py
   :pyobject: dump_counters

This will return a sequence of result set rows you can iterate over like
so:

.. literalinclude:: ../examples/counters.py
   :pyobject: print_counters_and_values

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

    def print_counters_and_values():
        for row in dump_counters_dict():
            print '%s: %d' % (row['counter'], row['value'])

Now we have enough for our counter management application, so lets start
on the subcommand function. We'll have the following subcommands: `set`,
`get`, `del`, `list`, `incr`, `list`, and `dump`. `aaargh` does all the
command dispatch for us, so all we need to create a database connection
context with :py:func:`dbkit.context`. It takes the database driver module
as its first argument, and any parameters you'd pass to that module's
`connect()` function to create a new connection as its remaining
arguments:

.. literalinclude:: ../examples/counters.py
   :pyobject: main

.. literalinclude:: ../examples/counters.py
   :pyobject: dispatch

.. literalinclude:: ../examples/counters.py
   :pyobject: print_help

And bingo! You now has a simple counter manipulation tool.

.. todo:: Connection pools.

.. vim:set tw=74:
