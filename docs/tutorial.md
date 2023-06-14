# Tutorial

## A simple application

Let's start with an 'hello, world' example. It's a small application
for manipulating an SQLite database of counter. Here's the schema:

``` {.literalinclude language="sql"}
../examples/counters.sql
```

You'll find that file in the `examples` directory, and it's called
`counters.sql`. Let's create the database:

    $ sqlite3 counters.sqlite < counters.sql

You should now have the database set up.

Now let's import some of the libraries we'll be needing for this
project:

``` {.literalinclude lines="3-8"}
../examples/counters.py
```

There are a few different thing we want to be able to do to the counter, such
as setting a counter, deleting a counter, listing counters, incrementing a
counter, and getting the value of a counter. We'll need to implement the code
to do those.

One of the neat things about `dbkit` is that you don't have to worry about
passing around database connections. Instead, you create a context in which the
queries are ran, and `dbkit` itself does the work. Thus, we can do something
like this:

    value = query_value(
        'SELECT value FROM counters WHERE counter = ?',
        (counter,),
        default=0)

And we don't need to worry about the database connection we're actually dealing
with. With that in mind, here's how we'd implement getting a counter's value
with `dbkit.query_value`:

``` {.literalinclude pyobject="get_counter"}
../examples/counters.py
```

To perform updates, there's the `dbkit.execute` function. Here's how we
increment a counter's value:

``` {.literalinclude pyobject="set_counter"}
../examples/counters.py
```

dbkit also makes dealing with transactions very easy. It provides two
mechanisms: the `dbkit.transaction` context manager, as demonstrated above, and
`dbkit.transactional` decorator. Let's implement incrementing the counter using
the context manager:

``` {.literalinclude pyobject="increment_counter"}
../examples/counters.py
```

With the decorator, we'd write the function like so:

    @transactional
    def increment_counter(counter, by):
        execute(
            'UPDATE counters SET value = value + ? WHERE counter = ?',
            (by, counter))

Both are useful in different circumstances.

Deleting a counter:

``` {.literalinclude pyobject="delete_counter"}
../examples/counters.py
```

dbkit also has ways to query for result sets. Once of these is
`dbkit.query_column`, which returns an iterable of the first column in the
result set. Thus, to get a list of counters, we'd do this:

``` {.literalinclude pyobject="list_counters"}
../examples/counters.py
```

One last thing that our tool ought to be able to do is dump the contents of the
_counters_ table. To do this, we can use `dbkit.query`:

``` {.literalinclude pyobject="dump_counters"}
../examples/counters.py
```

This will return a sequence of result set rows you can iterate over like so:

``` {.literalinclude pyobject="print_counters_and_values"}
../examples/counters.py
```

By default, `query()` will use tuples for each result set row, but if you'd
prefer dictionaries, all you have to do is pass in a different row factory when
you call `dbkit.query` using the `factory` parameter:

    def dump_counter_dict():
        return query(
            'SELECT counter, value FROM counters',
            factory=dict_set)

`dbkit.dict_set` is a row factory that generates a result set where each row is
a dictionary. The default row factory is `dbkit.tuple_set`, which yields tuples
for each row in the result set. Using `dbkit.dict_set`, we'd print the counters
and values like so:

    def print_counters_and_values():
        for row in dump_counters_dict():
            print(f"{row['counter']}: {row['value']}")

Now we have enough for our counter management application, so lets start on the
main function. We'll have the following subcommands: `set`, `get`, `del`,
`list`, `incr`, `list`, and `dump`. The `dispatch()` function below deals with
calling the right function based on the command line arguments, so all we need
to create a database connection context with `dbkit.connect`. It takes the
database driver module as its first argument, and any parameters you'd pass to
that module's `connect()` function to create a new connection as its remaining
arguments:

``` {.literalinclude pyobject="main"}
../examples/counters.py
```

Finally, two utility methods, the first of which decides which of the functions
to call based on a command dispatch table and the arguments the program was ran
with:

``` {.literalinclude pyobject="dispatch"}
../examples/counters.py
```

And a second for displaying help:

``` {.literalinclude pyobject="print_help"}
../examples/counters.py
```

Bingo! You now has a simple counter manipulation tool.

``` todo
Connection pools.
```
