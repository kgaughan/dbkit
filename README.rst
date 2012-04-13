=====
dbkit
=====

**dbkit** is intended to be a library to abstract away at least part of
the pain involved in dealing with `DB-API 2`_ compatible database
drivers.


Overview
========

*dbkit* is intended to be used in circumstances where it is impractical
or overkill to use an ORM such as `SQLObject`_ or `SQLAlchemy`_, but it
would be useful to at least abstract away some of the pain involved in
dealing with the database.

Aims:

-  Minimise and/or remove the need to pass around connection objects.
-  Make exception handling easier by removing hardwiring of exception
   handling code to specific drivers. Unfortunately, not all drivers
   support exceptions on the connection object, making this particular
   feature more useful than I'd like!
-  Easier to use transaction handling.
-  Easier iteration over resultsets.

Non-aims:

-  Abstraction of SQL statements. The idea is to get rid of the more
   annoying but necessary boilerplate code involved in dealing with
   DB-API 2 drivers, not to totally abstract away SQL itself.

Open questions:

-  Connection pooling: implement it, or interoperate with `DBUtils`_?
-  Query logging: this would be a useful feature. The question is, how
   should it be implemented?


Design Notes
============

*dbkit* will make heavy use of `context managers`_. The primary context
manager used is a *database context*. This wraps a database connection.
Database contexts are not created directly, but are exposed via the
module's ``connect()`` function, which will work something like this:

::

    def connect(module, *args, **kwargs):
        conn = module.connect(*args, **kwargs)
        return _DatabaseContext(module, conn)

A database context contains little or no actual information that's
useful or usable to anything outside of *dbkit* itself; it simply
maintains a reference to the driver module and the connection, provides
a ``close()`` method for use with ```contextlib.closing()```_, and the
magic methods necessary for implementing a context manager. It contains
very little intelligence.

The module maintains a per-thread stack of database contexts. When you
use a database context with the ``with`` statement, that context is
pushed onto the stack for the duration. Whichever database context is at
the head of the stack defines how the rest of the library works.

This method of doing things has several key advantages:

-  Driver-specific exceptions can be exposed in a uniform manner [1]_.
-  Modules containing any of the SQL statements you want to run against
   the database don't need to have a reference to the connection as
   they're totally decoupled from the connection.

Additionally, the module will have a context manager function called
``transaction()`` for enclosing statements to be ran in a single
transaction. It will also have functions exposing the following DB-API
cursor methods ``execute()`` and ``executemany()`` (renamed
``execute_many()``). Additionally, it will have a number of query helper
methods such as ``query_row()`` (returns the first row only),
``query_value()`` (returns the first field of the first row),
``query_column()`` (returns an iterable of the values in the first
column of the resultset). Cursors will be abstracted away behind some
form of iterable object that will expose whatever functionality is
needed.

.. [1]
   While the ideal way would be to expose these using something akin to
   `descriptors`_, descriptors only work with classes, not modules, to
   the best of my knowledge. I could very easily be wrong here, and
   rather hope I am!

.. _DB-API 2: http://www.python.org/dev/peps/pep-0249/
.. _SQLObject: http://sqlobject.org/
.. _SQLAlchemy: http://sqlalchemy.org/
.. _DBUtils: http://pypi.python.org/pypi/DBUtils/1.1
.. _context managers: http://docs.python.org/library/contextlib.html
.. _``contextlib.closing()``: http://docs.python.org/library/contextlib.html#contextlib.closing
.. _descriptors: http://docs.python.org/howto/descriptor.html
