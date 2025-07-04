from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required
from bugbox.db import get_db

bp = Blueprint('issue', __name__)

@bp.route('/')
@login_required
def index():
    db = get_db()
    issues = db.execute(
        'SELECT i.id, title, body, created, author_id, (first_name || " " || last_name) AS author_name'
        ' FROM issue i'
        ' JOIN user u ON i.author_id = u.id'
        ' ORDER BY created DESC'
    ).fetchall()

    # db.execute returns generator
    assignments = list(db.execute(
        'SELECT a.id, issue_id, assignee_id, (first_name || " " || last_name) as assignee_name'
        ' FROM assignment a JOIN user u ON a.assignee_id = u.id'
    ))
    
    print(assignments)
    return render_template('issue/index.html', issues=issues, assignments=assignments)

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
            db = get_db()
            cursor = db.cursor()
            cursor.execute(
                'INSERT INTO issue (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            if 'self-assign' in request.form:
                cursor.execute(
                    'INSERT INTO assignment (issue_id, assignee_id)'
                    ' VALUES (?, ?)',
                    (cursor.lastrowid, g.user['id'])
                )
            db.commit()
            return redirect(url_for('issue.index'))

    return render_template('issue/create.html')

def get_issue(id, check_author=True):
    issue = get_db().execute(
        'SELECT i.id, title, body, created, author_id, username'
        ' FROM issue i JOIN user u ON i.author_id = u.id'
        ' WHERE i.id = ?',
        (id,)
    ).fetchone()

    if issue is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and issue['author_id'] != g.user['id']:
        abort(403)

    return issue

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_issue(id)

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
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('issue.index'))
    return render_template('issue/update.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_issue(id)
    db = get_db()
    db.execute('DELETE FROM issue WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('issue.index'))