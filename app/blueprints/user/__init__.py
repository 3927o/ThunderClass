from flask import Blueprint
from flask_restful import Api
from flask_cors import CORS

from .resources import UserAPI, CurrentUserAPI, StuCertificateAPI, TaskListAPI, CourseListAPI, TeacherCoursesAPI


def create_user_bp(name='user_bp'):
    user_bp = Blueprint(name, __name__)
    api_user = Api(user_bp)
    CORS(user_bp)

    api_user.add_resource(UserAPI, '/<int:uid>', endpoint='user')
    api_user.add_resource(CurrentUserAPI, '/current', endpoint='current_user')
    api_user.add_resource(StuCertificateAPI, '/certificate', endpoint='certificate')
    api_user.add_resource(TaskListAPI, '/current/tasks', endpoint='tasks')
    api_user.add_resource(CourseListAPI, '/current/courses', endpoint='courses')
    api_user.add_resource(TeacherCoursesAPI, '/teacher/current/courses')

    return user_bp