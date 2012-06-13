.. _intro:

========
Overview
========

.. note::
   Like dbkit itself, this documentation is a work in progress. Unlike
   dbkit, it is nowhere near complete yet. Bear with me.


Introduction
============

*dbkit* is intended to be used in circumstances where it is impractical
or overkill to use an ORM such as `SQLObject`_ or `SQLAlchemy`_, but it
would be useful to at least abstract away some of the pain involved in
dealing with the database.

Features:

- Rather than passing around database connections, statements are executed
  within a database `context`_, thus helping to decouple modules that
  interface with the database from the database itself and its connection
  details.
- Database contexts contain references to the exceptions exposed by the
  database driver, thus decoupling exception handling from the database
  driver.
- Easier to use transaction handling.
- Easier iteration over resultsets.
- Connection pooling. In addition, any code using pooled connections has
  no need to know connection pooling is in place.
- Query logging.

Non-aims:

-  Abstraction of SQL statements. The idea is to get rid of the more
   annoying but necessary boilerplate code involved in dealing with
   `DB-API 2`_ drivers, not to totally abstract away SQL itself.

.. Links
.. _DB-API 2: http://www.python.org/dev/peps/pep-0249/
.. _SQLObject: http://sqlobject.org/
.. _SQLAlchemy: http://sqlalchemy.org/
.. _context: http://docs.python.org/library/contextlib.html


Comparison with straight DB-API 2 code
======================================

Need a "Hello, World!" example? Here's how you'd set up a connection context,
query a database table, and print out its contents with `dbkit`::

    from dbkit import connect, query
    from contextlib import closing
    import sqlite3

    with connect(sqlite3, 'counters.db') as ctx, closing(ctx):
        for counter, value in query('SELECT counter, value FROM counters'):
            print "%s: %d" % (counter, value)

And here's how you'd so it with a DB-API 2 (using *just* :pep:`249`, no
driver-specific extensions)::

    import sqlite3
    from contextlib import closing

    with closing(sqlite3.connect('counters.db')) as conn:
        with closing(conn.cursor()) as cur:
            cur.execute('SELECT counter, value FROM counters')
            while True:
                row = cur.fetchone()
                if row is None:
                    break
                print "%s: %d" % row


Download
========

The latest *development* version can be found in the `dbkit` Git repository::

    git clone https://github.com/kgaughan/dbkit

The project has yet to be submitted to PyPI, but I'm hoping to do that as soon
as I'm happy with the documentation. To build a source package for installation
and subsequently install it, do::

   python setup.py sdist
   pip install dist/dbkit-0.1.0.tar.gz

Alternatively, you can install it directly, bypassing package creation::

   python setup.py install


Requirements
============

`dbkit` will work with Python 2.5, 2.6, and 2.7 without issue. It appears to
have some minor issues with PyPy, but it ought to work fine. It's not yet
compatible with Python 3.

`dbkit` has no dependencies other than requiring a database driver.
