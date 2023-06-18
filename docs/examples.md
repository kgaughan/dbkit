# Examples

## counters.py {#counters-py-example}

A command line tool for manipulating and querying bunch of counters stored in
an SQLite database. This demonstrates basic use of dbkit.

```py
--8<--
examples/counters.py
--8<--
```

## pools.py {#pools-py-example}

A small web application, built using [Bottle](bottlepy.org/) and
[psycopg2](http://initd.org/psycopg/), to say that prints "Hello, *name*"
based on the URL fetched, and which records how many times it's said hello to
a particular name.

This demonstrates use of connection pools.

```py
--8<--
examples/pools.py
--8<--
```
