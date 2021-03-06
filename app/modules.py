import redis
import pickle
import random
import os
from uuid import uuid4 as uuid
from time import time

from werkzeug.security import generate_password_hash, check_password_hash
from flask import url_for, request, current_app, g

from app.extensions import db_sql as db, pool
from app.utils import guess_type, format_time


r = redis.Redis(connection_pool=pool)


def uuid4():
    return str(uuid())


assist_table = db.Table('association1',
                        db.Column('course_id', db.Integer, db.ForeignKey('course.id')),
                        db.Column('user_id', db.Integer, db.ForeignKey('user.id')))

user_task = db.Table('association2',
                     db.Column('task_id', db.Integer, db.ForeignKey('task.id')),
                     db.Column('student_id', db.Integer, db.ForeignKey('user.id')))


class User(db.Model):
    id_name = 'uid'
    id = db.Column(db.Integer, primary_key=True, autoincrement=True, index=True)
    nickname = db.Column(db.String(18), nullable=False, unique=True)
    name = db.Column(db.String(18))
    introduce = db.Column(db.String(300))
    avatar = db.Column(db.String(36))
    school = db.Column(db.String(30))
    student_id = db.Column(db.String(30))
    grade = db.Column(db.String(18))
    class_ = db.Column(db.String(18))
    gender = db.Column(db.Enum('male', 'female', 'secret'), default='secret')
    telephone = db.Column(db.String(11), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    create_at = db.Column(db.Float, nullable=False, default=time)
    update_at = db.Column(db.Float, default=time, onupdate=time)

    courses = db.relationship("Course", back_populates='students', secondary=assist_table)
    messages = db.relationship("Message", back_populates='author')
    tasks = db.relationship("Task", back_populates='students', secondary=user_task)
    answers = db.relationship("TaskAnswer", back_populates='student', cascade='all')
    prob_answers = db.relationship("Answer", back_populates='student', cascade='all')
    comments = db.relationship("Comment", back_populates="author", cascade="all")
    discussions = db.relationship("Discussion", back_populates="master", cascade="all")

    def __init__(self, nickname, telephone, password):
        self.nickname = nickname
        self.name = nickname
        self.avatar = Media.random_avatar()
        self.telephone = telephone
        self.set_password(password)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def validate_password(self, password):
        return check_password_hash(self.password_hash, password)

    def is_teacher(self, course):
        return course.teacher_id == self.id

    def to_json(self, detail=False):
        data = {
            "self": request.host_url[0:-1] + url_for('user_bp.user', uid=self.id),
            "uid": self.id,
            "avatar": Media.load_media_from_uuid(self.avatar, return_model=True).url if self.avatar is not None else None,
            "nickname": self.nickname,
            "introduce": self.introduce,
            "gender": self.gender,
            "school": self.school,
        }

        if detail:
            data_detail = {
                "name": self.name,
                "school_id": self.student_id,
                "telephone": self.telephone,
                "grade": self.grade,
                "class": self.class_,
                "courses": [course.to_json(detail=False) for course in self.courses]
            }
            data.update(data_detail)

        return data

    @staticmethod
    def list_to_json(users):
        data = {
            "count": len(users),
            "students": [student.to_json() for student in users]
        }
        return data

    def like(self, resource_id, resource_type):
        prefix = "like_{}:".format(resource_type)
        key = prefix + resource_id
        r.sadd(key, self.id)

    def liked(self, resource_id, resource_type):
        prefix = "like_{}:".format(resource_type)
        key = prefix + resource_id
        return r.sismember(key, self.id)


class Course(db.Model):
    id_name = "cid"

    id = db.Column(db.Integer, autoincrement=True, index=True, primary_key=True)
    name = db.Column(db.String(36), nullable=False)
    introduce = db.Column(db.String(100))
    public = db.Column(db.Boolean, nullable=False, index=True)
    avatar = db.Column(db.String(36))
    teacher_id = db.Column(db.Integer, nullable=False)
    start_at = db.Column(db.Float, nullable=False)
    end_at = db.Column(db.Float, nullable=False)
    create_at = db.Column(db.Float, nullable=False, default=time)
    update_at = db.Column(db.Float, default=time, onupdate=time)

    chapters = db.relationship("Chapter", back_populates='course', cascade='all')
    tasks = db.relationship("Task", back_populates='course', cascade='all')
    students = db.relationship("User", back_populates='courses', secondary=assist_table)
    messages = db.relationship("Message", back_populates='course', cascade='all')
    discussions = db.relationship("Discussion", back_populates="course", cascade="all")
    notices = db.relationship("Notice", back_populates='course', cascade='all')

    def __init__(self, name, public, teacher_id, start_at, end_at, introduce=None):
        self.name = name
        self.public = public
        self.teacher_id = teacher_id
        self.start_at = start_at
        self.end_at = end_at
        if introduce is not None:
            self.introduce = introduce

    @property
    def teacher(self):
        return User.query.get(self.teacher_id)

    def to_json(self, detail=False):
        data = {
            "self": request.host_url[0:-1] + url_for('course_bp.course', cid=self.id),
            "id": self.id,
            "name": self.name,
            "avatar": Media.load_media_from_uuid(self.avatar, return_model=True).url if self.avatar is not None else None,
            "introduce": self.introduce,
            "public": self.public,
            "create_status": 1 if g.current_user.is_teacher(self) else 0,
            "join_status": 1 if self in g.current_user.courses else 0,
            "stat_at": format_time(self.start_at),
            "end_at": format_time(self.end_at),
            "time_excess": not self.start_at <= time() <= self.end_at,
            "teacher_name": self.teacher.name if self.teacher.name is not None else self.teacher.nickname
        }
        if detail:
            data_detail = {
                "teacher": self.teacher.to_json(detail=False)
                # "students": [student.to_json(detail=False) for student in self.students]
            }
            data.update(data_detail)
        return data

    @staticmethod
    def list_to_json(courses):
        data = {
            "self": request.host_url[0:-1] + request.url,
            "count": len(courses),
            "courses": [course.to_json() for course in courses]
        }
        return data


class Chapter(db.Model):
    id_name = "chapter_id"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True, index=True)
    name = db.Column(db.String)
    documents = db.Column(db.Text)
    movies = db.Column(db.Text)
    create_at = db.Column(db.Float, default=time)
    update_at = db.Column(db.Float, default=time, onupdate=time)

    course_id = db.Column(db.Integer, db.ForeignKey("course.id"))
    course = db.relationship("Course", back_populates='chapters')

    def __init__(self, name, documents=None, movies=None):
        self.name = name
        self.movies = pickle.dumps([]) if movies is None else movies
        self.documents = pickle.dumps([]) if documents is None else documents

    def to_json(self, with_documents=False, with_movies=False):
        data = {
            "id": self.id,
            "name": self.name,
            "create_at": format_time(self.create_at),
            "update_at": format_time(self.update_at)
        }
        data_documents = {
            "document_count": len(pickle.loads(self.documents)) if self.documents is not None else 0,
            "documents": Media.load_medias_from_uuid_list(pickle.loads(self.documents)) if self.documents is not None else None
        }
        data_movies = {
            "movie_count": len(pickle.loads(self.movies)) if self.movies is not None else 0,
            "movies": Media.load_medias_from_uuid_list(pickle.loads(self.movies)) if self.movies is not None else None
        }
        data.update(data_documents) if with_documents else 1  # else pass
        data.update(data_movies) if with_movies else 1
        return data

    @staticmethod
    def list_to_json(chapters, with_documents=False, with_movies=False):
        data = {
            "count": len(chapters),
            "chapters": [chapter.to_json(with_documents, with_movies) for chapter in chapters]
        }
        return data


