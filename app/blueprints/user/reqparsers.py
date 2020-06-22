from flask_restful.reqparse import RequestParser

user_put_reqparser = RequestParser()
user_put_reqparser.add_argument('nickname', type=str, location='json')
user_put_reqparser.add_argument('introduce', type=str, location='json')
user_put_reqparser.add_argument('gender', choices=('male', 'female', 'secret'), type=str, location='json')
user_put_reqparser.add_argument('telephone', type=str, location='json')
user_put_reqparser.add_argument('code_changeTel', type=str, location='json')
user_put_reqparser.add_argument('password', type=str, location='json')
user_put_reqparser.add_argument('code_changePassword', type=str, location='json')

user_del_reqparser = RequestParser()
user_del_reqparser.add_argument('code', type=str, location='json')

user_create_reqparser = RequestParser()
user_create_reqparser.add_argument('nickname', required=True, type=str, location='json')
user_create_reqparser.add_argument('telephone', required=True, type=str, location='json')
user_create_reqparser.add_argument('password', required=True, type=str, location='json')
user_create_reqparser.add_argument('code', required=True, type=str, location='json')

stu_certificate_reqparser = RequestParser()
stu_certificate_reqparser.add_argument('school', required=True, type=str, location='json')
stu_certificate_reqparser.add_argument('student_id', required=True, type=str, location='json')
stu_certificate_reqparser.add_argument('certificate_code', required=True, type=str, location='json')