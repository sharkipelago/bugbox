
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required
from bugbox.db import get_db, get_users
from bugbox.team import TEAMS

bp = Blueprint('collab', __name__, url_prefix='/collab')

@bp.route('/')
@login_required
def index():
    return render_template('collab/index.html', users=get_users(), teams=TEAMS)