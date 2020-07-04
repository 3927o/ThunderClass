from flask import Blueprint, redirect, g, request
from flask_restful import Api, Resource
from flask_cors import CORS

from app.blueprints.auth import auth_required, resource_found_required
from app.modules import Media
from app.extensions import db_sql as db
from app.utils import api_abort


def create_avatar_bp(name="avatar_bp"):
    avatar_bp = Blueprint(name, __name__)
    api_avatar = Api(avatar_bp)
    CORS(avatar_bp)

    api_avatar.add_resource(UserAvatarAPI, '/user/<int:uid>', endpoint='user')
    api_avatar.add_resource(CourseAvatarAPI, '/course/<int:cid>', endpoint='course')

    return avatar_bp


# def set_user_avatar(uid):
#     # url: '/user/<int:uid>'
#     pass


class UserAvatarAPI(Resource):
    # url: avatars/user/<int:uid>
    method_decorators = {"get": [resource_found_required('user')],
                         "post": [auth_required, resource_found_required("user")]}

    def get(self, uid):
        print(g.current_user.avatar)
        url = Media.load_media_from_uuid(g.current_user.avatar, return_model=True).url
        return redirect(url)

    def post(self, uid):
        if not g.current_user.id == uid:
            return api_abort(403, "permission denied")

        old_media = Media.load_media_from_uuid(g.current_user.avatar, return_model=True)
        new_media = request.files.get("avatar")
        if new_media is None:
            return api_abort(400, "file missing")
        new_media_uuid = Media.save_media(new_media, "avatars/user", commit=False)
        old_media.delete() if old_media is not None else 1
        g.current_user.avatar = new_media_uuid
        db.session.commit()
        return "OK"


class CourseAvatarAPI(Resource):
    # url: avatars/course/<int:cid>
    method_decorators = {"get": [resource_found_required('course')],
                         "post": [auth_required, resource_found_required("course")]}

    def get(self, cid):
        url = Media.load_media_from_uuid(g.current_course.avatar, return_model=True).url
        return redirect(url)

    def post(self, cid):
        if not g.current_user.is_teacher(g.current_course):
            return api_abort(403, "permission denied")

        old_media = Media.load_media_from_uuid(g.current_course.avatar, return_model=True)
        new_media = request.files.get("avatar")
        if new_media is None:
            return api_abort(400, "file missing")
        new_media_uuid = Media.save_media(new_media, "avatars/course", commit=False)
        old_media.delete() if old_media is not None else 1
        g.current_course.avatar = new_media_uuid
        db.session.commit()
        return "OK"