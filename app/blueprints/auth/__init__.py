import redis

from flask_restful import Api
from flask import Blueprint, request, g
from flask_cors import CORS

from app.extensions import pool
from app.errors import api_abort
from app.modules import User, Discussion, Course, Task, Problem, TaskAnswer, Chapter, Comment, Notice, Media

from .utils import generate_token, load_user
from .resources import CheckNameExitAPI, CheckTelExitAPI, VerifyCodeAPI, LoginAuthAPI


access_token_expires = 3600*24*7
refresh_token_expires = 3600*24*30
key_access_token = "token:access"
key_refresh_token = "token:refresh"


def create_auth_bp(name='auth_bp'):
    auth_bp = Blueprint(name, __name__)
    api_auth = Api(auth_bp)
    CORS(auth_bp)

    api_auth.add_resource(CheckTelExitAPI, '/check/telephone')
    api_auth.add_resource(CheckNameExitAPI, '/check/nickname')
    api_auth.add_resource(VerifyCodeAPI, '/sms')
    api_auth.add_resource(LoginAuthAPI, '/login')

    return auth_bp


def auth_required(f):

    def decorator(*args, **kws):
        r = redis.Redis(connection_pool=pool)
        token = request.headers.get('Authorization', None)
        if token is None:
            return api_abort(403, 'token missing')
        try:
            access_token = token.split(';')[0]
            refresh_token = token.split(';')[1]
        except IndexError:
            access_token = token.split(';')[0]
            refresh_token = ""

        if r.sismember(key_access_token, access_token):
            user = load_user(access_token)
            if user is None:
                return api_abort(403, 'bad token')
            g.current_user = user
            return f(*args,  **kws)

        if r.sismember(key_refresh_token, refresh_token):
            user = load_user(refresh_token)
            if user is None:
                return api_abort(403, 'bad token')

            r.srem(key_refresh_token, refresh_token)
            access_token = generate_token(user, 'access', access_token_expires)
            refresh_token = generate_token(user, 'refresh', refresh_token_expires)
            token_info = {"access_token": access_token,
                          "refresh_token": refresh_token,
                          "expires_access": access_token_expires,
                          "expires_refresh": refresh_token_expires}

            g.current_user = user
            resp = f(*args, **kws)
            resp['token'] = token_info
            return resp

        return api_abort(403, 'bad token')

    return decorator


def find_resource_id(id_name):
    resource_id = request.view_args.get(id_name, None)
    if resource_id is None:
        resource_id = request.args.get(id_name, None)
    return resource_id


def resource_found_required(resource_name):
    def wrapper(f):
        def decorator(*args, **kws):
            resource_name_module_map = {"user": User, "course": Course, "task": Task, "discussion": Discussion,
                                        "chapter": Chapter, "problem": Problem, "task_answer": TaskAnswer,
                                        "comment": Comment, "notice": Notice, "media": Media}
            module = resource_name_module_map[resource_name]
            resource_id = find_resource_id(module.id_name)
            if resource_id is None:
                return api_abort(400, "{} id is required".format(resource_name))
            resource = module.query.get(resource_id)
            if resource is None:
                return api_abort(404, "resource {} not found".format(resource_name))
            setattr(g, "current_"+resource_name, resource)
            return f(*args, **kws)
        return decorator
    return wrapper


def get_course_allowed(f):
    def decorator(*args, **kws):
        user = g.current_user
        course = g.current_course
        if user not in course.students and not user.is_teacher(course):
            return api_abort(403, "not the student ot teacher")
        return f(*args, **kws)
    return decorator
