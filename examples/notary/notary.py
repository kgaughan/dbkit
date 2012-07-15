#!/usr/bin/env python

"""
A simple microblog/changelog app intended to exercise dbkit's type 1
database driver support for connection pooling.
"""

import web
import sqlite3
import dbkit
import unicodedata
import re


urls = (
    '/', 'Frontpage',
    '/([-a-z0-9]+)/', 'Project',
)

app = web.application(urls, globals())
render = web.template.render('templates')
pool = dbkit.create_pool(sqlite3, 10, "notary.db")
pool.default_factory = dbkit.dict_set


def strip_accents(s):
    """Strip accents to prepare for slugification."""
    nfkd = unicodedata.normalize('NFKD', unicode(s))
    return u''.join(ch for ch in nfkd if not unicodedata.combining(ch))


def slugify(s):
    """Converts the given string to a URL slug."""
    s = strip_accents(s.replace("'", '').lower())
    return re.sub('[^a-z0-9]+', ' ', s).strip().replace(' ', '-')


def get_last_row_id():
    """Returns the row ID of the last insert statement."""
    return dbkit.query_value("SELECT LAST_INSERT_ROWID()")


def get_projects():
    return dbkit.query("""
        SELECT    slug, project, COUNT(note_id) AS notes
        FROM      projects
        LEFT JOIN notes USING (project_id)
        GROUP BY  project_id
        ORDER BY  project
        """)


@dbkit.transactional
def add_project(project):
    slug = slugify(project)
    dbkit.execute("""
        INSERT INTO projects (project, slug) VALUES (?, ?)
        """, (project, slug))
    return (get_last_row_id(), slug)


def get_notes(project_id):
    return dbkit.query("""
        SELECT   note_id, note, created
        FROM     notes
        WHERE    project_id = ?
        ORDER BY created DESC
        """, (project_id,))


@dbkit.transactional
def save_entry(note):
    dbkit.execute("""
        INSERT INTO notes (note) VALUES (?)
        """, (note,))
    return get_last_row_id()


class Frontpage(object):

    def GET(self):
        with pool.connect():
            projects = get_projects()
        return render.layout(
            render.frontpage(projects=list(projects)),
            "Projects")

    def POST(self):
        form = web.input(project='')
        with pool.connect():
            _, slug = add_project(form.project)
        raise web.seeother(slug + '/')


if __name__ == '__main__':
    try:
        app.run()
    finally:
        pool.finalise()