class Task(db.Model):
    id_name = "tid"

    id = db.Column(db.String(36), primary_key=True, index=True, default=uuid4)
    type = db.Column(db.Enum('exam', 'test'))
    name = db.Column(db.String(18))
    introduce = db.Column(db.Text)
    answer_visible = db.Column(db.Boolean)
    max_score = db.Column(db.Integer)
    create_at = db.Column(db.Float, default=time)
    time_begin = db.Column(db.Float, default=time)
    time_end = db.Column(db.Float, nullable=False)
    expires = db.Column(db.Float)

    answers = db.relationship("TaskAnswer", back_populates='task', cascade='all')
    problems = db.relationship("Problem", back_populates='task', cascade='all')
    students = db.relationship("User", back_populates='tasks', secondary=user_task)

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    course = db.relationship("Course", back_populates='tasks')

    def __init__(self, type_, name, begin, end, visible, introduce=None, expires=None):
        self.type = type_
        self.name = name
        self.time_begin = begin
        self.time_end = end
        self.answer_visible = visible
        self.introduce = introduce
        if expires is None:
            expires = end-begin
        else:
            expires *= 60
        self.expires = expires

    def to_json(self, user, detail=False):
        key = "task_finished:"+str(self.id)
        if not r.sismember(key, user.id):
            finished = False
        else:
            finished = True
        data = {
            "self": request.host_url[0:-1] + url_for('task_bp.task', tid=self.id),
            "type": self.type,
            "id": self.id,
            "task_name": self.name,
            "time_begin": format_time(self.time_begin),
            "time_end": format_time(self.time_end),
            "finished": finished,
            "statistic_select": self.generate_prob_statistic("select"),
            "statistic_blank": self.generate_prob_statistic("blank"),
            "statistic_subjective": self.generate_prob_statistic("subjective"),
            "time_excess": not self.time_begin < time() < self.time_end,
            "answer_visible": self.answer_visible,
            "max_score": self.max_score,
            "create_at": format_time(self.create_at)
        }
        if finished and self.answer_visible:
            show_answer = True
        else:
            show_answer = False
        if detail:
            data_detail = {
                "problems": [prob.to_json(show_answer) for prob in self.problems]
            }
            if self.type == "exam":
                key = "exam_begin:tid:{}:uid:{}".format(self.id, user.id)
                print(key)
                exam_begin = r.get(key)
                exam_begin = float(exam_begin) if exam_begin is not None else None
                data_detail['exam_started'] = 1 if exam_begin is not None else 0
                data_detail['exam_time_excess'] = time()-exam_begin > self.expires if exam_begin is not None else 0
                data_detail['exam_end'] = format_time(exam_begin + self.expires) if exam_begin is not None else None
            data.update(data_detail)
        return data

    @staticmethod
    def list_to_json(tasks, user):
        data = {
            "count": len(tasks),
            "tasks": [task.to_json(user) for task in tasks]
        }
        return data

    @staticmethod
    def page_to_json(pagination, user, cid):
        page = pagination.page
        per_page = pagination.per_page
        max_page = pagination.pages
        tasks = pagination.items
        has_next = pagination.has_next
        has_prev = pagination.has_prev
        data = Task.list_to_json(tasks, user)
        data['max_page'] = max_page
        data['has_next'] = has_next
        data['has_prev'] = has_prev
        if has_next:
            data['next_page'] = request.host_url[0:-1] + url_for("course_bp.tasks", per_page=per_page, page=page + 1, cid=cid)
        else:
            data['next_page'] = None
        if has_prev:
            data['prev_page'] = request.host_url[0:-1] + url_for("course_bp.tasks", per_page=per_page, page=page - 1, cid=cid)
        else:
            data['prev_page'] = None
        return data

    def judge_max_score(self):
        max_score = 0
        probs = self.problems
        for prob in probs:
            max_score += int(prob.max_score)
        self.max_score = max_score
        return max_score

    def statistic(self, detail=False):
        answers = self.answers
        finished = [answer.student for answer in answers]
        unfinished = set(self.students).difference(set(finished))
        finish_rate = 1.0 * len(finished) / len(self.students) if len(self.students) is not 0 else 0
        pass_line = self.max_score * 0.6

        count_pass = 0
        score_sum = 0
        pass_detail = []
        fail_detail = []
        section_count = dict()
        for i in range(0, int(self.max_score/10)):
            section_count[i*10] = 0
        for answer in answers:
            if answer.score >= pass_line:
                count_pass += 1
                pass_detail.append(answer.student.name)
            else:
                fail_detail.append(answer.student.name)
            score_sum += answer.score
            section_count[int(answer.score/10)*10] += 1
        data = {
            "finish_rate": finish_rate,
            "pass_rate": 1.0 * count_pass / len(finished) if len(finished) is not 0 else 0,
            "average": 1.0 * score_sum / len(finished) if len(finished) is not 0 else 0,
            "finish_cnt": len(finished),
            "pass_cnt": count_pass,
            "total_cnt": len(self.students)
        }
        if detail:
            data_detail = {
                "finished_detail": [student.name for student in finished],
                "unfinished_detail": [student.name for student in unfinished],
                "pass_detail": pass_detail,
                "fail_detail": fail_detail,
                "section_count": section_count
            }
            data.update(data_detail)
        return data

    def generate_prob_statistic(self, prob_type):
        probs = self.problems
        if prob_type in current_app.config['SELECT_TYPE']:
            prob_type = 'select'
        statistic = dict()
        statistic['count'] = 0
        statistic['sum'] = 0
        for prob in probs:
            if prob.type == prob_type:
                statistic['count'] += 1
                statistic['sum'] += prob.max_score
        return statistic


