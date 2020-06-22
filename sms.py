import random
from redis import Redis

from flask import Flask, request


app = Flask(__name__)

r = Redis()


def send_message(tel, code=None):
    from aliyunsdkcore.client import AcsClient
    from aliyunsdkcore.request import CommonRequest
    client = AcsClient('LTAI4GCfPeu4kevrKwSMynRY', 'GHSBMqJdQu7n89I9Mn1puKia9UVv43', 'cn-hangzhou')

    if code is None:
        code = random.randint(100001, 999999)

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
    request.add_query_param('TemplateCode', "SMS_186947418")
    request.add_query_param('TemplateParam', str({'code': code}))

    response = client.do_action_with_exception(request)
    # response = client.do_action(request)
    response = eval(response)
    if response['Code'] != "OK":
        raise TypeError(response)

    return code


@app.route('/thunderclass', methods=['POST'])
def thunderclass():
    code_type = ['signup', 'login', 'changeTel', 'changePassword', 'delAccount']
    type_ = request.args.get("type")
    tel = request.args.get("tel")
    if tel is None:
        return {"message": "param missing"}
    type_ = int(type_)
    action = code_type[type_]

    key = action + ':' + tel
    code = r.get(key)
    code = send_message(tel, code)

    r.set(key, code, ex=60 * 5, nx=True)

    return "OK"


app.run(debug=True)