# Change history

## 0.2.5 (2016-04-15) {#version-0.2.5}

-   Minor fixes and cleanup, including getting rid of a nose dependency.
-   Wheel support.

## 0.2.4 (2015-11-30) {#version-0.2.4}

-   Python 3 support.

## 0.2.3 (2015-11-26) {#version-0.2.3}

-   `Context.cursor()` now always creates a transaction. The
    lack of this outer transaction meant that PostgreSQL would end up with a
    large number of idle transactions that had neither been committed or rolled
    back.
-   This is the last version that will work on Python 2.5.

## 0.2.2 (2013-04-04) {#version-0.2.2}

-   Scrap `unindent_statement()`.
-   Derive all dbkit exceptions from `Exception`.
-   Clean up connection pinging code.
-   Add `make_placeholders()` for generating statement placeholders safely.
-   Add `to_dict()` for converting resultsets to dicts mapped off of a
    particular field.

## 0.2.0 (2012-10-16) {#version-0.2.0}

-   Add `last_row_id()`.
-   Pools now can have custom mediators.
-   Cursors are now tracked.
-   Pooled connections are no longer closed prematurely.
-   Row factories are now usable outside of context safely.

## 0.1.4 (2012-10-11) {#version-0.1.4}

-   `execute*()` now returns the number of affected rows.
-   Add `last_row_count` and `last_row_id` to `Context`.
-   Remove `DummyPool` and `ThreadAffinePool`, though the latter may be
    returning.
-   Stablise the behaviour of `Pool` when dealing with expired connections.
-   Documentation version is now pegged directly to the library.

## 0.1.2 (2012-09-02) {#version-0.1.2}

-   Initial revision with a changelog.
