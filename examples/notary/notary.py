#!/usr/bin/env python

"""
A simple microblog/changelog app intended to exercise dbkit's type 1
database driver support for connection pooling.
"""

import web
import sqlite3
import dbkit


urls = (
    '/', 'frontpage',
    '/([-a-z0-9]+)/', 'project',
)

app = web.application(urls, globals())
render = web.template.render('templates')
pool = dbkit.create_pool(sqlite3, 10, "notary.db")
pool.default_factory = dbkit.dict_set


def get_last_row_id():
    return dbkit.query_value("SELECT LAST_INSERT_ROWID()")


def get_projects():
    return dbkit.query("""
        SELECT    project_id, project, COUNT(note_id) AS notes
        FROM      projects
        LEFT JOIN notes USING (project_id)
        GROUP BY  project_id
        ORDER BY  project
        """)


@dbkit.transactional
def add_project(project):
    dbkit.execute("""
        INSERT INTO projects (project) VALUES (?)
        """, (project,))
    return get_last_row_id()


def get_recent_entries():
    return dbkit.query("""
        SELECT note_id, note, created FROM notes ORDER BY created DESC
        """)


@dbkit.transactional
def save_entry(note):
    dbkit.execute("""
        INSERT INTO notes (note) VALUES (?)
        """, (note,))
    return get_last_row_id()


class frontpage(object):

    def GET(self):
        with pool.connect():
            projects = get_projects()
        return render.layout(render.frontpage(projects=list(projects)))

    def POST(self):
        form = web.input(project='')
        with pool.connect():
            add_project(form.project)
        raise web.seeother(web.ctx.path)


if __name__ == '__main__':
    try:
        app.run()
    finally:
        pool.finalise()