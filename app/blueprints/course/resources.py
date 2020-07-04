from time import time
import pickle
import redis
from flask import request, g, url_for, json
from flask_restful import Resource

from app.extensions import db_sql as db, pool
from app.modules import Course, User, Media, Task, Problem, Chapter, Discussion, Comment, create_commit, Notice
from app.blueprints.auth import auth_required, resource_found_required, get_course_allowed
from app.blueprints.auth.utils import send_notice
from app.utils import edit_module, api_abort, make_resp, strptime

from .reqparsers import course_create_reqparser, course_put_reqparser, commit_create_reqparser, notice_create_reqparser,\
    task_create_reqparser, prob_parser, upload_reqparser, discussion_reqparser, comment_reqparser
from .utils import parse_excel


r = redis.Redis(connection_pool=pool)


def teacher_required(f):
    def decorator(cid):
        if not g.current_user.is_teacher(g.current_course):
            return api_abort(403, 'not the teacher')
        return f(cid)
    return decorator


class CourseAPI(Resource):
    # url: /<int:id>
    method_decorators = {"get": [resource_found_required('course'), auth_required],
                         "put": [teacher_required, auth_required, resource_found_required('course')],
                         "delete": [teacher_required, auth_required, resource_found_required('course')]}

    def get(self, cid):
        return make_resp(g.current_course.to_json(detail=True))

    def put(self, cid):
        course = g.current_course
        data = course_put_reqparser.parse_args()
        edit_module(course, data)
        db.session.commit()
        return course.to_json(detail=True)

    def delete(self, cid):
        course = g.current_course
        data = course.to_json(detail=True)
        db.session.delete(course)
        db.session.commit()
        return make_resp(data)


class CourseListAPI(Resource):
    # url: /course_list?teacher_id=<int:uid>
    method_decorators = [auth_required]

    def get(self):
        courses = Course.query.filter_by(public=True)
        teacher_id = request.args.get('teacher_id', None)
        if teacher_id is not None:
            courses = courses.filter_by(teacher_id=teacher_id)
        courses = courses.all()
        data = Course.list_to_json(courses)
        return make_resp(data)

    def post(self):
        data = course_create_reqparser.parse_args()
        new_course = Course(data['name'], data['public'], g.current_user.id,
                            data['start_at'], data['end_at'], data['introduce'])

        new_media = request.files.get("avatar")
        if new_media is None:
            return api_abort(400, "file missing")
        new_media_uuid = Media.save_media(new_media, "avatars/course", commit=False)
        new_course.avatar = new_media_uuid

        db.session.add(new_course)
        db.session.commit()
        return make_resp(new_course.to_json(detail=True))


class TaskListAPI(Resource):
    # url: /<int:cid>/tasks/?per_page=&page=&type="exam"/"test"

    method_decorators = {"get": [get_course_allowed, auth_required, resource_found_required('course')],
                         "post": [teacher_required, auth_required, resource_found_required('course')]}

    def get(self, cid):
        # course = g.current_course
        # return make_resp(Task.list_to_json(course.tasks, g.current_user))
        task_query = Task.query.filter_by(course_id=cid)
        task_type = request.args.get("type")
        if task_type is not None:
            task_query = task_query.filter_by(type=task_type)

        per_page = int(request.args.get("per_page", 20))
        page = int(request.args.get("page", 1))
        tasks_pagination = task_query.paginate(page, per_page=per_page, error_out=False)
        data = Task.page_to_json(tasks_pagination, g.current_user, cid)
        return make_resp(data)

    def post(self, cid):
        course = g.current_course
        data = task_create_reqparser.parse_args()
        new_task = Task(data['type'], data['name'], data['t_begin'], data['t_end'],
                        int(data['ans_visible']), data['introduce'], data['expires'])
        probs = eval(data['problems'])
        prob_list = []
        for v in probs.values():
            prob_list.append(v)
        prob_order_set = set()
        for prob in prob_list:
            prob = prob_parser(prob)

            if not prob:
                return api_abort(400, 'bad prob param')
            if prob['order'] in prob_order_set:
                return api_abort(400, 'duplicate of order')
            prob_order_set.add(prob['order'])

            new_prob = create_prob(prob)
            new_task.problems.append(new_prob)
        new_task.judge_max_score()
        [new_task.students.append(student) for student in course.students]
        r.sadd("task_finished:"+str(new_task.id), g.current_user.id)
        course.tasks.append(new_task)
        db.session.commit()
        resp = new_task.to_json(g.current_user, detail=True)
        return make_resp(resp)


