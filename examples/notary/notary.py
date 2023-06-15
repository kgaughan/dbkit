#!/usr/bin/env python3

"""
A simple microblog/changelog app intended to exercise dbkit's type 1
database driver support for connection pooling.

.. note::
   This doesn't currently work fully due to dbkit's type 1 driver support
   being broken and thus removed. It will work just fine with type 2
   drivers and above such as `psycopg2`.
"""

import os.path
import re
import sqlite3
import unicodedata

from bottle import abort, Bottle, redirect, request, run, static_file, view

import dbkit

app = Bottle()
pool = dbkit.create_pool(sqlite3, 10, "notary.db")
pool.default_factory = dbkit.dict_set


def strip_accents(s):
    """
    Strip accents to prepare for slugification.
    """
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(ch for ch in nfkd if not unicodedata.combining(ch))


def slugify(s):
    """
    Converts the given string to a URL slug.
    """
    s = strip_accents(s.replace("'", "").lower())
    return re.sub("[^a-z0-9]+", " ", s).strip().replace(" ", "-")


def get_projects():
    return dbkit.query(
        """
        SELECT    slug, project, COUNT(note_id) AS notes
        FROM      projects
        LEFT JOIN notes USING (project_id)
        GROUP BY  project_id
        ORDER BY  project
        """
    )


def get_project(slug):
    return dbkit.query_row(
        """
        SELECT  project_id, slug, project, overview
        FROM    projects
        WHERE   slug = ?
        """,
        (slug,),
    )


@dbkit.transactional
def add_project(project):
    slug = slugify(project)
    dbkit.execute(
        """
        INSERT INTO projects (project, slug, overview) VALUES (?, ?, '')
        """,
        (project, slug),
    )
    return (dbkit.last_row_id(), slug)


def get_notes(project_id):
    return dbkit.query(
        """
        SELECT   note_id, note, created
        FROM     notes
        WHERE    project_id = ?
        ORDER BY created DESC
        """,
        (project_id,),
    )


@app.get("/static/<filepath:path>")
def server_static(filepath):
    return static_file(
        filepath,
        root=os.path.join(os.path.dirname(__file__), "static"),
    )


@dbkit.transactional
def save_note(project_id, note):
    dbkit.execute(
        """
        INSERT INTO notes (project_id, note) VALUES (?, ?)
        """,
        (project_id, note),
    )
    return dbkit.last_row_id()


@app.get("/")
@view("frontpage")
def show_index():
    with pool.connect():
        return dict(projects=list(get_projects()))


@app.post("/")
def post_index():
    project = request.forms.get("project")
    with pool.connect():
        _, slug = add_project(project)
    redirect(f"{slug}/")


@app.get("/<slug>/")
@view("project")
def show_project(slug):
    with pool.connect():
        project = get_project(slug)
        if not project:
            abort(404, "No such project.")
        return dict(
            project=project,
            notes=list(get_notes(project.project_id)),
        )


@app.post("/<slug>/")
def post_note(slug):
    note = request.forms.get("note")
    with pool.connect():
        if project := get_project(slug):
            note_id = save_note(project.project_id, note)
        else:
            abort(404, "No such project.")
    redirect(f"#p{note_id}")


if __name__ == "__main__":
    try:
        run(app, host="localhost", port=8080)
    finally:
        pool.finalise()
