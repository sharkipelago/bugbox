ALTER DATABASE bugbox CHARACTER SET = utf8mb4 COLLATE = utf8mb4_unicode_ci;
USE bugbox;

CREATE TABLE team (
	id INTEGER PRIMARY KEY,
	team_name VARCHAR(255)
)  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE user (
	id INTEGER PRIMARY KEY AUTO_INCREMENT,
	username VARCHAR(255) UNIQUE NOT NULL,
	`password` VARCHAR(255) NOT NULL,
	first_name VARCHAR(255) NOT NULL,
	last_name VARCHAR(255) NOT NULL,
	admin_level INTEGER NOT NULL CHECK (admin_level BETWEEN 0 AND 2),
	team_id INTEGER,
	pfp_filename VARCHAR(255) NOT NULL, -- which default pfp to use, if not set then it has a custom pfp in static
	FOREIGN KEY (team_id) REFERENCES team (id)
)  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE issue (
	id INTEGER PRIMARY KEY AUTO_INCREMENT,
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	progress INT NOT NULL DEFAULT 0 CHECK (progress BETWEEN 0 AND 2),  -- 0 is created, 1 is under review, 2 is closed
	author_id INTEGER NOT NULL,
	title TEXT NOT NULL,
	FOREIGN KEY (author_id) REFERENCES user (id)
)  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE comment (
	id INTEGER PRIMARY KEY AUTO_INCREMENT,
	created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
	author_id INTEGER NOT NULL,
	issue_id INTEGER NOT NULL,
	content TEXT NOT NULL,
	FOREIGN KEY (issue_id) REFERENCES issue (id),
	FOREIGN KEY (author_id) REFERENCES user (id)
)  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

CREATE TABLE assignment (
	id INTEGER PRIMARY KEY AUTO_INCREMENT,
	issue_id INTEGER NOT NULL,
	assignee_id INTEGER NOT NULL,
	CONSTRAINT issue_assignee_constraint UNIQUE (issue_id, assignee_id),
	FOREIGN KEY (issue_id) REFERENCES issue (id),
	FOREIGN KEY (assignee_id) REFERENCES user (id)
)  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;


CREATE TABLE issue_team (
	id INTEGER PRIMARY KEY AUTO_INCREMENT,
	issue_id INTEGER NOT NULL,
	team_id INTEGER NOT NULL,
	CONSTRAINT issue_team UNIQUE (issue_id, team_id),
	FOREIGN KEY (issue_id) REFERENCES issue (id),
	FOREIGN KEY (team_id) REFERENCES team (id)
)  DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;