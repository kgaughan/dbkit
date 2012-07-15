#!/usr/bin/env python

"""
A simple microblog/changelog app intended to exercise dbkit's type 1
database driver support for connection pooling.
"""

import web
import sqlite3
import pystache
import dbkit


urls = (
    '/', 'most_recent'
)

app = web.application(urls, globals())
pool = dbkit.create_pool(sqlite3, 10, "notary.db")
pool.default_factory = dbkit.dict_set


RECENT_ENTRIES = """<!DOCTYPE html>
<html>
    <head>
        <title>Recent entries</title>
    </head>
    <body>
        <h1>Recent entries</h1>
        <ul>
        {{#entries}}
        <li>{{note}}</li>
        {{/entries}}
        </ul>
    </body>
</html>"""


def get_recent_entries():
    return dbkit.query(
        "SELECT id, note, created FROM notes ORDER BY created DESC")


class most_recent(object):
    def GET(self):
        with pool.connect():
            recent_entries = get_recent_entries()
        return pystache.render(RECENT_ENTRIES, {'entries': recent_entries})


if __name__ == '__main__':
    try:
        app.run()
    finally:
        pool.finalise()
