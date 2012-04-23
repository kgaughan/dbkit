.. _intro:

========
Overview
========

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
