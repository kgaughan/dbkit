#!/usr/bin/env python

"""
A simple microblog/changelog app intended to exercise dbkit's type 1
database driver support for connection pooling.

.. note::
   This doesn't currently work fully due to dbkit's type 1 driver support
   being broken and thus removed. It will work just fine with type 2
   drivers and above such as `psycopg2`.
"""

import web
import sqlite3
import dbkit
import unicodedata
import re
import creole


urls = (
    '/', 'Frontpage',
    '/([-a-z0-9]+)/', 'Project',
)

app = web.application(urls, globals())
render = web.template.render('templates', base='layout', globals={
    'creole2html': creole.creole2html
})
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


def get_projects():
    return dbkit.query("""
        SELECT    slug, project, COUNT(note_id) AS notes
        FROM      projects
        LEFT JOIN notes USING (project_id)
        GROUP BY  project_id
        ORDER BY  project
        """)


def get_project(slug):
    return dbkit.query_row("""
        SELECT  project_id, slug, project, overview
        FROM    projects
        WHERE   slug = ?
        """, (slug,))


@dbkit.transactional
def add_project(project):
    slug = slugify(project)
    dbkit.execute("""
        INSERT INTO projects (project, slug, overview) VALUES (?, ?, '')
        """, (project, slug))
    return (dbkit.last_row_id(), slug)


def get_notes(project_id):
    return dbkit.query("""
        SELECT   note_id, note, created
        FROM     notes
        WHERE    project_id = ?
        ORDER BY created DESC
        """, (project_id,))


@dbkit.transactional
def save_note(project_id, note):
    dbkit.execute("""
        INSERT INTO notes (project_id, note) VALUES (?, ?)
        """, (project_id, note))
    return dbkit.last_row_id()


class Frontpage(object):

    def GET(self):
        with pool.connect():
            projects = list(get_projects())
        return render.frontpage(projects=projects)

    def POST(self):
        form = web.input(project='')
        with pool.connect():
            _, slug = add_project(form.project)
        raise web.seeother(slug + '/')


class Project(object):

    def GET(self, slug):
        with pool.connect():
            project = get_project(slug)
            if not project:
                raise web.notfound("No such project.")
            notes = list(get_notes(project.project_id))
        return render.project(project=project, notes=notes)

    def POST(self, slug):
        form = web.input(note='')
        with pool.connect():
            project = get_project(slug)
            if not project:
                raise web.notfound("No such project.")
            note_id = save_note(project.project_id, form.note)
        raise web.seeother('#p' + str(note_id))


if __name__ == '__main__':
    try:
        app.run()
    finally:
        pool.finalise()
else:
    wsgi_app = app.wsgifunc()
