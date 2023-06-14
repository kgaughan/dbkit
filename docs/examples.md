# Examples

## counters.py {#counters-py-example}

A command line tool for manipulating and querying bunch of counters stored in
an SQLite database. This demonstrates basic use of dbkit.

```{.literalinclude linenos=""}
../examples/counters.py
```

## pools.py {#pools-py-example}

A small web application, built using [web.py](http://webpy.org/),
[pystache](https://github.com/defunkt/pystache), and
[psycopg2](http://initd.org/psycopg/), to say that prints "Hello, *name*"
based on the URL fetched, and which records how many times it's said hello to
a particular name.

This demonstrates use of connection pools.

```{.literalinclude linenos=""}
../examples/pools.py
```
