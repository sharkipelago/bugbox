from collections import defaultdict

from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required, team_lead_required
from bugbox.db import get_db, get_user, get_users, get_issue_teams, get_assignees, get_team_names, create_issue, insert_assignment

bp = Blueprint('issue', __name__)


def get_assignments():
    return get_db().execute(
        'SELECT a.id, issue_id, assignee_id, (first_name || " " || last_name) as assignee_name'
        ' FROM assignment a JOIN user u ON a.assignee_id = u.id'
    ).fetchall()

def delete_assignment(cursor, issue_id, assignee_id):
    cursor.execute('DELETE FROM assignment WHERE issue_id = ? AND assignee_id = ?', (issue_id, assignee_id))

@bp.route('/')
@login_required
def index():
    db = get_db()
    issues = db.execute(
        'SELECT i.id, title, body, created, author_id, (first_name || " " || last_name) AS author_name, team_id'
        ' FROM issue i'
        ' JOIN user u ON i.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    return render_template('issue/index.html', issues=issues, assignments=get_assignments(), issue_teams=get_issue_teams(), team_names=get_team_names())

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            initial_assignees = []
            if 'self-assign' in request.form:
                initial_assignees.append( g.user['id']) 
            create_issue(g.user['id'], title, body, initial_assignees)
            return redirect(url_for('issue.index'))

    return render_template('issue/create.html')

def get_issue(id, check_author=True):
    issue = get_db().execute(
        'SELECT i.id, title, body, created, author_id, username, team_id'
        ' FROM issue i JOIN user u ON i.author_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if issue is None:
        abort(404, f"Post id {id} doesn't exist.")

    admin_access = issue['team_id'] == g.user['team_id'] and g.user['admin_level'] > 0
    if check_author and issue['author_id'] != g.user['id'] and not admin_access:
        abort(403)

    return issue

@bp.route('/<int:issue_id>/update', methods=('GET', 'POST'))
@login_required
def update(issue_id):
    issue = get_issue(issue_id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE issue SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, issue_id)
            )
            db.commit()
            return redirect(url_for('issue.index'))
    print(get_users())
    return render_template('issue/update.html', issue=issue, assignees=get_assignees(issue_id), users=get_users())

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_issue(id)
    db = get_db()
    db.execute('DELETE FROM issue WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('issue.index'))

@bp.route('/<int:issue_id>/<int:user_id>/add-assignee', methods=('GET',))
@login_required
@team_lead_required
def add_assignee(issue_id, user_id):
    assert g.user['team_id'] in get_issue_teams()[issue_id]
    assert get_user(user_id)['team_id'] in get_issue_teams()[issue_id]

    db = get_db()
    cursor = db.cursor()
    insert_assignment(cursor, issue_id, user_id)
    db.commit()
    return redirect(url_for('issue.update', issue_id=issue_id))

@bp.route('/<int:issue_id>/<int:assignee_id>/remove-assignee', methods=('GET',))
@login_required
@team_lead_required
def remove_assignee(issue_id, assignee_id):
    assert g.user['team_id'] in get_issue_teams()[issue_id]
    assert get_user(assignee_id)['team_id'] in get_issue_teams()[issue_id]

    db = get_db()
    cursor = db.cursor()
    delete_assignment(cursor, issue_id, assignee_id)
    db.commit()
    return redirect(url_for('issue.update', issue_id=issue_id))

