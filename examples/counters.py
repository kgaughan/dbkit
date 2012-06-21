"""A counter management tool."""

from contextlib import closing
from os import path
import sqlite3
import sys

from dbkit import connect, transaction, \
    execute, query, query_value, query_column


def get_counter(counter):
    """Get the value of a counter."""
    print query_value(
        'SELECT value FROM counters WHERE counter = ?',
        (counter,),
        default=0)


def set_counter(counter, value):
    """Set a counter."""
    with transaction():
        execute(
            'REPLACE INTO counters (counter, value) VALUES (?, ?)',
            (counter, value))


def increment_counter(counter, by):
    """Modify the value of a counter by a certain amount."""
    with transaction():
        execute(
            'UPDATE counters SET value = value + ? WHERE counter = ?',
            (by, counter))


def delete_counter(counter):
    """Delete a counter."""
    with transaction():
        execute(
            'DELETE FROM counters WHERE counter = ?',
            (counter,))


def list_counters():
    """List the names of all the stored counters."""
    print "\n".join(query_column('SELECT counter FROM counters'))


def dump_counters():
    """Query the database for all counters and their values."""
    return query('SELECT counter, value FROM counters')


def print_counters_and_values():
    """List all the counters and their values."""
    for counter, value in dump_counters():
        print "%s: %d" % (counter, value)


def print_help(filename, table, dest=sys.stdout):
    """Print help to the given destination file object."""
    cmds = '|'.join(sorted(table.keys()))
    print >> dest, "Syntax: %s %s [args]" % (path.basename(filename), cmds)


def dispatch(table, args):
    """Dispatches to a function based on the contents of `args`."""
    # No arguments: print help.
    if len(args) == 1:
        print_help(args[0], table)
        sys.exit(0)

    # Bad command or incorrect number of arguments: print help to stderr.
    if args[1] not in table or len(args) != len(table[args[1]]) + 1:
        print_help(args[0], table, dest=sys.stderr)
        sys.exit(1)

    # Cast all the arguments to fit their function's signature to ensure
    # they're correct and to make them safe for consumption.
    sig = table[args[1]]
    try:
        fixed_args = [type_(arg) for arg, type_ in zip(args[2:], sig[1:])]
    except TypeError:
        # If any are wrong, complain to stderr.
        print_help(args[0], table, dest=sys.stderr)
        sys.exit(1)

    # Dispatch the call to the correct function.
    sig[0](*fixed_args)


def main():
    # This table tells us the subcommands, the functions to dispatch to,
    # and their signatures.
    command_table = {
        'set': (set_counter, str, int),
        'del': (delete_counter, str),
        'get': (get_counter, str),
        'list': (list_counters,),
        'incr': (increment_counter, str, int),
        'dump': (print_counters_and_values,),
    }
    with connect(sqlite3, 'counters.sqlite') as ctx:
        with closing(ctx):
            dispatch(command_table, sys.argv)


if __name__ == '__main__':
    main()
