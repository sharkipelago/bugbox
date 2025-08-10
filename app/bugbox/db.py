from datetime import datetime
from collections import defaultdict
import functools, random
import os


from werkzeug.security import generate_password_hash
from flask import current_app, g

from sqlalchemy import create_engine, Table, select
from sqlalchemy.orm import scoped_session, sessionmaker, declarative_base
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import MetaData

from bugbox.team import TEAM_IDS

DB_USER = os.getenv("MYSQL_USER")
DB_HOST = os.getenv("MYSQL_HOST")
DB_PASSWORD = os.getenv("MYSQL_PASSWORD")
DB_NAME = os.getenv("MYSQL_DB") 

engine = create_engine(f"mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}")
try:
    with engine.connect() as connection:
        print("Successfully connected to the MySQL database!")
except Exception as e:
    print(f"Error connecting to the database: {e}")

# db_session = scoped_session(sessionmaker(autocommit=False,
#                                          autoflush=False,
#                                          bind=engine))

metadata_obj = MetaData()
user_table = Table("user", metadata_obj, autoload_with=engine)


DEFAULT_STATUS_UPDATE_SUBMIT = -1
DEFAULT_STATUS_UPDATE_CLOSE = -2

DEFAULT_PFPS = [
    'default-cicada.jpg',
    'default-dragonfly.jpg',
    'default-grasshopper.jpg',
    'default-ladybug.jpg',
    'default-stagbeetle.jpg'
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

# sqlite3.register_converter(
#     "timestamp", lambda v: datetime.fromisoformat(v.decode())
# )

def init_app(app):
    print("===PRINTING TEST SELECT===")
    stmt = select(user_table).where(user_table.c.first_name == "Private")
    with engine.connect() as conn:
        for row in conn.execute(stmt):
            print(row)
    print("===ENDING TEST SELECT===")

    app.teardown_appcontext(close_db)


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
    for t_id in set([get_user(i_a)['team_id'] for i_a in initial_assignees]):
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