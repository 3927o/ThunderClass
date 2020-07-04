from flask import Blueprint
from flask_restful import Api
from flask_cors import CORS

from .resources import TaskAPI, AnswerSubmitAPI, TaskAnswerAPI, CorrectAnswerAPI, \
    ProblemAPIByOrder, ProbAPIByID, AnswerAPIByOrder, TaskStatisticAPI, ProbStatisticAPI, TaskStuStatusAPI


def crate_task_bp(name='task_bp'):
    task_bp = Blueprint(name, __name__)
    api_task = Api(task_bp)
    CORS(task_bp)

    api_task.add_resource(TaskAPI, '/<string:tid>', endpoint="task")
    api_task.add_resource(AnswerSubmitAPI, '/<string:tid>/submit', endpoint='submit')
    api_task.add_resource(TaskAnswerAPI, '/<string:tid>/answers', endpoint="task_answer")
    api_task.add_resource(CorrectAnswerAPI, '/answers/correct_check', endpoint='correct_ans')
    api_task.add_resource(ProblemAPIByOrder, '/<string:tid>/problems/<int:order>', endpoint='prob_order')
    api_task.add_resource(ProbAPIByID, '/problem/<string:prob_id>', endpoint='prob_id')
    api_task.add_resource(AnswerAPIByOrder, '/<string:tid>/answers/<int:order>', endpoint='ans_order')
    api_task.add_resource(TaskStatisticAPI, '/<string:tid>/statistic', endpoint='statistic_t')
    api_task.add_resource(ProbStatisticAPI, '/<string:tid>/statistic/problems', endpoint='statistic_p')
    api_task.add_resource(TaskStuStatusAPI, '/<string:tid>/statistic/stu_status')

    return task_bp