class Problem(db.Model):
    id_name = "prob_id"

    id = db.Column(db.String(36), primary_key=True, index=True, default=uuid4)
    type = db.Column(db.Enum('select', 'blank', 'subjective', 'mselect', "judge"))
    order = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text)
    max_score = db.Column(db.Integer)
    media = db.Column(db.Text)  # include a list of url
    answer = db.Column(db.Text)  # if type is 'blank', it include a list of text
    answer_detail = db.Column(db.Text)  # include a dict has attr 'type'[text, url] and 'content'
    create_at = db.Column(db.Float, default=time)

    task_id = db.Column(db.Integer, db.ForeignKey("task.id"))
    task = db.relationship("Task", back_populates='problems')

    answers = db.relationship("Answer", back_populates='problem', cascade='all')

    def __init__(self, order, type_, content=None, medias=None, max_score=5, answer=None, answer_detail=None):
        """
        :param medias: a list containing medias's uuid
        :param answer: when type is "select", expected ['A' | 'B' | 'C' | 'D'].
                       when type is "blank", expected a list of answer
        :param answer_detail: expected a dict, dict example: {"type": ['media', 'text'], "content":"text or uuid"}
        """
        self.type = type_
        self.content = content
        self.max_score = max_score
        self.order = order
        self.answer_detail = answer_detail
        if medias is not None:
            self.media = pickle.dumps(medias)
        if answer is not None:
            self.answer = pickle.dumps(answer)

    def to_json(self, return_answer=False):
        data = {
            "type": self.type,
            "order": self.order,
            "id": self.id,
            "content": self.content if self.type not in current_app.config['SELECT_TYPE'] else pickle.loads(self.content),
            "medias": Media.load_medias_from_uuid_list(pickle.loads(self.media)) if self.media is not None else None,
            "max_score": self.max_score,
            "create_at": format_time(self.create_at),
            "picture_exist": 1 if self.media is not None else 0
        }
        if return_answer:
            data_answer = {
                "answer": pickle.loads(self.answer) if self.answer is not None else None,
                # "answer_detail": self.detail_answer_to_json()
                "answer_detail": self.answer_detail
            }
            print(data_answer)
            data.update(data_answer)
        return data

    def detail_answer_to_json(self):
        answer_detail = pickle.loads(self.answer_detail)
        if answer_detail['type'] is "media":
            media = Media.query.get(answer_detail['content'])
            answer_detail['content'] = media.to_json()
        return answer_detail

    def statistic(self, detail=False):
        answers = self.answers
        count_students = len(self.task.students)
        pass_line = self.max_score * 0.6
        score_sum = 0
        count_pass = 0
        count_correct = 0
        pass_detail = []
        fail_detail = []
        correct_detail = []

        for answer in answers:
            student = answer.student.name
            score_sum += answer.score
            if answer.score >= pass_line:
                count_pass += 1
                pass_detail.append(student)
                if answer.score == self.max_score:
                    count_correct += 1
                    correct_detail.append(student)
            else:
                fail_detail.append(student)

        data = {
            "pass_rate": count_pass / count_students if count_students is not 0 else 0,
            "correct_rate": count_correct / count_students if count_students is not 0 else 0,
            "average": score_sum / count_students if count_students is not 0 else 0
        }
        data_detail = {
            "pass_detail": pass_detail,
            "fail_detail": fail_detail,
            "correct_detail": correct_detail
        }
        if detail:
            data.update(data_detail)

        return data


