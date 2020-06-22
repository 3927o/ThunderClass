import os
from flask import Flask

from settings import config
from app.extensions import db_sql, socketio
from app.blueprints import auth_bp, user_bp, course_bp, test_bp, task_bp, avatar_bp


def create_app(config_name=None, **options):
    if config_name is None:
        config_name = os.getenv("FLASK_CONFIG", 'testing')

    app = Flask(__name__, **options)
    app.config.from_object(config[config_name])

    register_blueprints(app)
    register_extensions(app)

    return app


def register_blueprints(app):
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(user_bp, url_prefix='/api/user')
    app.register_blueprint(course_bp, url_prefix='/api/course')
    app.register_blueprint(test_bp, url_prefix='/api/test')
    app.register_blueprint(task_bp, url_prefix='/api/task')
    app.register_blueprint(avatar_bp, url_prefix='/api/avatars')


def register_extensions(app):
    db_sql.init_app(app)
    socketio.init_app(app)
