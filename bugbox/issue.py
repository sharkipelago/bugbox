import functools
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required, team_lead_required, same_team_required, admin_required
from bugbox.db import get_db, get_user, get_users, get_issue_teams, get_assignees, get_team_names, create_issue, insert_assignment, update_issue_progress, get_comments, insert_comment, delete_issue_team, insert_issue_team, delete_assignment

bp = Blueprint('issue', __name__)

from bugbox.team import TEAM_IDS
DEAFULT_ADMIN_STATE = {
    'teams': [],
    'assignees': []
}
admin_create_state = 2

def get_subordinate_users():
    subordinate_users = None
    if g.user['admin_level'] == 1:
        subordinate_users = get_users(g.user['team_id'])
    elif g.user['admin_level'] == 2:
        subordinate_users = get_users()
    return subordinate_users

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
        return redirect(url_for('auth.denied'))

    return wrapped_view
# Can add updates on comment chain and submit issue
def contribute_perms_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if get_edit_level(kwargs.get('issue_id')) > 0:
            return view(**kwargs)
        return redirect(url_for('auth.denied'))

    return wrapped_view


def get_assignments():
    return get_db().execute(
        'SELECT a.id, issue_id, assignee_id, (first_name || " " || last_name) as assignee_name'
        ' FROM assignment a JOIN user u ON a.assignee_id = u.id'
    ).fetchall()

@bp.route("/", defaults={"progress": 0})
@bp.route('/<int:progress>/')
@login_required
def index(progress=0):
    assert progress == 0 or progress == 1 or progress == 2
    db = get_db()
    issues = db.execute(
        'SELECT *, (first_name || " " || last_name) AS author_name'
        ' FROM issue i'
        ' JOIN user u ON i.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    return render_template('issue/index.html', 
                           issues=issues, assignments=get_assignments(), 
                           issue_teams=get_issue_teams(), 
                           team_names=get_team_names(),
                           progress=progress
                           )

# TODO When admin creates issue can manually assign teams
# TODO when team lead creates issue, can choose to assign other teams besides own team
@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    global admin_create_state

    if request.method == 'POST':
        print(request.form)
        title = request.form['title']
        description = request.form['desc']
        initial_assignees = [int(k.split('-')[-1]) for k in request.form.keys() if k.startswith('assignee')]
        if g.user['admin_level'] == 0:
            initial_assignees = [g.user['id']] 
        initial_teams = None
        if g.user['admin_level'] == 2:
            initial_teams = list(set([get_user(i_a)['team_id'] for i_a in initial_assignees]))
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            create_issue(g.user['id'], title, description, initial_assignees, initial_teams)
            # admin_create_state.clear()
            return redirect(url_for('issue.index'))

    return render_template('issue/create.html', assignable_users=get_subordinate_users())


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
    return render_template('issue/details.html', 
                           issue=get_issue(issue_id), 
                           issue_teams=get_issue_teams(issue_id), 
                           assignees=get_assignees(issue_id), 
                           assignable_users=get_subordinate_users(),
                           users=get_users(), 
                           comments=get_comments(issue_id),
                           edit_level=get_edit_level(issue_id)
    )

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
@same_team_required
def add_assignee(issue_id, user_id):
    assert get_user(user_id)['team_id'] in get_issue_teams(issue_id)

    db = get_db()
    cursor = db.cursor()
    insert_assignment(cursor, issue_id, user_id)
    db.commit()
    return redirect(url_for('issue.details', issue_id=issue_id))

@bp.route('/<int:issue_id>/<int:user_id>/remove-assignee', methods=('GET',))
@login_required
@modify_perms_required
@same_team_required
def remove_assignee(issue_id, user_id):
    assert get_user(user_id)['team_id'] in get_issue_teams(issue_id)
    delete_assignment(issue_id, user_id)
    return redirect(url_for('issue.details', issue_id=issue_id))

@bp.route('/<int:issue_id>/<int:submitter_id>/submit-issue', methods=('POST',))
@login_required
@contribute_perms_required
def submit_issue(issue_id, submitter_id):
    update_issue_progress(issue_id, 1)
    submitter = get_user(submitter_id)
    status_update_content = f'{submitter['first_name']} {submitter['last_name']} submitted this issue for review'
    insert_comment(-1, issue_id, status_update_content)
    return redirect(url_for('issue.index',  progress=1))

@bp.route('/<int:issue_id>/<int:closer_id>/close-issue', methods=('POST',))
@login_required
@modify_perms_required
def close_issue(issue_id, closer_id):
    update_issue_progress(issue_id, 2)
    closer = get_user(closer_id)
    status_update_content = f'{closer['first_name']} {closer['last_name']} closed this issue'
    insert_comment(-1, issue_id, status_update_content)
    return redirect(url_for('issue.index', progress=2))

@bp.route('/<int:issue_id>/<int:reopener_id>/reopen-issue', methods=('POST',))
@login_required
@modify_perms_required
def reopen_issue(issue_id, reopener_id):
    update_issue_progress(issue_id, 0)
    reopener = get_user(reopener_id)
    status_update_content = f'{reopener['first_name']} {reopener['last_name']} reopened this issue'
    insert_comment(-1, issue_id, status_update_content)
    return redirect(url_for('issue.index', progress=0))

# TODO Make a modal pop up warning about removing all assignees
@bp.route('/<int:issue_id>/<int:team_id>/remove-issue-team')
@login_required
@team_lead_required
def remove_issue_team(issue_id, team_id):
    assert team_id in get_issue_teams(issue_id)
    for a in get_assignees(issue_id):
        if a['team_id'] == team_id:
            delete_assignment(issue_id, a['id'])
    delete_issue_team(issue_id, team_id)
    return redirect(url_for('issue.details', issue_id=issue_id))

@bp.route('/<int:issue_id>/<int:team_id>/add-issue-team')
@login_required
@team_lead_required
def add_issue_team(issue_id, team_id):
    assert team_id not in get_issue_teams(issue_id)
    insert_issue_team(issue_id, team_id)
    return redirect(url_for('issue.details', issue_id=issue_id))