class TaskAnswer(db.Model):
    id_name = "task_answer_id"

    id = db.Column(db.String(36), primary_key=True, default=uuid4)
    status = db.Column(db.Boolean, server_default=db.text('0'))
    score = db.Column(db.Integer, server_default=db.text('0'))
    create_at = db.Column(db.Float, default=time)
    update_at = db.Column(db.Float, default=time, onupdate=time)

    answers = db.relationship("Answer", back_populates='task_answer', cascade='all')

    student_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    student = db.relationship("User", back_populates='answers')

    task_id = db.Column(db.String(36), db.ForeignKey('task.id'))
    task = db.relationship("Task", back_populates='answers')

    def __init__(self):
        pass

    def to_json(self,detail=False):
        data = {
            "uuid": self.id,
            "status": self.status,
            "score": self.score,
            "create_at": format_time(self.create_at),
            "update_at": format_time(self.update_at)
        }
        if detail:
            if self.task.answer_visible:
                correct_ans = True
            else:
                correct_ans = False
            data_detail = {
                "answers": [answer.to_json(return_correct_answer=correct_ans) for answer in self.answers]
            }
            data.update(data_detail)
        return data

    def judge_score(self):
        score = 0
        answers = self.answers
        for answer in answers:
            score += answer.score
        self.score = score
        return score


