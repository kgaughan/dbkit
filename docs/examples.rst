.. _examples:

========
Examples
========

.. _counters-py-example:

counters.py
===========

A command line tool for manipulating and querying bunch of counters stored in
an SQLite database. This demonstrates basic use of `dbkit`.

.. literalinclude:: ../examples/counters.py
   :linenos:


.. _pools-py-example:

pools.py
========

A small web application, built using web.py_, pystache_, and psycopg2_, to say
that prints "Hello, *name*" based on the URL fetched, and which records how
many times it's said hello to a particular name.

This demonstrates use of connection pools.

.. literalinclude:: ../examples/pools.py
   :linenos:

.. _web.py: http://webpy.org/
.. _pystache: https://github.com/defunkt/pystache
.. _psycopg2: http://initd.org/psycopg/