class GetStudentsAPI(Resource):
    # url: /<int:cid>/students
    method_decorators = [resource_found_required('course')]

    def get(self, cid):
        students = g.current_course.students
        page = request.args.get("page", 1)
        per_page = request.args.get("per_page", 20)
        students = students[(page-1)*per_page:page*per_page]
        data = User.list_to_json(students)
        return make_resp(data)


class JoinCourseAPI(Resource):
    # url: /join/<int:cid>
    method_decorators = [auth_required, resource_found_required('course')]

    def post(self, cid):
        course = g.current_course
        user = g.current_user
        if course in user.courses:
            return api_abort(400, "you already in the course")
        if user.is_teacher(course):
            return api_abort(403, "you are the teacher!")
        if not course.public:
            return api_abort(403, "can only join the public course")
        course.students.append(user)
        db.session.commit()
        return make_resp(course.to_json())


class JoinStatusAPI(Resource):
    # url: /<int:cid>/join/status
    method_decorators = [auth_required, resource_found_required('course')]

    def get(self, cid):
        status = 1 if g.current_user in g.current_course.students else 0
        return make_resp(status)


class ImportStuAPI(Resource):
    # url: course/<int:cid>/students/import
    method_decorators = [teacher_required, auth_required, resource_found_required('course')]

    def post(self, cid):
        course = g.current_course
        data = parse_excel(request, 'excel_file')  # it's a list
        for item in data:
            item = deal_import_data(item)
            user = User.query.filter_by(school=item['school'], student_id=item['student_id']).first()
            if user is None:
                key = item['school'] + ":" + item['student_id']
                item['courses'].append(course.id)
                r.set(key, pickle.dumps(item))
            else:
                user.courses.append(course)
                user.name = item['name']
                db.session.commit()
        return make_resp(course.to_json(detail=True))


class ChapterListAPI(Resource):
    # url: /course/<int:cid>/chapters
    method_decorators = [resource_found_required('course'), auth_required]

    def get(self, cid):
        chapters = g.current_course.chapters
        return make_resp(Chapter.list_to_json(chapters))


class MediaAPI(Resource):
    # url: /course/media/<string:media_id>
    method_decorators = [resource_found_required("media")]

    def get(self, media_id):
        media = g.current_media
        return make_resp(media.to_json())


class DocumentUploadAPI(Resource):
    # url: /course/<int:cid>/documents/upload
    method_decorators = [teacher_required, auth_required, resource_found_required('course')]

    def post(self, cid):
        # expected str chapter and file document, if chapter not exist, create it.
        data = upload_reqparser.parse_args()
        chapter_name = data['chapter']
        name = data['name']
        chapter = Chapter.query.filter_by(name=chapter_name, course_id=g.current_course.id).first()
        if chapter is None:
            chapter = Chapter(chapter_name)
            chapter.course = g.current_course
            db.session.add(chapter)

        course = g.current_course
        document = request.files.get('document')
        if document is None:
            return api_abort(400, "document is None")

        new_media_uuid = Media.save_media(document, 'course/{}/documents'.format(course.id), name=name)
        media_uuid_list = pickle.loads(chapter.documents)
        media_uuid_list.append(new_media_uuid)
        chapter.documents = pickle.dumps(media_uuid_list)
        db.session.commit()
        return make_resp(chapter.to_json(with_documents=True))


