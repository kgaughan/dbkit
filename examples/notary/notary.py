#!/usr/bin/env python

"""
A simple microblog/changelog app intended to exercise dbkit's type 1
database driver support for connection pooling.
"""

import web
import sqlite3
import dbkit


urls = (
    '/', 'most_recent'
)

app = web.application(urls, globals())
render = web.template.render('templates')
pool = dbkit.create_pool(sqlite3, 10, "notary.db")
pool.default_factory = dbkit.dict_set


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
        return render.layout(
            render.recent_entries(entries=list(recent_entries)))

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
