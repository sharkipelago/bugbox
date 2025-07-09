import functools
from flask import g, redirect, url_for

from bugbox.db import get_issue_teams

def issue_team_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        team_ids = get_issue_teams(kwargs.get('issue_id'))
        assert isinstance(team_ids, int) or isinstance(team_ids, set)
        # Allows to pass in a single team_id or multiple ids as a set
        if not isinstance(team_ids, set):
            team_ids = set(team_ids) 
        if g.user['admin_level'] != 2 and g.user["team_id"] not in team_ids:
            return redirect(url_for('admin.denied'))

        return view(**kwargs)

    return wrapped_view