class MovieUploadAPI(Resource):
    method_decorators = [teacher_required, auth_required, resource_found_required('course')]

    def post(self, cid):
        # expected str chapter and file document, if chapter not exist, create it.
        data = upload_reqparser.parse_args()
        chapter_name = data['chapter']
        name = data['name']
        chapter = Chapter.query.filter_by(name=chapter_name, course_id=g.current_course.id).first()
        if chapter is None:
            chapter = Chapter(chapter_name)
            chapter.course = g.current_course
            db.session.add(chapter)

        course = g.current_course
        movie = request.files.get('movie')
        if movie is None:
            return api_abort(400, "movie is None")

        new_media_uuid = Media.save_media(movie, 'course/{}/movie'.format(course.id), name=name)
        media_uuid_list = pickle.loads(chapter.movies)
        media_uuid_list.append(new_media_uuid)
        chapter.movies = pickle.dumps(media_uuid_list)
        db.session.commit()
        return make_resp(chapter.to_json(with_movies=True))


class DocumentListAPI(Resource):
    # url: /course/<int:cid>/documents
    method_decorators = [resource_found_required('course')]

    def get(self, cid):
        course = g.current_course
        chapters = course.chapters
        data = Chapter.list_to_json(chapters, with_documents=True)
        return make_resp(data)


class MovieListAPI(Resource):
    # url: /course/<int:cid>/movies
    method_decorators = [resource_found_required('course')]

    def get(self, cid):
        course = g.current_course
        chapters = course.chapters
        data = Chapter.list_to_json(chapters, with_movies=True)
        return make_resp(data)


class DiscussionAPI(Resource):
    # url: /course/<int:cid>/discussions/<string:discus_id>
    method_decorators = [get_course_allowed, resource_found_required("course"),
                         resource_found_required("discussion"), auth_required]

    def get(self, cid, discus_id):
        # get a discussion and its comments
        discussion = g.current_discussion
        return make_resp(discussion.to_json(detail=True))


class DiscussionListAPI(Resource):
    # url: /course/<int:cid>/discussions/
    method_decorators = [get_course_allowed, resource_found_required("course"), auth_required]

    def get(self, cid):
        # get discussions
        discussions = g.current_course.discussions
        return make_resp(Discussion.list_to_json(discussions))

    def post(self, cid):
        # post a discussion
        data = discussion_reqparser.parse_args()
        new_discussion = Discussion(data['content'])
        new_discussion.master = g.current_user
        new_discussion.course = g.current_course
        db.session.add(new_discussion)
        db.session.commit()
        return make_resp(new_discussion.to_json(detail=True))


class CommentAPI(Resource):
    # url: /course/discussions/<string:discus_id>/comments?page=&per_page=
    method_decorators = [resource_found_required("discussion"), auth_required]

    def get(self, discus_id):
        per_page = int(request.args.get("per_page", 20))
        page = int(request.args.get("page", 1))
        comments_pagination = Comment.query.filter_by(discussion_id=discus_id).paginate(page, per_page=per_page, error_out=False)
        data = Comment.page_to_json(comments_pagination, discus_id)
        return make_resp(data)

    def post(self, discus_id):
        # post a comment
        data = comment_reqparser.parse_args()
        new_comment = Comment(data['content'], data['reply'])
        new_comment.author = g.current_user
        new_comment.discussion = g.current_discussion
        db.session.add(new_comment)
        if data['reply'] is not None:
            comment_reply = Comment.query.get(data['reply'])
            if comment_reply is None:
                return api_abort(404, "comment reply is not exist")
            replies = pickle.loads(comment_reply.replies)
            replies.append(new_comment.id)
            comment_reply.replies = pickle.dumps(replies)
        db.session.commit()
        return make_resp(g.current_discussion.to_json(detail=True))


