import sqlite3
from datetime import datetime
from collections import defaultdict
import functools, random

from werkzeug.security import generate_password_hash

import click
from flask import current_app, g

from bugbox.team import TEAM_IDS
DEFAULT_STATUS_UPDATE_SUBMIT = -1
DEFAULT_STATUS_UPDATE_CLOSE = -2

DEFAULT_PFPS = [
    'default-cicada.jpg',
    'default-dragonfly.jpg',
    'default-grasshopper.jpg',
    'default-ladybug.jpg',
    'default-stagbeetle.jpg'
]

DEFAULT_USERS = [
    # Admin
    ("md", "mooodeng", "Moo", "Deng", 2, None, 'moo.jpg'), 
    # Team Lead
    ("puxp", "punxsutawney", "Phil", "Punxsutawney", 1, TEAM_IDS["Mobile"], 'punxsutawney.jpg'),
    ("simba","ifittouchesthesun", "Simba", "", 1, TEAM_IDS['DevOps'], 'simba.jpg'),
    ("hachi","hachikoko", "Chūken", "Hachikō", 1, TEAM_IDS["Backend"], 'hachikō.png'),
    # User
    ("harambe","rememberharambe", "Harambe", "Van Coppenolle", 0, TEAM_IDS["Mobile"], 'harambe.jpg'),
    ("pomgpriv", "computeroverride", "Private", "", 0, TEAM_IDS['Mobile'], 'private.jpg'),      
    ("crikey", "saltwatercroc", "Bindi", "Irwin", 0, TEAM_IDS["DevOps"], 'bindi.jpg'),
    ("ohana", "experiment626", "Stitch", "Pelekai", 0, TEAM_IDS['Backend'], 'stitch.jpg'),
    ("laika","laikaspaceneighbor", "Laika", "Kudryavka", 0, TEAM_IDS["QA"], 'laika.jpg'),
    ("wolly", "mammmmoth", "Lyuba", "Khudi", 0, None, 'lyuba.jpg'),
]

DEFAULT_USER_IDS = {user[2] : i+1 for i, user in enumerate(DEFAULT_USERS)}

DEFAULT_ISSUES = [
    (DEFAULT_USER_IDS['Phil'], 1, [DEFAULT_USER_IDS['Phil'], DEFAULT_USER_IDS['Private'], DEFAULT_USER_IDS['Harambe']], "Shadow Detection", "Some mobile users are reporting an erroneous six more weeks of winter with a negative shadow reading after the 1.13 patch. Could we check that out?"),
    (DEFAULT_USER_IDS['Phil'], 2, [DEFAULT_USER_IDS['Phil'], DEFAULT_USER_IDS['Private']], "Apple Pay Vulnerabilities", "The security scan showed a couple minor vulnerabilities for your proposed Apple Pay integration, but I was pretty sure you had everything cleared after this morning's stand-up?"),
    (DEFAULT_USER_IDS['Bindi'], 0, [], "Outback Servers Bandwidth Consumption", "Got notice that our outback servers are seeing sudden spikes in bandwidth consumption. I know we started sharing the servers with some local companies, but the impact should not be this drastic."),
    (DEFAULT_USER_IDS['Chūken'], 0, [DEFAULT_USER_IDS['Stitch']], "Data Lake Migration API Ohana Errors?", "@Stitch A lot of your API pull requests looks like they're adding new features with an Ohana library? As discussed in the planning meeting, because the data lake itself is already using a lot of new tooling, right now we just want to focus migrating from the previous data warehouse. This means our new data lake query APIs should not have any new dependencies that our old APIs did not have. "),
    (DEFAULT_USER_IDS['Laika'], 0, [], "Совместимость с космическим пространством", "Я тестировал этот продукт в космосе. оно сломалось.")
]

