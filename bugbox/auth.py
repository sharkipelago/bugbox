import functools
from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from wtforms import Form, StringField, PasswordField, SubmitField, validators

from bugbox.db import get_db

bp = Blueprint('auth', __name__, url_prefix='/auth')

class RegistrationForm(Form):
    first_name = StringField(render_kw={"placeholder": "First Name"})
    last_name = StringField(render_kw={"placeholder": "Last Name"})
    username = StringField(render_kw={"placeholder": "Username"})
    password = PasswordField(render_kw={"placeholder": "Password"})
    confirm = PasswordField(render_kw={"placeholder": "Confirm Password"})
    submit = SubmitField(render_kw={"value": "Register"})

class LoginForm(Form):
    username = StringField(render_kw={"placeholder": "Username"})
    password = PasswordField(render_kw={"placeholder": "Password"})
    submit = SubmitField(render_kw={"value": "Login"})


@bp.route('/register', methods=('GET', 'POST'))
def register():
    form = RegistrationForm(request.form)

    if request.method == 'POST': #and form.validate():
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        username = request.form['username']
        password = request.form['password']
        confirm = request.form['confirm']
        db = get_db()
        error = None

        if not first_name or not last_name:
            error = 'First name and last name are required'
        if not username:
            error = 'Username is required'
        elif not password:
            error = 'Password is required'
        elif len(password) < 8:
            error = 'Password is must be at least 8 characters long'
        elif not confirm:
            error = 'Password confirmation is required'
        elif password != confirm:
            error = 'Passwords do not match'
        if error is None:
            try:
                # By default new registered users will join team unassigned
                db.execute(
                    "INSERT INTO user (username, [password], first_name, last_name, admin_level, team_id) VALUES (?, ?, ?, ?, ?, ?)",
                    (username, generate_password_hash(password), first_name, last_name, 0, -1),
                )
                db.commit()
                flash('Thanks for registering!', 'success')
            except db.IntegrityError:
                error = f"User {username} is already registered."
            else:
                return redirect(url_for("auth.login"))

        flash(error)

    return render_template('auth/register.html', form=form)

@bp.route('/login', methods=('GET', 'POST'))
def login():
    form = LoginForm(request.form)
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Username not found'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect password'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            return redirect(url_for('index'))

        flash(error)

    return render_template('auth/login.html', form=form)

# used to allow people looking at the sight to view the sight from admin perspective
@bp.route('/admin-login')
def guest_admin_login():
    session.clear()
    session['user_id'] = 1
    return redirect(url_for('index'))

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('auth.login'))

        return view(**kwargs)

    return wrapped_view

# TODO move this to an admin.py
def team_lead_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user["admin_level"] < 1:
            return redirect(url_for('admin.denied'))

        return view(**kwargs)

    return wrapped_view