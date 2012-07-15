CREATE TABLE projects (
	project_id INTEGER NOT NULL PRIMARY KEY,
	project    TEXT    NOT NULL
);

CREATE TABLE notes (
	note_id    INTEGER  NOT NULL PRIMARY KEY,
	project_id INTEGER  NOT NULL DEFAULT 0 REFERENCES projects (project_id),
	note       TEXT     NOT NULL,
	created    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_note_created ON notes (created);
CREATE INDEX ix_note_project ON notes (project_id);
