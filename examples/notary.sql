CREATE TABLE notes (
	id      INTEGER  NOT NULL PRIMARY KEY,
	note    TEXT     NOT NULL,
	created DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ix_note_created ON notes (created);
