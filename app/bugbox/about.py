
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required
from bugbox.db import get_db, get_users

bp = Blueprint('about', __name__, url_prefix='/about')

@bp.route('/')
@login_required
def index():
    return render_template('about.html')