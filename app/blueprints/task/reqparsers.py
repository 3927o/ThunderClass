from flask import request
from flask_restful.reqparse import RequestParser


answer_submit_reqparser = RequestParser()
answer_submit_reqparser.add_argument('answers', type=str, required=True)

check_answer_reqparser = RequestParser()
check_answer_reqparser.add_argument('check_res', type=str, required=True, location='json')