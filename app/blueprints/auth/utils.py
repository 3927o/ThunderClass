import random
import redis
import pickle
from itsdangerous import TimedJSONWebSignatureSerializer as Serializer, BadSignature, SignatureExpired

from flask import current_app

from app.modules import User
from app.extensions import pool


r = redis.Redis(connection_pool=pool)


def send_message(tel, template_parm, template_code):
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    client = AcsClient('<>', '<>', '<>')

    request = CommonRequest()
    request.set_accept_format('json')
    request.set_domain('dysmsapi.aliyuncs.com')
    request.set_method('POST')
    request.set_protocol_type('https')
    request.set_version('2017-05-25')
    request.set_action_name('SendSms')

    request.add_query_param('RegionId', "cn-hangzhou")
    request.add_query_param('PhoneNumbers', str(tel))
    request.add_query_param('SignName', "狂野男孩聊天室")
    request.add_query_param('TemplateCode', template_code)
    request.add_query_param('TemplateParam', str(template_parm))

    response = client.do_action_with_exception(request)
    print(str(response, encoding='utf-8'))

    return 1


def send_verify_code(tel, code=None):

    if code is None:
        code = random.randint(100001, 999999)

    status = send_message(tel, {"code": code}, current_app.config['TEMPLATE_CODE']['verify'])

    return code


def send_notice(user, notice):

    template_param = {
        "name": user.name,
        "course": notice.course.name,
        "content": str(notice.title)
    }

    status = send_message(user.telephone, template_param, current_app.config['TEMPLATE_CODE']['notice'])

    return status


def get_user_by_name_or_tel(name_or_tel):
    user = User.query.filter_by(nickname=name_or_tel).first()
    if user is None:
        user = User.query.filter_by(telephone=name_or_tel).first()

    return user


def validate_verify_code(tel, code_type, code):
    key = code_type + ':' + tel
    real_code = r.get(key)
    real_code = real_code.decode("utf-8") if real_code is not None else None
    return real_code == code


def generate_token(user, token_type, expires=3600 * 24 * 7, json_user=False):
    # generate token with user's info
    s = Serializer(current_app.secret_key, expires_in=expires)
    if json_user:
        data = user
    else:
        data = user.to_json(detail=True)
    token = s.dumps(data).decode('ascii')

    key = "token" + ':' + token_type
    r.sadd(key, token)

    return token


def load_user(token):
    # read user's info from token
    # return: dict
    s = Serializer(current_app.secret_key)
    try:
        user_data = s.loads(token)
    except (BadSignature, SignatureExpired):
        return None

    # uid = token.split('.')[0]
    # try:
    #     user_data = pickle.loads(r.get("user:"+uid))
    # except TypeError:
    #     return None

    uid = user_data['uid']
    user = User.query.get(uid)

    return user