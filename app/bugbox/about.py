from flask import Blueprint, render_template

from bugbox.auth import login_required

bp = Blueprint('about', __name__, url_prefix='/about')

@bp.route('/')
@login_required
def index():
    return render_template('about.html')