DEFAULT_COMMENTS = [
    # Shadow Detection Issue 1
    (DEFAULT_USER_IDS['Private'], 1, "Sir, I looked into it. It seems like it's mostly affecting users with older devices. Specifically, the update is having compatibility problems with systems before iOS 18 and Android 15."),
    (DEFAULT_USER_IDS['Harambe'], 1,"I submitted a hotfix to revert back to the previous version, but still tackling a permanent fix; @Phil could you give it a look over when you get a chance?"),
    (DEFAULT_USER_IDS['Harambe'], 1, DEFAULT_STATUS_UPDATE_SUBMIT),
    # Apple Pay Issue 2
    (DEFAULT_USER_IDS['Private'], 2, "Apologies, I had not sent the most recent scan results, just sent them over now."),
    (DEFAULT_USER_IDS['Private'], 2, DEFAULT_STATUS_UPDATE_SUBMIT),
    (DEFAULT_USER_IDS['Phil'], 2, "@Private thank you"),
    (DEFAULT_USER_IDS['Phil'], 2, DEFAULT_STATUS_UPDATE_CLOSE),
    # Outback Bandwidth Issue 3
    (DEFAULT_USER_IDS['Simba'], 3, "Thanks for bringing this up @Bindi. That should not be happening. Make sure that the other organizations are primarily on the HPC clusters; everything the lightweight servers touch is our kingdom."),
    # Data Lake Migration Issue 4
    (DEFAULT_USER_IDS['Stitch'], 4, "Ohana means family and family means Stitch thinks we should use migration as an opportunity to address some inefficiencies of the old data query APIs."),
    (DEFAULT_USER_IDS['Chūken'], 4, "I completely understand your concern, but right now as a team we're focused on migration, which is taking up a lot of resources and delaying services for our users. Right now, I think it's best if we diligently work towards making sure the migration goes smoothly. Afterwards we can focus on addressing inefficiencies."),
    (DEFAULT_USER_IDS['Chūken'],4, "Additionally, an explanation of the Ohana library more comprehensive explanation than “it means family” would be appreciated."),
    # Russian Issue 5
    (DEFAULT_USER_IDS['Laika'], 5, "Я тестировал этот продукт в космосе. оно сломалось.")
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
        author_id, progress, assignees, title, initial_comment = i 
        issue_id = create_issue(author_id, title, initial_comment, assignees)
        update_issue_progress(issue_id, progress)

    for c in DEFAULT_COMMENTS:
        user_id, issue_id, content = c 
        if content == DEFAULT_STATUS_UPDATE_SUBMIT:
            insert_status_update(user_id, issue_id, 1)
        elif content == DEFAULT_STATUS_UPDATE_CLOSE:
            insert_status_update(user_id, issue_id, 2)
        else:
            insert_comment(user_id, issue_id, content)

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


def get_user(user_id):
    return get_db().execute(
        'SELECT *'
        ' FROM user u'
        ' WHERE u.id = ?',
        (user_id,)
    ).fetchone()  



def create_user(username, password, first_name, last_name, admin_level, team=None, pfp_filename=None):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO user (username, [password], first_name, last_name, admin_level, team_id, pfp_filename)' 
        ' VALUES (?, ?, ?, ?, ?, ?, ?)',
        (username, generate_password_hash(password), first_name, last_name, admin_level, 
         TEAM_IDS["Admin"] if admin_level == 2 else team,
         'pfp/' + (pfp_filename if pfp_filename else random.choice(DEFAULT_PFPS))
        )
    )
    cursor.close()
    db.commit()

def create_issue(author_id, title, initial_comment, assignee_ids = []):
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        'INSERT INTO issue (author_id, title)'
        ' VALUES (?, ?)',
        (author_id, title)
    )
    issue_id = cursor.lastrowid

    initial_assignees = assignee_ids if assignee_ids else [author_id]
    print("USER2============", get_user(2).keys())
    print("==================SETTY=========", [get_user(i_a).keys() for i_a in initial_assignees])
    for t_id in set([get_user(i_a)['team_id'] for i_a in initial_assignees]):
        print("TEAMIDDD:", t_id)
        insert_issue_team(issue_id, t_id)

    insert_comment(author_id, issue_id, initial_comment, cursor)
    for a in initial_assignees:
        insert_assignment(cursor, issue_id, a)
    cursor.close()
    db.commit()   
    return issue_id

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

def get_all_issues():
    return get_db().execute(
        'SELECT *, (first_name || " " || last_name) AS author_name'
        ' FROM issue i'
        ' JOIN user u ON i.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

@dml_operation
def insert_status_update(user_id, issue_id, target_progress_level, cursor=None):
    user = get_user(user_id)
    status_update_content = f'{user['first_name']} {user['last_name']} '
    if target_progress_level == 0:
        status_update_content +='reopened this issue'
    elif target_progress_level == 1:
        status_update_content += 'submitted this issue for review'
    elif target_progress_level == 2:
        status_update_content += 'closed this issue'
    insert_comment(-1, issue_id, status_update_content)