.. _reference:

=========
Reference
=========

.. autofunction:: dbkit.connect

.. autofunction:: dbkit.context


Contexts
========

Contexts wrap a notional database connection. They're returned by the
:py:func:`dbkit.connect` function. Methods are for the internal use of dbkit
only though it does expose a method for closing the database connection when
you're done with it and contains references for each of the exceptions exposed
by the connection's database driver. For a list of these exceptions, see
`PEP-0249`_.

.. autoclass:: dbkit.Context
   :members: close

   .. attribute:: default_factory

      The row factory used for generating rows from :py:func:`dbkit.query` and
      :py:func:`dbkit.query_row`. The default is :py:func:`dbkit.tuple_set`.

      The factory function should take a cursor an return an iterable over the
      current resultset.

   .. attribute:: logger

      The function used for logging statements and their arguments.

      The logging function should take two arguments: the query and a
      sequence of query arguments.

      There are two supplied logging functions: :py:func:`dbkit.null_logger`,
      the default, logs nothing, while :py:func:`dbkit.stderr_logger` logs its
      arguments to stderr.


Exceptions
==========

.. autoclass:: dbkit.NoContext

.. autoclass:: dbkit.NotSupported

.. autoclass:: dbkit.AbortTransaction


Transactions
============

.. autofunction:: dbkit.transaction

.. autofunction:: dbkit.transactional


Statement execution
===================

These functions allow you to execute SQL statements within the current
database context.

.. autofunction:: dbkit.execute

.. autofunction:: dbkit.query

.. autofunction:: dbkit.query_row

.. autofunction:: dbkit.query_value

.. autofunction:: dbkit.query_column


Stored procedures
=================

These functions allow you to execute stored procedures within the current
database context, if the DBMS supports stored procedures.

.. autofunction:: dbkit.execute_proc

.. autofunction:: dbkit.query_proc

.. autofunction:: dbkit.query_proc_row

.. autofunction:: dbkit.query_proc_value

.. autofunction:: dbkit.query_proc_column


Result generators
=================

Result generators are generator functions that are used internally by dbkit to
take the results from a database cursor and turn them into a form that's easier
to deal with programmatically, such a sequence of tuples or a sequence of
dictionaries, where each tuple or dictionary represents a row of the result set.
By default, :py:func:`dbkit.tuple_set` is used as the result generator, but you
can change this by assigning another, such as :py:func:`dbkit.dict_set` to
:py:attr:`dbkit.Context.default_factory` function.

Some query functions allow you to specify the result generator to be used
for the result, which is passed in using the `factory` parameter.

.. autofunction:: dbkit.column_set

.. autofunction:: dbkit.dict_set

.. autofunction:: dbkit.tuple_set


Loggers
=======

Loggers are functions that you can assign to :py:attr:`dbkit.Context.logger` to
have dbkit log any SQL statements ran or stored procedures called to some sink.
dbkit comes with a number of simple loggers listed below. To create your own
logger, simply create a function that takes two arguments, the first of which
is the SQL statement or stored procedure name, and the second is a sequence of
arguments that were passed with it.

.. autofunction:: dbkit.null_logger

.. autofunction:: dbkit.make_file_object_logger

.. function:: dbkit.stderr_logger(stmt, args)

   A logger that logs to standard error.


Utilities
=========

.. autofunction:: dbkit.unindent_statement


Connection pools
================

.. note:: Connection pool support is currently considered pre-alpha.

Connection pooling is a way to share a common set of database connections
over a set of contexts, each of which can be executing in different
threads. Connection pooling can increase efficiency as it mitigates
much of the cost involved in connecting and disconnecting from databases.
It also can help lower the number of database connections an application
needs to keep open with a database server concurrently, thus helping to
lower server low.

As with contexts, pools have a copy of the driver module's exceptions.
For a list of these exceptions, see `PEP-0249`_.

The `acquire` and `release` methods are for internal use only.

.. autoclass:: dbkit.PoolBase
   :members: acquire, release, finalise, connect
   :undoc-members: Warning, Error, InterfaceError, DatabaseError, DataError, OperationalError, IntegrityError, InternalError, ProgrammingError, NotSupportedError

.. autoclass:: dbkit.Pool
   :members: finalise, connect
   :undoc-members: Warning, Error, InterfaceError, DatabaseError, DataError, OperationalError, IntegrityError, InternalError, ProgrammingError, NotSupportedError


Connection mediators
====================

Connection mediators are used internally within contexts to mediate
connection acquisition and release between a context and a (notional)
connection pool. They're an advanced feature that you as a developer will
only need to understand and use if writing your own connection pool. All
connection mediator instances are context managers.

.. note:: You might find the naming a bit odd. After all, wouldn't calling
   something like this a 'manager' be just as appropriate and less...
   odd? Not really. Calling something a 'manager' presupposes a degree of
   control over the resource in question. A 'mediator', on the other hand,
   simply acts as a middle man which both parties know. Introducing the
   mediator means that contexts don't need to know where their connections
   come from and pools don't need to care how they're used. The mediator
   takes care of all that.

.. autoclass:: dbkit.ConnectionMediatorBase
   :members:

.. autoclass:: dbkit.SingleConnectionMediator
   :undoc-members: close

.. autoclass:: dbkit.PooledConnectionMediator
   :undoc-members: close

.. Links
.. _PEP-0249: http://www.python.org/dev/peps/pep-0249/
