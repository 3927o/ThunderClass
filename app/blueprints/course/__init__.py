from flask_restful import Api
from flask import Blueprint
from flask_cors import CORS

from .resources import CourseAPI, CourseListAPI, JoinCourseAPI, ImportStuAPI, TaskListAPI, GetStudentsAPI, \
    ChapterListAPI, DocumentUploadAPI, DocumentListAPI, MovieUploadAPI, MovieListAPI, DiscussionAPI, \
    DiscussionListAPI, CommentLikeAPI, CommitAPI, CommitStatisticsAPI, CommentAPI, NoticeAPI, NoticeListAPI, \
    DiscussionRecommendAPI, CourseRecommendAPI, MediaAPI,  ReplyAPI, JoinStatusAPI
from .message_socketio import send_message, join_room_, leave_room_


def create_course_bp(name='course_bp'):
    course_bp = Blueprint(name, __name__)

    register_extensions(course_bp)

    return course_bp


def register_extensions(app):
    CORS(app)
    create_api().init_app(app)


def create_api():
    api_course = Api()

    api_course.add_resource(CourseAPI, "/<int:cid>", endpoint="course")
    api_course.add_resource(CourseListAPI, "/course_list", endpoint="courses")
    api_course.add_resource(JoinCourseAPI, '/<int:cid>/join/', endpoint='join_course')
    api_course.add_resource(ImportStuAPI, '/<int:cid>/students/import', endpoint='import_course')
    api_course.add_resource(TaskListAPI, '/<int:cid>/tasks', endpoint='tasks')
    api_course.add_resource(GetStudentsAPI, '/<int:cid>/students', endpoint='students')
    api_course.add_resource(ChapterListAPI, '/<int:cid>/chapters')
    api_course.add_resource(DocumentUploadAPI, '/<int:cid>/documents/upload')
    api_course.add_resource(DocumentListAPI, '/<int:cid>/documents')
    api_course.add_resource(MovieUploadAPI, '/<int:cid>/movies/upload')
    api_course.add_resource(MovieListAPI, '/<int:cid>/movies')
    api_course.add_resource(DiscussionAPI, '/<int:cid>/discussions/<string:discus_id>')
    api_course.add_resource(DiscussionListAPI, '/<int:cid>/discussions/')
    api_course.add_resource(CommentLikeAPI, '/<int:cid>/comments/<string:comment_id>/like')
    api_course.add_resource(CommitAPI, "/<int:cid>/commit")
    api_course.add_resource(CommitStatisticsAPI, "/<int:cid>/commit/statistics")
    api_course.add_resource(CommentAPI, '/discussions/<string:discus_id>/comments', endpoint="comments")
    api_course.add_resource(NoticeAPI, '/<int:cid>/notices/<string:notice_id>', endpoint='notice')
    api_course.add_resource(NoticeListAPI, '/<int:cid>/notices')
    api_course.add_resource(DiscussionRecommendAPI, '/discussions/recommend')
    api_course.add_resource(CourseRecommendAPI, '/recommend')
    api_course.add_resource(MediaAPI, '/media/<string:media_id>')
    api_course.add_resource(ReplyAPI, '/comment/<string:comment_id>/replies')
    api_course.add_resource(JoinStatusAPI, '/<int:cid>/join/status')

    return api_course