class Answer(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=uuid4)
    content = db.Column(db.Text)
    media = db.Column(db.Text)
    order = db.Column(db.Integer)
    score = db.Column(db.Integer)
    comment = db.Column(db.Text)
    create_at = db.Column(db.Float, default=time)
    update_at = db.Column(db.Float, default=time, onupdate=time)

    problem_id = db.Column(db.String(36), db.ForeignKey("problem.id"))
    problem = db.relationship("Problem", back_populates='answers')

    task_answer_id = db.Column(db.String(36), db.ForeignKey("task_answer.id"))
    task_answer = db.relationship("TaskAnswer", back_populates='answers')

    student_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    student = db.relationship("User", back_populates='prob_answers')

    def __init__(self, order, content=None, medias=None):
        self.order = order
        if content is not None:
            if not isinstance(content, list):
                content = [content]
            self.content = pickle.dumps(content)
        if medias is not None:
            self.media = pickle.dumps(medias)
        self.score = 0

    def to_json(self, with_problem=False, return_correct_answer=False):
        data = {
            "id": str(self.id),
            "content": pickle.loads(self.content) if self.content is not None else None,
            "medias": Media.load_medias_from_uuid_list(pickle.loads(self.media)) if self.media is not None else None,
            "score": self.score,
            "order": self.order,
            "comment": self.comment,
            "answer_at": format_time(self.create_at),
            "update_at": format_time(self.update_at)
        }
        if with_problem:
            data_problem = self.problem.to_json(return_correct_answer)
            data_problem['student_answer'] = data
            data = data_problem
            return data
        if return_correct_answer:
            data_answer = {
                "correct_answer": pickle.loads(self.problem.answer) if self.problem.answer is not None else None,
                # "answer_detail": self.detail_answer_to_json()
                "answer_detail": self.problem.answer_detail
            }
            data.update(data_answer)
        return data

    def judge_score(self):
        if self.content is None:
            self.score = 0
            return 0

        prob = self.problem
        answers = pickle.loads(prob.answer) if prob.answer is not None else None
        my_ans = pickle.loads(self.content)
        max_score = prob.max_score
        if prob.type is 'select':
            answers = set(answers)
            my_ans = set(my_ans)
            if answers == my_ans:
                score = max_score
            else:
                score = 0
        elif prob.type is 'blank':
            score = max_score
            for i in range(0, len(answers)):
                if my_ans[i] != answers[i]:
                    score -= 1.0*max_score/len(answers)
        else:
            score = 0
        self.score = score
        return score


