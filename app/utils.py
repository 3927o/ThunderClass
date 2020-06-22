import time
from hashlib import md5
from flask import jsonify, current_app
from werkzeug.http import HTTP_STATUS_CODES


def guess_type(url):
    media_type = None

    types = ['picture', 'video', 'audio', 'word', 'excel', 'ppt', 'pdf', 'python', 'cpp']
    picture = ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'ico']
    video = ['mp4', 'mkv', 'avi', 'mov', 'flv', 'wmv']
    audio = ['mp3', 'wma', 'ape', 'flac']
    word = ['doc', 'docx', 'docm', 'dotx', 'dotm']
    excel = ['xls', 'xlsx', 'xlsm', 'xltx', 'xltm', 'xlsb', 'xlam']
    ppt = ['ppt', 'pptx', 'pptm', 'ppsx', 'ppsm', 'potx', 'potm', 'ppam']
    pdf = ['pdf']
    python = ['py']
    cpp = ['cpp', 'c']

    d = dict()
    for type_ in types:
        d[type_] = eval(type_)

    postfix = url.split('.')[-1].lower()
    for k, v in d.items():
        if postfix in v:
            media_type = k
            break

    if media_type is None:
        raise RuntimeError("unsupported type or missing postfix")

    return media_type


def edit_module(module, data):
    for k in data:
        if data[k] is not None:
            setattr(module, k, data[k])


def api_abort(code, message=None, **kwargs):
    if message is None:
        message = HTTP_STATUS_CODES.get(code, '')

    response = jsonify(status=code, message=message, **kwargs)
    response.status_code = code
    return response


def make_resp(data, status=200, message='succeed'):
    resp = jsonify({
        'status': status,
        'message': message,
        'data': data
    })
    resp.status_code = status
    return resp


def format_time(ts):
    return time.strftime("%Y/%m/%d %X", time.localtime(ts))


def strptime(str_time):
    return time.mktime(time.strptime(str_time, "%Y/%m/%d %X"))


def push_url_builder(stream_name, time, key="1b74cb987121964596c61e9176ba1e72", domain="rtmp://102433.livepush.myqcloud.com/live/"):
    txTime = hex(int(strptime(time)))[2:].upper()
    txSecret = md5((key+stream_name+txTime).encode("utf-8")).hexdigest()
    stream = "{}?txSecret={}&txTime={}".format(stream_name, txSecret, txTime)
    return domain + stream