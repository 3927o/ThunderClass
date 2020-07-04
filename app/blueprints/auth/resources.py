import redis
from flask import request, current_app, g
from flask_restful import Resource

from app.errors import api_abort
from app.extensions import pool
from app.schemas import make_resp
from app.modules import User

from .utils import send_verify_code, get_user_by_name_or_tel, validate_verify_code, generate_token
from .reqparsers import code_send_reqparser, pwd_login_reqparser, tel_login_reqparser, login_reqparser

r = redis.Redis(connection_pool=pool)


class LoginAuthAPI(Resource):
    # url: /login?method=[0, 1]
    def post(self):
        reqparser = [pwd_login_reqparser, tel_login_reqparser]
        auth_user_funcs = [auth_user_by_pwd, auth_user_by_phone]

        data = login_reqparser.parse_args()
        method = data['method']

        data = reqparser[int(method)].parse_args()
        user, message = auth_user_funcs[int(method)](data)
        g.current_user = user

        if message is not 'succeed' or user is None:
            return api_abort(401, message)

        access_token = generate_token(user, 'access', 3600*24*7)
        refresh_token = generate_token(user, 'refresh', 3600*24*30)

        return make_resp({'user_info': user.to_json(detail=True),
                          'access_token': access_token,
                          'refresh_token': refresh_token,
                          'access_expires': 3600*24*7,
                          'refresh_expires': 3600*24*30})


class VerifyCodeAPI(Resource):
    # url: /sms
    def post(self):
        code_type = current_app.config['CODE_TYPE']
        data = code_send_reqparser.parse_args()
        action = code_type[data['type']]
        tel = data['tel']

        key = action + ':' + tel
        code = r.get(key)
        code = send_verify_code(tel, code)

        r.set(key, code, ex=60*5, nx=True)

        return make_resp({})


class CheckNameExitAPI(Resource):
    # url: /check/nickname?nickname={{name}}
    def get(self):
        nickname = request.args.get('nickname')
        if nickname is None:
            return api_abort(400, "param nickname missing")
        user = User.query.filter_by(nickname=nickname).first()
        if user is None:
            exit_status = 0
        else:
            exit_status = 1
        return {"status": int(exit_status)}


class CheckTelExitAPI(Resource):
    # url: /check/telephone?tel={{tel}}
    def get(self):
        tel = request.args.get('tel')
        if tel is None:
            return api_abort(400, "param tel missing")
        user = User.query.filter_by(telephone=tel).first()
        if user is None:
            exit_status = 0
        else:
            exit_status = 1
        return {"status": int(exit_status)}


class TokenAuthAPI(Resource):
    # url: /auth/token
    def get(self):
        token = request.headers.get('Authorization', None)
        if token is None:
            return api_abort(403, 'token missing')
        try:
            access_token = token.split(';')[0]
            refresh_token = token.split(';')[1]
        except IndexError:
            access_token = token.split(';')[0]
            refresh_token = ""

        if r.sismember("token:access", access_token):
            return make_resp("", message="OK")
        else:
            return make_resp("", message="Bad Token")


def auth_user_by_pwd(data):
    username_or_tel = data['username']
    pwd = data['password']
    message = 'succeed'

    user = get_user_by_name_or_tel(username_or_tel)

    if user is None:
        message = 'user do not exist'

    if user is not None and not user.validate_password(pwd):
        message = "wrong password"

    return user, message


def auth_user_by_phone(data):
    tel = data['tel']
    verify_code = data['code']
    message = 'succeed'

    user = User.query.filter_by(telephone=tel).first()

    if user is None:
        message = 'user do not exit'

    if not validate_verify_code(tel, 'login', verify_code):
        message = 'wrong verify code'

    return user, message