class Media(db.Model):
    id_name = "media_id"

    id = db.Column(db.String(36), primary_key=True)
    name = db.Column(db.String(36))
    url = db.Column(db.Text, unique=False)
    type = db.Column(db.Enum('picture', 'audio', 'video', 'word', 'excel', 'ppt', 'pdf', 'python', 'cpp'))
    upload_at = db.Column(db.Float, default=time)

    def __init__(self, url, uuid=None, name=None):
        if uuid is None:
            uuid = uuid4()
        self.id = uuid
        if name is None:
            name = self.id
        self.name = name
        self.url = url
        self.type = guess_type(url)

    def to_json(self):
        data = {
            'uuid': str(self.id),
            "name": self.name,
            'type': self.type,
            'url': self.url,
            'upload_at': format_time(self.upload_at)
        }
        return data

    @staticmethod
    def save_medias(medias, media_type, return_model=False):
        media_list = []
        for media in medias:
            new_media = Media.save_media(media, media_type, return_model=return_model, commit=False)
            media_list.append(new_media)
        db.session.commit()
        return media_list

    @staticmethod
    def save_media(media, media_type, name=None, return_model=False, commit=True):
        filename = media.filename
        if filename[-1] is "\"":
            filename = filename[0:-1]
        postfix = filename.split('.')[-1]
        if postfix == 'blob':
            postfix = 'jpg'
        uuid = uuid4()
        if name is None:
            name = uuid
        sub_path = "/{}/{}.{}".format(media_type, uuid, postfix)
        save_path = os.path.abspath(current_app.static_folder + sub_path)
        try:
            media.save(save_path)
        except FileNotFoundError:
            os.makedirs(os.path.split(save_path)[0])
            media.save(save_path)
        url = request.host_url[0:-1] + current_app.static_url_path + sub_path
        new_media = Media(url, uuid, name)
        db.session.add(new_media)
        if commit:
            db.session.commit()
        if return_model:
            return new_media
        else:
            return new_media.id

    @staticmethod
    def load_medias_from_uuid_list(media, return_model=False):
        media_uuid_list = media
        media_list = []
        for uuid in media_uuid_list:
            media = Media.load_media_from_uuid(uuid, return_model)
            media_list.append(media)
        return media_list

    @staticmethod
    def load_media_from_uuid(uuid, return_model=False):
        media = Media.query.get(uuid)
        if return_model:
            return media
        return media.to_json()

    def delete(self):
        path = current_app.static_folder + self.url.replace(request.host_url[:-1] + current_app.static_url_path, "")
        try:
            os.remove(os.path.abspath(path))
        except FileNotFoundError:
            pass

    @staticmethod
    def random_avatar(return_model=False):
        url = request.host_url[:-1] + current_app.static_url_path + "/avatars/user/banner{}.jpg".format(random.choice([6, 7, 8, 13, 14]))
        new_avatar = Media(url)
        db.session.add(new_avatar)
        db.session.commit()
        if return_model:
            return new_avatar
        return new_avatar.id


class Discussion(db.Model):
    id_name = "discus_id"

    id = db.Column(db.String(36), primary_key=True, default=uuid4)
    content = db.Column(db.Text)
    creat_at = db.Column(db.Float, default=time)
    update_at = db.Column(db.Float, default=time, onupdate=time)

    course_id = db.Column(db.Integer, db.ForeignKey("course.id"))
    course = db.relationship("Course", back_populates='discussions')

    master_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    master = db.relationship("User", back_populates='discussions')

    comments = db.relationship("Comment", back_populates='discussion', cascade="all")

    def __init__(self, content):
        self.content = content

    def to_json(self, detail=False):
        data = {
            "id": self.id,
            "content": self.content,
            "post_at": format_time(self.creat_at),
            "update_at": format_time(self.update_at),
            "user": self.master.to_json()
        }
        if detail:
            data_detail = {
                "comments_count": len(self.comments)
            }
            data_detail.update(Comment.list_to_json(self.comments))
            data.update(data_detail)
        return data

    @staticmethod
    def list_to_json(discussions):
        data = {
            "count": len(discussions),
            "discussions": [discussion.to_json() for discussion in discussions]
        }
        return data


