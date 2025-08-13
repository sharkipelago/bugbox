from collections import defaultdict
from typing import List, Optional
import functools, random
from os import getenv

from werkzeug.security import generate_password_hash
from werkzeug.exceptions import abort
from flask import g

from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import scoped_session, sessionmaker, DeclarativeBase, Mapped, relationship

from bugbox.team import TEAM_IDS

SUBMIT_STATUS_CONTENT = 'SUBMIT_STATUS_UPDATE',
CLOSE_STATUS_CONTENT = 'CLOSE_STATUS_UPDATE',
REOPEN_STATUS_CONTENT = 'REOPEN_STATUS_UPDATE'

DB_USER = getenv("MYSQL_USER")
DB_HOST = getenv("MYSQL_HOST")
DB_PASSWORD = getenv("MYSQL_PASSWORD")
DB_NAME = getenv("MYSQL_DB") 

engine = create_engine(f"mysql+mysqldb://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:3306/{DB_NAME}?charset=utf8mb4")
try:
    with engine.connect() as connection:
        print("Successfully connected to the MySQL database!")
except Exception as e:
    print(f"Error connecting to the database: {e}")

class Base(DeclarativeBase):
    pass

Base.metadata.reflect(engine)

# Association Tables should be core tables instead of ORM? https://docs.sqlalchemy.org/en/20/orm/basic_relationships.html#many-to-many
assignment = Base.metadata.tables['assignment']
issue_team = Base.metadata.tables['issue_team']

class Team(Base):
    __table__ = Base.metadata.tables['team']
    users: Mapped[List["User"]] = relationship(back_populates="team")
   
    assigned_issues: Mapped[List["Issue"]] = relationship(
        secondary=issue_team, back_populates="assigned_teams"
    )

class User(Base):
    __table__ = Base.metadata.tables['user']
    team: Mapped[Optional["Team"]] = relationship(back_populates="users")
    authored_issues: Mapped[List["Issue"]] = relationship(back_populates="author")
    comments: Mapped[List["Comment"]] = relationship(back_populates="author")
    
    assigned_issues: Mapped[List["Issue"]] = relationship(
        secondary=assignment, back_populates="assigned_users"
    )

class Issue(Base):
    __table__ = Base.metadata.tables['issue']
    author: Mapped["User"] = relationship(back_populates="authored_issues")
    comments: Mapped[List["Comment"]] = relationship(back_populates="issue", cascade="all, delete-orphan")

    assigned_users: Mapped[List["User"]] = relationship(
        secondary=assignment, back_populates="assigned_issues"
    )
    assigned_teams: Mapped[List["Team"]] = relationship(
        secondary=issue_team, back_populates="assigned_issues"
    )

class Comment(Base):
    __table__ = Base.metadata.tables['comment']
    author: Mapped["User"] = relationship(back_populates="comments")
    issue: Mapped["Issue"] = relationship(back_populates="comments")

db_session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))


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
        db_func(*args, **kwargs)
        get_db_session().commit()
    return wrapper

def get_db():
    pass

def get_db_session():
    if 'db_session' not in g:
        g.db_session = db_session
    return g.db_session


def close_db(e=None):
    db_session = g.pop('db_session', None)

    if db_session is not None:
        db_session.remove()

def init_app(app):
    app.teardown_appcontext(close_db)

# TEAMS
def get_team(team_id):
    return get_db_session().get(Team, team_id)

def get_team_names():
    team_query = get_db_session().scalars(select(Team)).all()
    team_names = {}
    for t in team_query:
        team_names[t.id] = t.team_name
    return team_names

# USERS
def create_user(username, password, first_name, last_name, admin_level, team=TEAM_IDS["Frontend"], pfp_filename=None):
    u = User(
        username=username, 
        password=generate_password_hash(password), 
        first_name=first_name, 
        last_name=last_name, 
        admin_level=admin_level,
        team_id=TEAM_IDS["Admin"] if admin_level == 2 else team,
        pfp_filename='pfp/' + (pfp_filename if pfp_filename else random.choice(DEFAULT_PFPS))
    )
    db = get_db_session()
    db.add(u)
    db.commit()

def get_user(user_id):
    return get_db_session().scalars(select(User).where(User.id == user_id)).first()

def get_users(team_id = None):
    if team_id:
        return get_db_session().scalars(select(User).where(User.team_id == team_id)).all()
    return get_db_session().scalars(select(User)).all()

def get_user_by_username(username): 
    return db_session.scalars(select(User).where(User.username == username)).first()

