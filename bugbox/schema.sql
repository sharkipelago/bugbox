DROP TABLE IF EXISTS user;
DROP TABLE IF EXISTS issue;
DROP TABLE IF EXISTS comment;
DROP TABLE IF EXISTS assignment;
DROP TABLE IF EXISTS team;
DROP TABLE IF EXISTS issue_team;

CREATE TABLE user (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	username TEXT UNIQUE NOT NULL,
	[password] TEXT NOT NULL,
	first_name TEXT NOT NULL,
	last_name TEXT NOT NULL,
	admin_level INTEGER NOT NULL CHECK (admin_level BETWEEN 0 AND 2),
	team_id INTEGER,
	FOREIGN KEY (team_id) REFERENCES team (id)
);

CREATE TABLE issue (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	progress INT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 2),  -- 0 is created, 1 is under review, 2 is closed
	author_id INTEGER NOT NULL,
	title TEXT NOT NULL,
	FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE comment (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	author_id INTEGER NOT NULL,
	issue_id INTEGER,
	content TEXT NOT NULL,
	FOREIGN KEY (issue_id) REFERENCES issue (id),
	FOREIGN KEY (author_id) REFERENCES user (id)
);

CREATE TABLE assignment (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	issue_id INTEGER NOT NULL,
	assignee_id INTEGER NOT NULL,
	CONSTRAINT issue_assignee_constraint UNIQUE (issue_id, assignee_id),
	FOREIGN KEY (issue_id) REFERENCES issue (id),
	FOREIGN KEY (assignee_id) REFERENCES user (id)
);

CREATE TABLE team (
	id INTEGER PRIMARY KEY,
	team_name TEXT
);

CREATE TABLE issue_team (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	issue_id INTEGER NOT NULL NULL CHECK (0 < issue_id),
	team_id INTEGER,
	CONSTRAINT issue_team UNIQUE (issue_id, team_id),
	FOREIGN KEY (issue_id) REFERENCES issue (id),
	FOREIGN KEY (team_id) REFERENCES user (id)
);