class Comment(db.Model):
    id_name = "comment_id"

    id = db.Column(db.String(36), primary_key=True, default=uuid4)
    content = db.Column(db.Text)
    replies = db.Column(db.Text)
    reply = db.Column(db.String(36))
    creat_at = db.Column(db.Float, default=time)

    discussion_id = db.Column(db.String(36), db.ForeignKey("discussion.id"))
    discussion = db.relationship("Discussion", back_populates='comments')

    author_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    author = db.relationship("User", back_populates="comments")

    def __init__(self, content, reply=None):
        self.content = content
        self.reply = reply
        self.replies = pickle.dumps([])

    def to_json(self):
        replies = []
        for reply_id in pickle.loads(self.replies):
            reply = Comment.query.filter_by(id=reply_id).first()
            if reply is not None:
                replies.append(reply.to_json())
        data = {
            "id": str(self.id),
            "content": self.content,
            "likes": r.scard("like_comment:{}".format(str(self.id))),
            "liked": g.current_user.liked(str(self.id), "comment"),
            "replies": replies,
            "reply": self.reply,
            "post_at": format_time(self.creat_at),
            "author": self.author.to_json()
        }
        return data

    @staticmethod
    def list_to_json(comments):
        comment_list = []
        for comment in comments:
            if comment.reply is None:
                comment_list.append(comment.to_json())
        data = {
            "count": len(comments),
            "comments": comment_list
        }
        return data

    @staticmethod
    def page_to_json(pagination, discus_id):
        page = pagination.page
        per_page = pagination.per_page
        max_page = pagination.pages
        comments = pagination.items
        has_next = pagination.has_next
        has_prev = pagination.has_prev
        data = Comment.list_to_json(comments)
        data['max_page'] = max_page
        data['has_next'] = has_next
        data['has_prev'] = has_prev
        if has_next:
            data['next_page'] = request.host_url[0:-1] + url_for("course_bp.comments", per_page=per_page, page=page + 1, discus_id=discus_id)
        else:
            data['next_page'] = None
        if has_prev:
            data['prev_page'] = request.host_url[0:-1] + url_for("course_bp.comments", per_page=per_page, page=page - 1, discus_id=discus_id)
        else:
            data['prev_page'] = None
        return data


class Notice(db.Model):
    id_name = "notice_id"

    id = db.Column(db.String(36), primary_key=True, index=True, default=uuid4)
    title = db.Column(db.String, nullable=False)
    content = db.Column(db.Text, nullable=False)
    create_at = db.Column(db.Float, default=time())

    course_id = db.Column(db.Integer, db.ForeignKey("course.id"))
    course = db.relationship("Course", back_populates='notices')

    def __init__(self, title, content):
        self.content = content
        self.title = title

    def to_json(self, detail=False):

        read = 0
        key = "read:{}".format(self.id)
        if r.sismember(key, g.current_user.id):
            read = 1

        data = {
            "id": self.id,
            "self": request.host_url[:-1] + url_for("course_bp.notice", notice_id=self.id, cid=self.course.id),
            "title": self.title,
            "read": read
        }
        if detail:
            data_detail = {
                "content": self.content,
                "create_at": format_time(self.create_at)
            }
            data.update(data_detail)
        return data

    @staticmethod
    def list_to_json(notices):
        data = {
            "count": len(notices),
            "notices": [notice.to_json(detail=True) for notice in notices]
        }
        return data


class Message(db.Model):

    id = db.Column(db.String(36), primary_key=True, default=uuid4)
    type = db.Column(db.Enum('text', 'picture', 'file'))
    content = db.Column(db.String(300))
    create_at = db.Column(db.Float, default=time)

    author_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    author = db.relationship('User', back_populates='messages')

    course_id = db.Column(db.Integer, db.ForeignKey('course.id'))
    course = db.relationship('Course', back_populates='messages')

    def __init__(self, type_, content):
        self.type = type_
        self.content = content


def create_commit(course, expires):
    begin = time()
    end = begin + expires
    new_commit = dict()
    new_commit['begin'] = format_time(begin)
    new_commit['end'] = format_time(end)
    finished = []
    unfinished = []
    for user in course.students:
        d = dict()
        d["id"] = user.id
        d["name"] = user.name
        unfinished.append(d)
    new_commit['finished'] = finished
    new_commit['unfinished'] = unfinished
    new_commit['id'] = uuid4()
    return new_commit
