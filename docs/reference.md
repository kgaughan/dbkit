# Reference

::: dbkit.connect

::: dbkit.context

## Contexts

Contexts wrap a notional database connection. They're returned by the
`dbkit.connect` function. Methods are for the internal use of dbkit only though
it does expose a method for closing the database connection when you're done
with it and contains references for each of the exceptions exposed by the
connection's database driver. For a list of these exceptions, see
[PEP-0249](http://www.python.org/dev/peps/pep-0249/).

::: dbkit.Context

## Exceptions

::: dbkit.NoContextError

::: dbkit.NotSupportedError

::: dbkit.AbortTransactionError

## Transactions

::: dbkit.transaction

::: dbkit.transactional

## Statement execution

These functions allow you to execute SQL statements within the current
database context.

::: dbkit.execute

::: dbkit.query

::: dbkit.query_row

::: dbkit.query_value

::: dbkit.query_column

## Stored procedures

These functions allow you to execute stored procedures within the current
database context, if the DBMS supports stored procedures.

::: dbkit.execute_proc

::: dbkit.query_proc

::: dbkit.query_proc_row

::: dbkit.query_proc_value

::: dbkit.query_proc_column

## Result generators

Result generators are generator functions that are used internally by dbkit to
take the results from a database cursor and turn them into a form that's easier
to deal with programmatically, such a sequence of tuples or a sequence of
dictionaries, where each tuple or dictionary represents a row of the result
set. By default, `dbkit.TupleFactory` is used as the result generator, but you
can change this by assigning another, such as `dbkit.DictFactory` to
`dbkit.Context.default_factory` function.

Some query functions allow you to specify the result generator to be used for
the result, which is passed in using the `factory` parameter.

::: dbkit.DictFactory

::: dbkit.TupleFactory

## Utilities

::: dbkit.to_dict

::: dbkit.make_placeholders

## Connection pools

!!! note
    Connection pool support is currently considered pre-alpha.

Connection pooling is a way to share a common set of database connections over
a set of contexts, each of which can be executing in different threads.
Connection pooling can increase efficiency as it mitigates much of the cost
involved in connecting and disconnecting from databases. It also can help lower
the number of database connections an application needs to keep open with a
database server concurrently, thus helping to lower server low.

As with contexts, pools have a copy of the driver module's exceptions. For a
list of these exceptions, see
[PEP-0249](http://www.python.org/dev/peps/pep-0249/).

The `acquire` and `release` methods are for internal use only.

::: dbkit.PoolBase

::: dbkit.Pool

## Connection mediators

Connection mediators are used internally within contexts to mediate connection
acquisition and release between a context and a (notional) connection pool.
They're an advanced feature that you as a developer will only need to
understand and use if writing your own connection pool. All connection mediator
instances are context managers.

!!! note
    You might find the naming a bit odd. After all, wouldn't calling something
    like this a 'manager' be just as appropriate and less... odd? Not really.
    Calling something a 'manager' presupposes a degree of control over the
    resource in question. A 'mediator', on the other hand, simply acts as a
    middle man which both parties know. Introducing the mediator means that
    contexts don't need to know where their connections come from and pools
    don't need to care how they're used. The mediator takes care of all that.

::: dbkit.ConnectionMediatorBase

::: dbkit.SingleConnectionMediator

::: dbkit.PooledConnectionMediator