@dml_operation
def update_user_team(user_id, team_id):
    user = get_db_session().get(User, user_id)
    assert user.admin_level == 0 or team_id # Makes sure you don't set a team lead or admin to unassiagned team
    user.team_id = team_id

@dml_operation
def update_admin_level(user_id, admin_level):
    user = get_db_session().get(User, user_id)
    assert admin_level == 0 or user.team_id # Makes sure you don't set a team lead or admin to unassiagned team
    user.admin_level = admin_level

# ISSUES
@dml_operation
def create_issue(author_id, title, initial_comment, assignee_ids = []):
    db_session = get_db_session()
    i = Issue(
        author_id = author_id,
        title = title
    )
    db_session.add(i)
    db_session.commit()
    assert i.id is not None

    initial_assignees = assignee_ids if assignee_ids else [author_id]
    for t_id in set([get_user(i_a).team_id for i_a in initial_assignees]):
        insert_issue_team(i.id, t_id)

    insert_comment(author_id, i.id, initial_comment)
    for a in initial_assignees:
        insert_assignment(i.id, a)
    return i.id

@dml_operation
def update_issue_progress(issue_id, new_progress):
    issue = get_issue(issue_id)
    issue.progress = new_progress

def get_issue(issue_id):
    issue =  get_db_session().get(Issue, issue_id)
    if not issue:
        abort(404, f"Post id {id} doesn't exist.")
    return issue


def get_all_issues():
    stmt = (
        select(Issue, func.concat(User.first_name, ' ', User.last_name).label('author_name'))
        .join(Issue.author)
        .order_by(Issue.created.desc())
    )
    return get_db_session().scalars(stmt).all()

@dml_operation
def delete_issue(issue_id):
    issue = get_issue(issue_id)
    get_db_session().delete(issue)

# COMMENTS
@dml_operation
def insert_comment(author_id, issue_id, content):
    c = Comment(author_id=author_id, issue_id=issue_id, content=content)
    db_session = get_db_session()
    db_session.add(c)

@dml_operation
def insert_status_update(user_id, issue_id, target_progress_level):
    assert target_progress_level == 0 or target_progress_level == 1 or target_progress_level == 2
    content = None
    if target_progress_level == 0:
        content = REOPEN_STATUS_CONTENT
    elif target_progress_level == 1:
        content = SUBMIT_STATUS_CONTENT
    elif target_progress_level == 2:
        content = CLOSE_STATUS_CONTENT
    c = Comment(author_id=user_id, issue_id=issue_id, content=content)

    db = get_db_session()
    db.add(c)

# ASSIGNMENTS
@dml_operation
def insert_assignment(issue_id, assignee_id):
    assert get_user(assignee_id).team_id in get_issue_teams(issue_id) or get_user(assignee_id).admin_level == 2
    issue = get_issue(issue_id)
    issue.assigned_users.append(get_user(assignee_id))

@dml_operation
def delete_assignment(issue_id, assignee_id):
    issue = get_db_session().get(Issue, issue_id)
    issue.assigned_users.remove(get_user(assignee_id))

@dml_operation
def delete_all_assignments(user_id):
    user = get_db_session().get(User, user_id)
    user.assigned_issues[:] = []

def get_assignees(issue_id):
    issue = get_issue(issue_id)
    return [{'id': a.id, 'name': f"{a.first_name} {a.last_name}", 'team_id': a.team_id } for a in issue.assigned_users]

def get_all_assignments():
    stmt = (
        select(Issue, func.concat(User.first_name, ' ', User.last_name).label('assignee_name'))
        .join(Issue.assigned_users)
    )
    return get_db_session().execute(stmt).all()

# ISSUE TEAMS
@dml_operation
def insert_issue_team(issue_id, team_id):
    issue = get_issue(issue_id)
    issue.assigned_teams.append(get_team(team_id))

@dml_operation
def delete_issue_team(issue_id, team_id):
    issue = get_issue(issue_id)
    issue.assigned_teams.remove(get_team(team_id))

def get_issue_teams(issue_id):
    issue_teams_query =  get_db_session().execute(select(issue_team)).all()
    issue_teams = defaultdict(list)
    for i_t in issue_teams_query:
        issue_teams[i_t.issue_id].append(i_t.team_id)
    return issue_teams[issue_id]

def get_all_issue_teams():
    issue_teams_query =  get_db_session().execute(select(issue_team)).all()
    issue_teams = defaultdict(list)
    for i_t in issue_teams_query:
        issue_teams[i_t.issue_id].append(i_t.team_id)
    return issue_teams