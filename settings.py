import os
import sys

basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# SQLite URI compatible
WIN = sys.platform.startswith('win')
if WIN:
    prefix = 'sqlite:///'
else:
    prefix = 'sqlite:////'


class BaseConfig:

    SECRET_KEY = os.getenv('SECRET_KEY', 'secret_key')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', prefix + os.path.join(basedir, 'data.db'))
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    MONGO_DBNAME = 'tasks'
    MONGO_URI = 'mongodb://127.0.0.1:27017'

    CODE_TYPE = ['signup', 'login', 'changeTel', 'changePassword', 'delAccount']
    SELECT_TYPE = ['select', 'mselect', 'judge']
    TEMPLATE_CODE = {"verify": "SMS_186947418", "notice": "SMS_186947418"}


class DevelopmentConfig(BaseConfig):
    pass


class ProductionConfig(BaseConfig):
    pass


class TestingConfig(BaseConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///'
    # SQLALCHEMY_DATABASE_URI = 'mysql://root:123456@127.0.0.1/test'
    WTF_CSRF_ENABLED = False


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig
}