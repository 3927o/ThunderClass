from flask import jsonify
from werkzeug.http import HTTP_STATUS_CODES


def api_abort(code, message=None, **kwargs):
    if message is None:
        message = HTTP_STATUS_CODES.get(code, '')

    response = jsonify(status=code, message=message, **kwargs)
    response.status_code = code
    return response