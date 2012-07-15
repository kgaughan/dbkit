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

        {{#has_entries}}<ul>{{/has_entries}}
        {{#entries}}
        <li>{{note}}</li>
        {{/entries}}
        </ul>
        {{#has_entries}}</ul>{{/has_entries}}

        {{^entries}}
        <p><em>No entries!</em></p>
        {{/entries}}

        <form action="" method="post">
        <div><textarea name="note"></textarea></div>
        <div><input type="submit" value="Post"></div>
        </form>
    </body>
</html>"""


def get_recent_entries():
    return dbkit.query(
        "SELECT id, note, created FROM notes ORDER BY created DESC")


@dbkit.transactional
def save_entry(note):
    dbkit.execute("INSERT INTO notes (note) VALUES (?)", (note,))


class most_recent(object):

    def GET(self):
        with pool.connect():
            recent_entries = list(get_recent_entries())
        return pystache.render(RECENT_ENTRIES, {
            'entries': recent_entries,
            'has_entries': len(recent_entries) > 0})

    def POST(self):
        with pool.connect():
            form = web.input(note='')
            save_entry(form.note)
        raise web.seeother(web.ctx.path)


if __name__ == '__main__':
    try:
        app.run()
    finally:
        pool.finalise()
