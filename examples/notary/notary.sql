CREATE TABLE projects (
	project_id INTEGER NOT NULL PRIMARY KEY,
	slug       TEXT    NOT NULL,
	project    TEXT    NOT NULL,
	overview   TEXT    NOT NULL
);

CREATE UNIQUE INDEX ux_project_slug ON projects (slug);

CREATE TABLE notes (
	note_id    INTEGER  NOT NULL PRIMARY KEY,
	project_id INTEGER  NOT NULL DEFAULT 0 REFERENCES projects (project_id),
	note       TEXT     NOT NULL,
	created    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_note_created ON notes (created);
CREATE INDEX ix_note_project ON notes (project_id);
