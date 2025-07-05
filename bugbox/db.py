import sqlite3
from datetime import datetime
from werkzeug.security import generate_password_hash

import click
from flask import current_app, g

teams = {
    "Unassigned": -1,
    "Frontend": 0,
    "Backend": 1,
    "Mobile": 2,
    "QA": 3,
    "DevOps": 4
}

DEFAULT_USERS = [
    # Admin
    ("md", generate_password_hash("mooodeng"), "Moo", "Deng", 2, None), 
    # Team Lead
    ("puxp", generate_password_hash("punxsutawney"), "Punxsutawney", "Phil", 1, teams["Mobile"]),
    # User
    ("hachi", generate_password_hash("hachikoko"), "Chūken", "Hachikō", 0, teams["Backend"]),
    ("harambe", generate_password_hash("rememberharambe"), "Harambe", "Van Coppenolle", 0, teams["Mobile"]),
    ("laika", generate_password_hash("laikaspaceneighbor"), "Laika", " Kudryavka", 0, teams["QA"])
]

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(
            current_app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES
        )
        g.db.row_factory = sqlite3.Row

    return g.db


def close_db(e=None):
    db = g.pop('db', None)

    if db is not None:
        db.close()

def init_db():
    db = get_db()

    with current_app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))

    db.executemany(
        "INSERT INTO team (id, team_name) VALUES (?, ?)",
        [(id, name) for (name, id) in teams.items()],
    )
    db.commit()

    db.executemany(
        "INSERT INTO user (username, [password], first_name, last_name, admin_level, team_id) VALUES (?, ?, ?, ?, ?, ?)",
        DEFAULT_USERS,
    )
    db.commit()


@click.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


sqlite3.register_converter(
    "timestamp", lambda v: datetime.fromisoformat(v.decode())
)

def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)