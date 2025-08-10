import os
from flask import Flask, render_template
from flask_bootstrap import Bootstrap5

# TODO update teams to grab from data
from bugbox.team import TEAMS, TEAM_IDS
from bugbox.db import get_user, get_all_issues

def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'bugbox.sqlite'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    # pass teams object to every template
    def inject_data():
        return dict(TEAMS=TEAMS, TEAM_IDS=TEAM_IDS, get_user=get_user, all_issues=get_all_issues)
    app.context_processor(inject_data)


    app.config["BOOTSTRAP_BOOTSWATCH_THEME"] = 'sandstone' #https://bootswatch.com/
    Bootstrap5(app) # adds boostrap object https://bootstrap-flask.readthedocs.io/en/stable/basic/

    def handle_404_request(e):
        return render_template('error/404.html')

    app.register_error_handler(404, handle_404_request)

    from . import db
    db.init_app(app)

    from . import auth
    app.register_blueprint(auth.bp)

    from . import issue
    app.register_blueprint(issue.bp)
    app.add_url_rule('/', endpoint='index')
    
    from . import collab
    app.register_blueprint(collab.bp)

    from . import about
    app.register_blueprint(about.bp)

    return app