class ReplyAPI(Resource):
    # /course/comment/<string:comment_id>/replies
    method_decorators = [resource_found_required("comment"), auth_required]

    def get(self, comment_id):
        comment = g.current_comment
        return make_resp(comment.to_json())


class CommentLikeAPI(Resource):
    # url: /courses/<int:cid>/comments/<string:comment_id>/like
    method_decorators = [get_course_allowed, resource_found_required('course'),
                         resource_found_required("comment"), auth_required]

    def post(self, cid, comment_id):
        if g.current_user.liked(comment_id, "comment"):
            return api_abort(400, "already liked")
        g.current_user.like(comment_id, "comment")
        return "OK"


class NoticeAPI(Resource):
    # url: /course/<int:cid>/notices/<string:notice_id>
    method_decorators = {"get": [get_course_allowed, auth_required, resource_found_required("notice"),
                                 resource_found_required("course")],
                         "post": [get_course_allowed, auth_required, resource_found_required("notice"),
                                 resource_found_required("course")],
                         "delete": [teacher_required, auth_required, resource_found_required("course"),
                                    resource_found_required("notice")]}

    def get(self, cid, notice_id):
        return make_resp(g.current_notice.to_json(detail=True))

    def post(self, cid, notice_id):
        key_notice_read = "read:{}".format(notice_id)
        key_user_cnt = "read:{}:{}".format(cid, g.current_user.id)
        r.sadd(key_notice_read, g.current_user.id)
        r.incr(key_user_cnt)
        return "OK"

    def delete(self, cid, notice_id):
        db.session.delete(g.current_notice)
        db.session.commit()
        return "OK"


class NoticeListAPI(Resource):
    # url: /course/<int:id>/notices
    method_decorators = {"get": [get_course_allowed, auth_required, resource_found_required("course")],
                         "post": [teacher_required, auth_required, resource_found_required("course")]}

    def get(self, cid):
        notices = g.current_course.notices
        data = Notice.list_to_json(notices)
        return make_resp(data)

    def post(self, cid):
        data = notice_create_reqparser.parse_args()
        new_notice = Notice(data['title'], data['content'])
        new_notice.course = g.current_course

        try:
            students = new_notice.course.students
            for student in students:
                send_notice(student, new_notice)
        except:
            pass

        db.session.add(new_notice)
        db.session.commit()
        return make_resp(new_notice.to_json(detail=True))


class CommitAPI(Resource):
    # url: /course/<int:cid>/commit
    method_decorators = {"get": [get_course_allowed, resource_found_required("course"), auth_required],
                         "post": [teacher_required, resource_found_required("course"), auth_required],
                         "put": [get_course_allowed, resource_found_required("course"), auth_required]}
    
    def get(self, cid):
        # get commit status and it's info
        data = dict()
        data['exist'] = 0
        data['finish'] = 0
        commit_recent = r.lindex("commits:" + str(g.current_course.id), 0)
        if commit_recent is None:
            return make_resp(data)
        commit_recent = pickle.loads(commit_recent)

        time_now = time()
        if strptime(commit_recent['end'])> time_now > strptime(commit_recent['begin']):
            data['exist'] = 1
            data['finished'] = len(commit_recent['finished'])
            data['unfinished'] = len(commit_recent['unfinished'])
            for value in commit_recent['finished']:
                if value['id'] == g.current_user.id:
                    data['finish'] = 1
        return make_resp(data)

    def post(self, cid):
        # submit a commit
        data = commit_create_reqparser.parse_args()
        status, message = validate_commit_time(g.current_course.id, data['expires']*60)
        if not status:
            return api_abort(400, message)

        new_commit = create_commit(g.current_course, data['expires']*60)
        r.lpush("commits:" + str(g.current_course.id), pickle.dumps(new_commit))
        return make_resp(new_commit)

    def put(self, cid):
        # make a commit
        user = g.current_user
        key = "commits:" + str(g.current_course.id)
        commit_recent = r.lindex(key, 0)
        if commit_recent is None:
            return api_abort(400, "there do not exist commit now")
        commit_recent = pickle.loads(commit_recent)

        time_now = time()
        if time_now < strptime(commit_recent['begin']) or time_now > strptime(commit_recent['end']):
            return api_abort(400, "there do not exist commit now")

        unfinished = commit_recent['unfinished']
        finished = commit_recent['finished']
        stu_data = dict()
        stu_data['id'] = user.id
        stu_data['name'] = user.name
        for value in unfinished:
            if value['id'] == user.id:
                unfinished.remove(value)
        finished.append(stu_data)
        commit_recent['unfinished'] = unfinished
        commit_recent['finished'] = finished
        r.lset(key, 0, pickle.dumps(commit_recent))
        return make_resp("OK")


