.. _philosophy:

=================
Design philosophy
=================

The design philosophy of dbkit can be summed up as "decoupling through
statefulness".

Many things about database interaction are already stateful,
transactions for instance. While statelessness can, in many areas, help
with scalability, it has a negative effect on ease of use: stateless code
must always have the context it requires to do its work passed to it.

Implemented poorly, this means that stateless code can end up with
assumptions about the kind of contextual information it needs to have to
do its job and where it's much easier to do the wrong thing than to do
the right thing.

dbkit aims to solve this, at least for relational database access, by
providing an interface that makes the easy solution the right case while
still making the difficult stuff possible[1]_.

It does this by decoupling the execution of SQL statements from the
connection they're executed against. This might seem like a small thing,
but it has significant consequences: it means that database code need
have little if any awareness of the environment it executes in, and what
context it does need to have can easily be introspected when needed.

.. [1] Not that this side of things has been completely solved, but a
       significant section of the problem definitely has.
