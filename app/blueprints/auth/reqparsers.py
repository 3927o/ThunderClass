from flask_restful.reqparse import RequestParser


code_send_reqparser = RequestParser()
code_send_reqparser.add_argument('type', type=int, required=True)
code_send_reqparser.add_argument('tel', type=str, required=True)

login_reqparser = RequestParser()
login_reqparser.add_argument('method', type=int, required=True)

tel_login_reqparser = RequestParser()
tel_login_reqparser.add_argument('tel', type=str, required=True)
tel_login_reqparser.add_argument('code', type=str, required=True)

pwd_login_reqparser = RequestParser()
pwd_login_reqparser.add_argument('username', type=str, required=True)
pwd_login_reqparser.add_argument('password', type=str, required=True)