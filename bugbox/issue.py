import functools
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required
from bugbox.db import get_db, get_user, get_users, get_issue_teams, get_assignees, get_team_names, create_issue, insert_assignment, update_issue_progress, get_comments, insert_comment

bp = Blueprint('issue', __name__)

# how much can this user edit this issue
def get_edit_level(issue_id):
    team_ids = get_issue_teams(issue_id)
    assignee_ids = [a['id'] for a in get_assignees(issue_id)]
    issue = get_issue(issue_id)

    if g.user['admin_level'] == 2 or g.user['admin_level'] == 1 and g.user['team_id'] in team_ids:
        return 2
    elif g.user['id'] in assignee_ids or g.user['id'] == issue['author_id']:
        return 1
    return 0
    

# ==View Wrappers==
# Can Update, Delete, Edit Assignees, Mark as Reviewed and Close an issue in addition to contribute_perms
def modify_perms_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_edit_level(kwargs.get('issue_id')) == 2:
            return view(**kwargs)
        # TODO custom modify_perms denied page
        return redirect(url_for('admin.denied'))

    return wrapped_view
# Can add updates on comment chain and submit issue
def contribute_perms_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_edit_level(kwargs.get('issue_id')) > 0:
            return view(**kwargs)
        # TODO custom modify_perms denied page
        return redirect(url_for('admin.denied'))

    return wrapped_view


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
        'SELECT *, (first_name || " " || last_name) AS author_name'
        ' FROM issue i'
        ' JOIN user u ON i.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    print("TEST", issues[0].keys())
    return render_template('issue/index.html', issues=issues, assignments=get_assignments(), issue_teams=get_issue_teams(), team_names=get_team_names())

# TODO When admin creates issue can manually assign teams
# TODO when team lead creates issue, can choose to assign other teams besides own team
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

def get_issue(id):
    issue = get_db().execute(
        'SELECT *'
        ' FROM issue i JOIN user u ON i.author_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if issue is None:
        abort(404, f"Post id {id} doesn't exist.")

    # admin_access = issue['team_id'] == g.user['team_id'] and g.user['admin_level'] > 0
    # if check_author and issue['author_id'] != g.user['id'] and not admin_access:
    #     abort(403)

    return issue

@bp.route('/<int:issue_id>/details')
@login_required
def details(issue_id):
    issue = get_issue(issue_id)
    return render_template('issue/details.html', issue=issue, issue_teams=get_issue_teams(issue_id), assignees=get_assignees(issue_id), users=get_users(), comments=get_comments(issue_id), edit_level=get_edit_level(issue_id))

@bp.route('/<int:issue_id>/add-comment', methods=('POST',))
@login_required
@contribute_perms_required
def add_comment(issue_id):
    content = request.form['content']
    error = None
    if not content:
        error = 'Blank comments are not allowed'
    if error is not None:
        flash(error)

    insert_comment(g.user['id'], issue_id, content)
    return redirect(url_for('issue.details', issue_id=issue_id))


@bp.route('/<int:issue_id>/update', methods=('POST',))
@login_required
@modify_perms_required
def update(issue_id):
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
    return redirect(url_for('issue.details', issue_id=issue_id))

@bp.route('/<int:issue_id>/delete', methods=('POST',))
@login_required
@modify_perms_required
def delete(issue_id):
    get_issue(issue_id)
    db = get_db()
    db.execute('DELETE FROM issue WHERE id = ?', (issue_id,))
    db.commit()
    return redirect(url_for('issue.index'))

@bp.route('/<int:issue_id>/<int:user_id>/add-assignee', methods=('GET',))
@login_required
@modify_perms_required
def add_assignee(issue_id, user_id):
    assert get_user(user_id)['team_id'] in get_issue_teams(issue_id)

    db = get_db()
    cursor = db.cursor()
    insert_assignment(cursor, issue_id, user_id)
    db.commit()
    return redirect(url_for('issue.details', issue_id=issue_id))

@bp.route('/<int:issue_id>/<int:assignee_id>/remove-assignee', methods=('GET',))
@login_required
@modify_perms_required
def remove_assignee(issue_id, assignee_id):
    assert get_user(assignee_id)['team_id'] in get_issue_teams(issue_id)

    db = get_db()
    cursor = db.cursor()
    delete_assignment(cursor, issue_id, assignee_id)
    db.commit()
    return redirect(url_for('issue.details', issue_id=issue_id))

@login_required
# TODO assignee required
# TODO Change to post for more security?
@bp.route('/<int:issue_id>/<int:submitter_id>/submit-issue', methods=('GET',))
def submit_issue(issue_id, submitter_id):
    update_issue_progress(issue_id, 1)
    return redirect(url_for('issue.index'))

@login_required
# TODO assignee required
@bp.route('/<int:issue_id>/<int:closer_id>/close-issue', methods=('GET',))
def close_issue(issue_id, closer_id):
    update_issue_progress(issue_id, 2)
    return redirect(url_for('issue.index'))
