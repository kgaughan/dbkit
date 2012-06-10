from contextlib import closing
import sqlite
import sys

import aaargh

from dbkit import (
    connect, execute, query, query_value, query_column,
    transaction, transactional, tuple_set, dict_set)

app = aaargh.App(description='A counter management tool.')

@app.cmd(name='set')
@app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
@app.cmd_arg('value', type=int, nargs=1, help='Value name')
def set_counter(counter, value):
    """Set a counter."""
    execute(
        'REPLACE INTO counters (counter, value) VALUES (?, ?)',
        (counter, value))

@app.cmd(name='del')
@app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
def delete_counter(counter):
    """Delete a counter."""
    execute(
        'DELETE FROM counters WHERE counter = ?',
        (counter,))

@app.cmd(name='get')
@app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
def get_counter(counter):
    """Get the value of a counter."""
    print query_value(
        'SELECT value FROM counters WHERE counter = ?',
        (counter,),
        default=0)

@app.cmd(name='list')
def list_counters():
    """List the names of all the stored counters."""
    print "\n".join(query_column('SELECT counter FROM counters'))

@app.cmd(name='incr')
@app.cmd_arg('counter', type=str, nargs=1, help='Counter name')
@app.cmd_arg('by', type=int, nargs=1, help='Amount to change by')
@transactional
def increment_counter(counter, by):
    """Modify the value of a counter by a certain amount."""
    update_counter(counter, get_counter(counter) + by)

@app.cmd(name='dump')
def print_counters_and_values():
    """List all the counters and their values."""
    for counter, value in dump_counters():
        print "%s: %d" % (counter, value)

if __name__ == '__main__':
    with context(sqlite, 'counters.sqlite') as ctx, closing(ctx):
        app.run()
