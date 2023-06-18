"""
A counter management tool.
"""

from contextlib import closing
from os import path
import sqlite3
import sys

from dbkit import connect, execute, query, query_column, query_value, transactional


# --8<-- [start:get_counter]
def get_counter(counter):
    """
    Get the value of a counter.
    """
    print(
        query_value(
            "SELECT value FROM counters WHERE counter = ?",
            (counter,),
            default=0,
        )
    )


# --8<-- [end:get_counter]


@transactional
def set_counter(counter, value):
    """
    Set a counter.
    """
    execute("REPLACE INTO counters (counter, value) VALUES (?, ?)", (counter, value))


@transactional
def increment_counter(counter, by):
    """
    Modify the value of a counter by a certain amount.
    """
    execute("UPDATE counters SET value = value + ? WHERE counter = ?", (by, counter))


# --8<-- [start:delete_counter]
@transactional
def delete_counter(counter):
    """
    Delete a counter.
    """
    execute("DELETE FROM counters WHERE counter = ?", (counter,))


# --8<-- [end:delete_counter]


# --8<-- [start:list_counters]
def list_counters():
    """
    List the names of all the stored counters.
    """
    print("\n".join(query_column("SELECT counter FROM counters")))


# --8<-- [end:list_counters]


# --8<-- [start:dump_counters]
def dump_counters():
    """
    Query the database for all counters and their values.
    """
    return query("SELECT counter, value FROM counters")


# --8<-- [end:dump_counters]


# --8<-- [start:print_counters_and_values]
def print_counters_and_values():
    """
    List all the counters and their values.
    """
    for counter, value in dump_counters():
        print(f"{counter}: {value}")


# --8<-- [end:print_counters_and_values]


# --8<-- [start:print_help]
def print_help(filename, table, dest=sys.stdout):
    """
    Print help to the given destination file object.
    """
    cmds = "|".join(sorted(table.keys()))
    print(f"Syntax: {path.basename(filename)} {cmds} [args]", file=dest)


# --8<-- [end:print_help]


# --8<-- [start:dispatch]
def dispatch(table, args):
    """
    Dispatches to a function based on the contents of `args`.
    """
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


# --8<-- [end:dispatch]


# --8<-- [start:main]
def main():
    # This table tells us the subcommands, the functions to dispatch to,
    # and their signatures.
    command_table = {
        "set": (set_counter, str, int),
        "del": (delete_counter, str),
        "get": (get_counter, str),
        "list": (list_counters,),
        "incr": (increment_counter, str, int),
        "dump": (print_counters_and_values,),
    }
    with connect(sqlite3, "counters.sqlite") as ctx:
        with closing(ctx):
            dispatch(command_table, sys.argv)


# --8<-- [end:main]


if __name__ == "__main__":
    main()
