import redis
import pickle
from time import time

from flask import g, request
from flask_restful import Resource

from app.extensions import db_sql as db
from app.extensions import pool
from app.modules import User, Course, Task
from app.blueprints.auth import auth_required, resource_found_required
from app.blueprints.auth.utils import validate_verify_code
from app.utils import edit_module, make_resp, api_abort

from .reqparsers import user_put_reqparser, user_del_reqparser, user_create_reqparser, stu_certificate_reqparser


secure_info_map = {'telephone': "changeTel", 'password': "changePassword"}

r = redis.Redis(connection_pool=pool)


class UserAPI(Resource):
    # url: /user/<int:uid>
    method_decorators = [resource_found_required('user')]

    def get(self, uid):
        return make_resp(g.current_user.to_json(detail=False))


class CurrentUserAPI(Resource):
    # url: /user/current
    method_decorators = {"get": [auth_required], "put": [auth_required], 'delete': [auth_required]}

    def get(self):
        return make_resp(g.current_user.to_json(detail=True))

    def post(self):
        data = user_create_reqparser.parse_args()
        if not validate_verify_code(data['telephone'], 'signup', data['code']):
            return api_abort(401, 'wrong verify code')
        user = User(data['nickname'], data['telephone'], data['password'])
        db.session.add(user)
        db.session.commit()
        return make_resp(user.to_json(detail=True))

    def put(self):
        base_info = ['nickname', 'gender', 'introduce']
        data = user_put_reqparser.parse_args()
        for info in base_info:
            if data[info] is not None:
                setattr(g.current_user, info, data[info])

        for info in secure_info_map:
            if data[info] is not None:
                if not validate_and_change_info(info, data[info], data["code_"+secure_info_map[info]]):
                    return api_abort(400, "wrong code")

        db.session.commit()
        return make_resp(g.current_user.to_json(detail=True))

    def delete(self):
        code = user_del_reqparser.parse_args()['code']
        if validate_verify_code(g.current_user.telephone, 'delAccount', code):
            db.session.delete(g.current_user)
        else:
            return api_abort(401, 'wrong code')
        db.session.commit()
        return make_resp({})


class CourseListAPI(Resource):
    # url: user/current/courses?public=[0,1]
    method_decorators = [auth_required]

    def get(self):
        courses = g.current_user.courses
        public = request.args.get("public")
        if public is not None:
            public = int(public)
            course_list = []
            for course in courses:
                if course.public == public:
                    course_list.append(course)
            courses = course_list
        return make_resp(Course.list_to_json(courses))


class TaskListAPI(Resource):
    # url: /current/tasks
    method_decorators = [auth_required]

    def get(self):
        student = g.current_user
        tasks = student.tasks
        time_now = time()
        time_latest = time_now - 3600 * 24 * 7
        task_list = []
        for task in tasks:
            if task.create_at > time_latest:
                task_list.append(task)
        return make_resp(Task.list_to_json(task_list, g.current_user))


class StuCertificateAPI(Resource):
    # url: /user/certificate
    method_decorators = [auth_required]

    def post(self):
        data = stu_certificate_reqparser.parse_args()
        school = data['school']
        student_id = data['student_id']
        code = data['certificate_code']
        data_string = r.get((school + ":" + student_id))
        if data_string is None:
            return api_abort(401, "certificate info not exist")
        data = pickle.loads(data_string)
        print(data)
        if not data['certificate_code'] == code:
            print(str(data['certificate_code']))
            return api_abort(403, 'wrong certificate code')
        user = g.current_user
        courses = data['courses']
        data.pop('courses')
        data.pop("certificate_code")
        edit_module(user, data)
        for cid in courses:
            course = Course.query.get(cid)
            if not user.is_teacher(course):
                user.courses.append(course)
        db.session.commit()
        return make_resp(user.to_json(detail=True))


class TeacherCoursesAPI(Resource):
    # url: /teacher/current/courses
    method_decorators = [auth_required]

    def get(self):
        courses = Course.query.filter_by(teacher_id=g.current_user.id).all()
        return make_resp(Course.list_to_json(courses))


class TeacherTaskAPI(Resource):
    # url: /user/teacher/tasks
    method_decorators = [auth_required]

    def get(self):
        courses = Course.query.filter_by(teacher_id=g.current_user.id).all()
        task_list = []
        for course in courses:
            tasks = course.tasks
            for task in tasks:
                task_list.append(task)

        data = Task.list_to_json(task_list, g.current_user)
        return make_resp(data)


def validate_and_change_info(info_name, new_info, code):
    if validate_verify_code(g.current_user.telephone, secure_info_map[info_name], code):
        if info_name is "password":
            g.curret_user.set_password(new_info)
        else:
            setattr(g.current_user, info_name, new_info)
        return True
    else:
        return False


def validate_certificate_code(school, student_id, code):
    certificate_data = pickle.loads(r.get((school + ":" + student_id)))
    real_code = certificate_data['certificate_code']
    return real_code == code