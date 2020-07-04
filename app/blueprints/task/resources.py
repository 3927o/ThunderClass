import redis
import pickle
from time import time

from flask import g, request
from flask_restful import Resource

from app.utils import api_abort, make_resp
from app.extensions import db_sql as db, pool
from app.modules import Task, TaskAnswer, Media, Answer
from app.blueprints.auth import auth_required, resource_found_required

from .reqparsers import answer_submit_reqparser, check_answer_reqparser


r = redis.Redis(connection_pool=pool)


def get_course_allowed(f):
    def decorator(*args, **kws):
        user = g.current_user
        course = g.current_task.course
        if user not in course.students and not user.is_teacher(course):
            return api_abort(403, "not the student ot teacher")
        return f(*args, **kws)
    return decorator


def edit_task_allowed(f):
    def decorator(*args, **kws):
        user = g.current_user
        task = g.current_task
        if not user.is_teacher(task.course):
            return api_abort(403, "not the teacher")
        return f(*args, **kws)
    return decorator


class TaskAPI(Resource):
    # url: /task/<int:tid>
    # if finished, will return the correct answer
    method_decorators = {"get": [get_course_allowed, auth_required, resource_found_required('task')],
                         "delete": [edit_task_allowed, auth_required, resource_found_required('task')]}

    def get(self, tid):
        set_exam_expires(g.current_user, g.current_task)
        return make_resp(g.current_task.to_json(g.current_user, detail=True))

    def delete(self, tid):
        db.session.delete(g.current_task)
        db.session.commit()
        return make_resp({})


class AnswerSubmitAPI(Resource):
    # url: /task/<string:tid>/submit
    method_decorators = [get_course_allowed, auth_required, resource_found_required('task')]

    def post(self, tid):
        user = g.current_user
        task = g.current_task
        if user.is_teacher(task.course):
            return api_abort(403, "you are the teacher")
        time_now = time()
        if not task.time_begin <= time_now <= task.time_end:
            return api_abort(403, "not in the time")

        # delete existed answer
        exist_task_answer = set(task.answers).intersection(set(user.answers))
        if exist_task_answer:
            exist_task_answer = exist_task_answer.pop()
            for answer in exist_task_answer.answers:
                if answer.media is not None:
                    medias = Media.load_medias_from_uuid_list(pickle.loads(answer.media), return_model=True)
                    for media in medias:
                        media.delete()
            db.session.delete(exist_task_answer)

        new_task_answer = TaskAnswer()
        answers = answer_submit_reqparser.parse_args()['answers']
        if not isinstance(answers, list):
            answers = eval(answers)
        problems = dict()
        prob_order_set = set()
        for prob in task.problems:
            problems[prob.order] = prob
            prob_order_set.add(prob.order)

        answer_order_set = set()
        for answer in answers:
            if not isinstance(answer, dict):
                answer = eval(answer)
            content = answer.get('content', None)
            if content == 'undefined':
                content = None
            order = answer.get("order", None)
            if order is None:
                return api_abort(400, "order is needed")
            answer_order_set.add(order)
            medias = request.files.getlist('answer' + str(order))
            media_uuid_list = Media.save_medias(medias, 'answer') if len(medias) is not 0 else None
            new_answer = Answer(order, content, media_uuid_list)
            new_answer.student = user
            new_answer.problem = problems[order]
            if new_answer.problem.type is not "subjective":
                new_answer.judge_score()
            new_task_answer.answers.append(new_answer)

        if answer_order_set.difference(prob_order_set):
            return api_abort(400, "answer order over the max order")
        for order in prob_order_set.difference(answer_order_set):
            medias = request.files.getlist('answer' + str(order), None)
            media_uuid_list = Media.save_medias(medias, 'answer') if len(medias) is not 0 else None
            new_answer = Answer(order, medias=media_uuid_list)
            new_answer.student = user
            new_answer.problem = problems[order]
            new_task_answer.answers.append(new_answer)

        new_task_answer.student = user
        new_task_answer.task = task
        new_task_answer.judge_score()
        r.sadd("task_finished:"+task.id, user.id)
        db.session.add(new_task_answer)
        db.session.commit()
        data = new_task_answer.to_json(detail=True)
        return make_resp(data)


class TaskAnswerAPI(Resource):
    # url: /task/<string:tid>/answers?uncheck=<bool>
    method_decorators = [auth_required, resource_found_required('task')]

    def get(self, tid):
        task = g.current_task
        user = g.current_user
        uncheck = request.args.get('uncheck', 0)
        task_answer = None
        if uncheck:
            if not user.is_teacher(task.course):
                return api_abort(403, 'not the teacher')
            for answer in task.answers:
                if not answer.status:
                    task_answer = answer
                    break
            if task_answer is None:
                return api_abort(404, "all answers checked")
        else:
            task_answer = set(user.answers).intersection(set(task.answers))
            if not task_answer:
                return api_abort(404, "have not finished the task")
            task_answer = task_answer.pop()
        return make_resp(task_answer.to_json(detail=True))


