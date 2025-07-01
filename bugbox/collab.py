
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required
from bugbox.db import get_db

bp = Blueprint('collab', __name__, url_prefix='/collab')

@bp.route('/')
@login_required
def index():
    db = get_db()
    users = db.execute(
        'SELECT * FROM user'
    ).fetchall()

    return render_template('collab/index.html', users=users)