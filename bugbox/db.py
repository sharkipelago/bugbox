import sqlite3
from datetime import datetime
from collections import defaultdict
import functools

from werkzeug.security import generate_password_hash

import click
from flask import current_app, g

from bugbox.team import TEAMS

TEAM_IDS = {team_name: team_id for team_id, team_name in enumerate(TEAMS)}

DEFAULT_USERS = [
    # Admin
    ("md", "mooodeng", "Moo", "Deng", 2), 
    # Team Lead
    ("puxp", "punxsutawney", "Punxsutawney", "Phil", 1, TEAM_IDS["Mobile"]),
    # User
    ("hachi","hachikoko", "Chūken", "Hachikō", 0, TEAM_IDS["Backend"]),
    ("harambe","rememberharambe", "Harambe", "Van Coppenolle", 0, TEAM_IDS["Mobile"]),
    ("laika","laikaspaceneighbor", "Laika", " Kudryavka", 0, TEAM_IDS["QA"])
]

DEFAULT_ISSUES = [
    (2, "Probably more winter", "I think I saw the shadow? But I also just woke up it could've been a hibernation dust build-up", [2, 4]),
    (2, "Pennsylvanian top hats", "Where can I accquire one?"),
    (3, "飼い主はまだ帰っていないの？", "彼がお菓子を持ってきてくれるといいな"),
    (4, "Zoo transfer request", "This place is too hot"),
    (5, "Вкусы мороженого «Астронавт»", "будут ли другие вкусы, кроме шоколада?")
]


def dml_operation(db_func):
    @functools.wraps(db_func)
    def wrapper(*args, **kwargs):
        db = get_db()
        cursor = db.cursor()
        db_func(*args, cursor=cursor, **kwargs)
        cursor.close()
        db.commit()
        return None
    return wrapper


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
        [(id, name) for (name, id) in TEAM_IDS.items()],
    )
    db.commit()

    for u in DEFAULT_USERS:
        create_user(*u)

    for i in DEFAULT_ISSUES:
        create_issue(*i)

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

def create_user(username, password, first_name, last_name, admin_level, team=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO user (username, [password], first_name, last_name, admin_level, team_id)' 
        ' VALUES (?, ?, ?, ?, ?, ?)',
        (username, generate_password_hash(password), first_name, last_name, admin_level, TEAM_IDS["Admin"] if admin_level == 2 else team)
    )
    cursor.close()
    db.commit()

def create_issue(author_id, title, body, assignee_ids = []):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO issue (author_id, title, body)'
        ' VALUES (?, ?, ?)',
        (author_id, title, body)
    )
    issue_id = cursor.lastrowid
    cursor.execute(
        'INSERT INTO issue_team (issue_id, team_id)'
        ' VALUES (?, ?)',
        (issue_id, get_user(author_id)['team_id'])
    )
    for a in assignee_ids:
        insert_assignment(cursor, issue_id, a)
    cursor.close()
    db.commit()   

def get_user(user_id):
    return get_db().execute(
        'SELECT *'
        ' FROM user u'
        ' WHERE u.id = ?',
        (user_id,)
    ).fetchone()  

def get_users():
    return get_db().execute(
        'SELECT *'
        ' FROM user u LEFT JOIN team t ON u.team_id = t.id'
    ).fetchall()


# Only executes not resposible for committing or anything
def insert_assignment(cursor, issue_id, assignee_id):
    # print(get_user(assignee_id)['team_id'], get_issue_teams()[issue_id])
    assert get_user(assignee_id)['team_id'] in get_issue_teams()[issue_id] 
    cursor.execute(
        'INSERT INTO assignment (issue_id, assignee_id)'
        ' VALUES (?, ?)',
        (issue_id, assignee_id)
    )


def get_team_names():
    team_query = get_db().execute(
        'SELECT *'
        ' FROM team t'
    ).fetchall()
    team_names = {}
    for t in team_query:
        team_names[t['id']] = t['team_name']
    return team_names

def get_issue_teams(issue_id = None):
    issue_teams_query = get_db().execute(
        'SELECT *' 
        ' FROM issue_team i_t'
    ).fetchall()
    
    issue_teams = defaultdict(set)
    for i_t in issue_teams_query:
        issue_teams[i_t['issue_id']].add(i_t['team_id'])
   
    if issue_id:
        return issue_teams[issue_id]
    return issue_teams

def get_assignees(issue_id):
    assignee_query = get_db().execute(
        'SELECT a.assignee_id, (u.first_name || " " || u.last_name) as assignee_name'
        ' FROM assignment a JOIN user u ON a.assignee_id = u.id'
        ' WHERE a.issue_id = ?',
        (issue_id,)
    ).fetchall()
    return [{'id': a['assignee_id'], 'name': a['assignee_name'] } for a in assignee_query]

@dml_operation
def update_issue_progress(issue_id, new_progress, cursor):
    cursor.execute(
        'UPDATE issue SET progress = ?'
        ' WHERE id = ?',
        (new_progress, issue_id)
    )