class ProblemAPIByOrder(Resource):
    # url: /task/<string:tid>/problems/<int:order>
    method_decorators = [get_course_allowed, auth_required, resource_found_required('task')]

    def get(self, tid, order):
        task = g.current_task
        problem = None
        for prob in task.problems:
            if prob.order == order:
                problem = prob
                break
        if problem is None:
            return api_abort(404, "problem order {} not found".format(order))
        return make_resp(problem.to_json())


class ProbAPIByID(Resource):
    # url: /task/problem/<string:prob_id>
    method_decorators = [auth_required, resource_found_required('problem')]

    def get(self, prob_id):
        return make_resp(g.current_problem.to_json())


class AnswerAPIByOrder(Resource):
    # url: /task/<string:tid>/answers/<int:order>
    method_decorators = [get_course_allowed, auth_required, resource_found_required('task')]

    def get(self, tid, order):
        task = g.current_task
        user = g.current_user
        task_answer = set(task.answers).intersection(set(user.answers))
        if not task_answer:
            return api_abort(404, "you have not finished the problem")
        task_answer = task_answer.pop()
        answers = task_answer.answers
        answer_return = None
        for answer in answers:
            if answer.problem.order == order:
                answer_return = answer
                break
        if answer_return is None:
            return api_abort(404, "answer order {} not found".format(order))
        return make_resp(answer_return.to_json())


class CorrectAnswerAPI(Resource):
    # url: /task/answers/correct_answer?task_answer_id=<string:uuid>
    method_decorators = [auth_required, resource_found_required('task_answer')]

    def post(self):
        if not g.current_user.is_teacher(g.current_task_answer.task.course):
            return api_abort(403, "not the teacher")
        #  要是想以另一种形式返回也行
        check_res_list = check_answer_reqparser.parse_args()['check_res']
        check_res_list = eval(check_res_list)
        answers = dict()
        answer = g.current_task_answer.answers
        for ans in answer:
            answers[int(ans.order)] = ans

        for check_res in check_res_list:
            order = check_res['order']
            ans = answers[order]
            score = check_res['score'] if check_res['score'] is not None else ans.score
            if score>ans.problem.max_score:
                return api_abort(400, "the score of answer ordered {} is too high".format(order))
            ans.score = score
            ans.comment = check_res.get("comment", None)

        g.current_task_answer.judge_score()
        db.session.commit()
        return make_resp("OK")


class TaskStatisticAPI(Resource):
    # url: /task/<string:tid>/statistic?detail=True
    method_decorators = [edit_task_allowed, resource_found_required("task"), auth_required]

    def get(self, tid):
        detail = request.args.get("detail", False)
        data = g.current_task.statistic(detail)
        return make_resp(data)


class ProbStatisticAPI(Resource):
    # url: /task/<string:tid>/statistic/problems?order=<int:order>&detail=True
    method_decorators = [edit_task_allowed, resource_found_required("task"), auth_required]

    def get(self, tid):
        order = request.args.get("order", None)
        if order is None:
            return api_abort(400, "param order is needed")
        order = int(order)

        problem = None
        for prob in g.current_task.problems:
            if prob.order == order:
                problem = prob
                break
        if problem is None:
            return api_abort(400, "problem order {} is not found".format(order))

        detail = request.args.get("detail", False)
        data = problem.statistic(detail)
        return make_resp(data)


class TaskStuStatusAPI(Resource):
    # url:/task/<string:tid>/statistic/stu_status
    method_decorators = [edit_task_allowed, auth_required, resource_found_required("task")]

    def get(self, tid):
        task = g.current_task
        students = task.students
        key = "task_finished:" + str(task.id)
        stu_list = []
        for student in students:
            score = 0
            task_answer = set(student.answers).intersection(set(g.current_task.answers))
            if task_answer:
                score = task_answer.pop().score

            if not r.sismember(key, student.id):
                finished = False
            else:
                finished = True

            data = {
                "name": student.name,
                "student_id": student.student_id,
                "finished": finished,
                "score": score
            }

            stu_list.append(data)

        return make_resp(stu_list)


def set_exam_expires(user, task):
    key = "exam_begin:tid:{}:uid:{}".format(task.id, user.id)
    print(key)
    if r.get(key) is None:
        r.set(key, time())