class CommitStatisticsAPI(Resource):
    # url: /course/<int:cid>/commit/statistics?commit_id=
    method_decorators = [teacher_required, resource_found_required("course"), auth_required]

    def get(self, cid):
        key = "commits:" + str(g.current_course.id)
        commits = r.lrange(key, 0, r.llen(key))

        # find commit by commit id
        commit_id = request.args.get("commit_id")
        if commit_id is not None:
            status = 0
            for commit in commits:
                if commit['id'] == commit_id:
                    commits = [commit]
                    status = 1
                    break
            if not status:
                return api_abort(404, "resource commit not found")
        commit_list = []
        for commit in commits:
            commit_list.append(pickle.loads(commit))

        data = {
            "count": len(commits),
            "commits": commit_list
        }
        return make_resp(data)


class CourseRecommendAPI(Resource):
    # url: /course/recommend?count_items=<int>
    def get(self):
        count = request.args.get("count_items", 5)
        courses = Course.query.all()[-1*count:]
        data = Course.list_to_json(courses)
        return make_resp(data)


class DiscussionRecommendAPI(Resource):
    # url: /course/discussions/recommend?count_items=<int>
    def get(self):
        count = int(request.args.get("count_items", 5))
        discussions = Discussion.query.all()[-1*count:]
        data = Discussion.list_to_json(discussions)
        return make_resp(data)


def parse_data(data):
    mapping = {
        "学校": "school",
        "学号": "student_id",
        "姓名": "name",
        "绑定码": "certificate_code",
        "年级": "grade",
        "班级": "class_"
    }
    new_data = dict()
    for k in data:
        new_data[mapping[k]] = data[k]
    if not isinstance(new_data['certificate_code'], str):
        new_data['certificate_code'] = str(int(new_data['certificate_code']))
    return new_data


def deal_import_data(data):
    data = parse_data(data)
    key = data['school'] + ":" + data['student_id']
    existing_data = r.get(key)
    if existing_data:
        existing_data = pickle.loads(existing_data)
        existing_data['school'] = data['school']
        existing_data['student_id'] = data['student_id']
    else:
        existing_data = data
        existing_data['courses'] = []
    return existing_data


def create_prob(data):
    # expected a dict contain prob info
    order = data['order']
    prob_type = data['type']
    content = data['content']
    max_score = data['max_score']
    answer = data['answer']
    answer_detail = data['answer_detail']
    medias = request.files.getlist('problem'+str(order), None)
    media_uuid_list = Media.save_medias(medias, 'problem')
    new_prob = Problem(order, prob_type, content, media_uuid_list, max_score, answer, answer_detail)
    return new_prob


def validate_commit_time(course_id, expires):
    begin = time()
    end = begin + expires
    old_commit = r.lindex("commits:" + str(course_id), 0)
    if old_commit is None:
        return True, "OK"
    if begin > end:
        return False, "invalid time"

    old_commit = pickle.loads(old_commit)
    if strptime(old_commit['end']) > begin:
        return False, "already exist a commit now"

    return True, "OK"