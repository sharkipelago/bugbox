
from flask import Blueprint, flash, g, redirect, render_template, request, url_for
from werkzeug.exceptions import abort

from bugbox.auth import login_required, team_lead_required, same_team_required, admin_required
from bugbox.db import get_user, get_users, update_user_team, delete_all_assignments, update_admin_level

bp = Blueprint('collab', __name__, url_prefix='/collab')

@bp.route('/')
@login_required
def index():
    return render_template('collab/index.html', users=get_users())

# Not passing any value for team_id will "unassign" that user from all teams
@bp.route('/<int:user_id>/<int:team_id>/assign-team')
@login_required
@team_lead_required
def assign_team(user_id, team_id):
    assert get_user(user_id)['team_id'] != team_id
    update_user_team(user_id, team_id)
    return redirect(url_for('collab.index'))

@bp.route('/<int:user_id>/<int:team_id>/remove-from-team')
@login_required
@team_lead_required
@same_team_required
def remove_from_team(user_id, team_id):
    assert get_user(user_id)['team_id'] == team_id
    update_user_team(user_id, None)
    delete_all_assignments(user_id)
    return redirect(url_for('collab.index'))

@bp.route('/<int:user_id>/<int:new_admin_level>/change-admin-level')
@login_required
@admin_required
def change_admin_level(user_id, new_admin_level):
    assert get_user(user_id)['admin_level'] < 2
    assert get_user(user_id)['admin_level'] != new_admin_level
    update_admin_level(user_id, new_admin_level)
    return redirect(url_for('collab.index'))