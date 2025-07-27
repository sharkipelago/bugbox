import sqlite3
from datetime import datetime
from collections import defaultdict
import functools

from werkzeug.security import generate_password_hash

import click
from flask import current_app, g

from bugbox.team import TEAM_IDS

DEFAULT_USERS = [
    # Admin
    ("md", "mooodeng", "Moo", "Deng", 2), 
    # Team Lead
    ("puxp", "punxsutawney", "Punxsutawney", "Phil", 1, TEAM_IDS["Mobile"]),
    ("ohana", "experiment626", "Stitch", "Pelekai", 1, TEAM_IDS['DevOps']),
    # User
    ("hachi","hachikoko", "Chūken", "Hachikō", 0, TEAM_IDS["Backend"]),
    ("harambe","rememberharambe", "Harambe", "Van Coppenolle", 0, TEAM_IDS["Mobile"]),
    ("laika","laikaspaceneighbor", "Laika", "Kudryavka", 0, TEAM_IDS["QA"]),
    ("simba","ifittouchesthesun", "King", "Simba", 0, None),
    # Team Lead 
    ("pomgpriv", "computeroverride", "Private", "Madagascar", 1, TEAM_IDS['Backend']),
]

DEFAULT_ISSUES = [
    (2, "Probably more winter", "I think I saw the shadow? But I also just woke up it could've been a hibernation dust build-up", [2, 5]),
    (2, "Pennsylvanian top hats", "Where can I accquire one?"),
    (4, "飼い主はまだ帰っていないの？", "彼がお菓子を持ってきてくれるといいな"),
    (5, "Zoo transfer request", "This place is too hot"),
    (6, "Вкусы мороженого «Астронавт»", "будут ли другие вкусы, кроме шоколада?")
]


def dml_operation(db_func):
    @functools.wraps(db_func)
    def wrapper(*args, **kwargs):
        db = get_db()
        cursor = db.cursor()
        db_func(*args, cursor=cursor, **kwargs)
        cursor.close()
        db.commit()
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

def create_issue(author_id, title, initial_comment, assignee_ids = [], team_ids = None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO issue (author_id, title)'
        ' VALUES (?, ?)',
        (author_id, title)
    )
    issue_id = cursor.lastrowid

    if not team_ids:
        insert_issue_team(issue_id, get_user(author_id)['team_id'])
    else:
        for t_id in team_ids:
            insert_issue_team(issue_id, t_id)

    insert_comment(author_id, issue_id, initial_comment, cursor)
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

def get_users(team_id = None):
    if team_id:
        return get_db().execute(
            'SELECT * FROM user u WHERE u.team_id = ?',
            (team_id, )
        ).fetchall() 
    
    return get_db().execute(
        'SELECT *'
        ' FROM user u LEFT JOIN team t ON u.team_id = t.id'
    ).fetchall()

def get_comments(issue_id):
    return get_db().execute(
        'SELECT c.*, (u.first_name || " " || u.last_name) as author_name'
        ' FROM comment c'
        ' LEFT JOIN user u ON c.author_id = u.id'
        ' WHERE c.issue_id = ?',
        (issue_id,)
    ).fetchall()


# Only executes not resposible for committing or anything
def insert_assignment(cursor, issue_id, assignee_id):
    # print(get_user(assignee_id)['team_id'], get_issue_teams()[issue_id])
    assert get_user(assignee_id)['team_id'] in get_issue_teams()[issue_id] or get_user(assignee_id)['admin_level'] == 2
    cursor.execute(
        'INSERT INTO assignment (issue_id, assignee_id)'
        ' VALUES (?, ?)',
        (issue_id, assignee_id)
    )

# If cursor is provided, will not self_commit
def insert_comment(author_id, issue_id, content, _cursor=None):
    cursor = _cursor if _cursor else get_db().cursor()
    cursor.execute(
        'INSERT into comment (author_id, issue_id, content)'
        ' VALUES (?, ?, ?)',
        (author_id, issue_id, content)
    )
    if _cursor:
        return
    cursor.close()
    get_db().commit()

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
    
    issue_teams = defaultdict(list)
    for i_t in issue_teams_query:
        issue_teams[i_t['issue_id']].append(i_t['team_id'])
   
    if issue_id:
        return issue_teams[issue_id]
    return issue_teams

def get_assignees(issue_id):
    assignee_query = get_db().execute(
        'SELECT *, (u.first_name || " " || u.last_name) as assignee_name'
        ' FROM assignment a JOIN user u ON a.assignee_id = u.id'
        ' WHERE a.issue_id = ?',
        (issue_id,)
    ).fetchall()
    return [{'id': a['assignee_id'], 'name': a['assignee_name'], 'team_id': a['team_id'] } for a in assignee_query]

# def get_assignments(user_id):
#     assignment_query = get_db().execute(
#         'SELECT *'
#         ' FROM assignment a'
#         ' WHERE u.user_id = ?',
#         (user_id,)
#     ).fetchall()
#     return [a['issue_id'] for a in assignment_query]

@dml_operation
def update_issue_progress(issue_id, new_progress, cursor=None):
    cursor.execute(
        'UPDATE issue SET progress = ?'
        ' WHERE id = ?',
        (new_progress, issue_id)
    )

@dml_operation
def delete_issue_team(issue_id, team_id, cursor=None):
    cursor.execute(
        'DELETE FROM issue_team'
        ' WHERE issue_id = ? AND team_id = ?', 
        (issue_id, team_id)
    )


@dml_operation
def insert_issue_team(issue_id, team_id, cursor=None):
    cursor.execute(
        'INSERT INTO issue_team (issue_id, team_id)'
        ' VALUES (?, ?)', 
        (issue_id, team_id)
    )

@dml_operation
def delete_assignment(issue_id, assignee_id, cursor=None):
    cursor.execute('DELETE FROM assignment WHERE issue_id = ? AND assignee_id = ?', (issue_id, assignee_id))

@dml_operation
def delete_all_assignments(user_id, cursor=None):
    print(user_id)
    cursor.execute('DELETE FROM assignment WHERE assignee_id = ?', (user_id, ))

@dml_operation
def update_user_team(user_id, team_id, cursor=None):
    cursor.execute(
        'UPDATE user SET team_id = ?'
        ' WHERE id = ?',
        (team_id, user_id)
    )

@dml_operation
def update_admin_level(user_id, admin_level, cursor=None):
    cursor.execute(
        'UPDATE user SET admin_level = ?'
        ' WHERE id = ?',
        (admin_level, user_id)
    )