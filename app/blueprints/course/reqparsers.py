import pickle
from flask_restful.reqparse import RequestParser


course_create_reqparser = RequestParser()
course_create_reqparser.add_argument('name', type=str, required=True)
course_create_reqparser.add_argument('public', type=int, required=True)
course_create_reqparser.add_argument('introduce', type=str)
course_create_reqparser.add_argument('start_at', type=float, required=True)
course_create_reqparser.add_argument('end_at', type=float, required=True)

course_put_reqparser = RequestParser()
course_put_reqparser.add_argument('introduce', type=str, location='json')

task_create_reqparser = RequestParser()
task_create_reqparser.add_argument("type", type=str, required=True)
task_create_reqparser.add_argument("name", type=str, required=True)
task_create_reqparser.add_argument("t_begin", type=float, required=True)
task_create_reqparser.add_argument("t_end", type=float, required=True)
task_create_reqparser.add_argument("problems", required=True)
task_create_reqparser.add_argument("ans_visible", type=str, required=True)
task_create_reqparser.add_argument("introduce", type=str, required=False)
task_create_reqparser.add_argument("expires", type=float)

upload_reqparser = RequestParser()
upload_reqparser.add_argument('chapter', type=str, required=True)
upload_reqparser.add_argument('name', type=str, required=True)

comment_reqparser = RequestParser()
comment_reqparser.add_argument('content', type=str, required=True, location='json')
comment_reqparser.add_argument('reply', type=str, required=False, location='json')

discussion_reqparser = RequestParser()
discussion_reqparser.add_argument('content', type=str, required=True, location='json')

commit_create_reqparser = RequestParser()
commit_create_reqparser.add_argument("expires", type=int, required=True, location="json")

notice_create_reqparser = RequestParser()
notice_create_reqparser.add_argument('title', type=str, required=True, location='json')
notice_create_reqparser.add_argument('content', type=str, required=True, location='json')


def prob_parser(data):
    new_data = dict()
    if not isinstance(data, dict):
        data = eval(data)

    required = ['type', 'order']
    for require in required:
        if require not in data:
            print("no required")
            return None
        new_data[require] = data[require]

    # item answer should be a list, it is required when type is not subjective
    if data['type'] is 'select' or data['type'] is 'mselect' or data['type'] is 'judge':
        if 'answer' not in data:
            print("no ans")
            return None
        if not isinstance(data['answer'], list):
            data['answer'] = [data['answer']]
        new_data['answer'] = [ans.upper() for ans in data['answer']]
    elif data['type'] is 'blank':
        if 'answer' not in data:
            print("no ans")
            return None
        if not isinstance(data['answer'], list):
            print("ans is not list")
            return None
        new_data['answer'] = data['answer']
    elif data['type'] is "subjective":
        new_data['answer'] = data.get("answer", None)
    else:
        print("wrong type")
        return None

    new_data["answer_detail"] = data.get("answer_detail", None)
    new_data['max_score'] = int(data.get("max_score", 5))
    if new_data['type'] is "select" or new_data['type'] is "mselect" or data['type'] is 'judge':
        new_data['content'] = data.get("content", None)
    else:
        new_data['content'] = data["content"]["text"]
    new_data['order'] = int(new_data['order'])

    # deal select problem's content
    if new_data['type'] is "select" or new_data['type'] is "mselect" or data['type'] is 'judge':
        if new_data['content'] is not None:
            if not isinstance(new_data['content'], dict):
                print("content is not list")
                return None
            if "options" in new_data['content'] and not isinstance(new_data['content']['options'], list):
                print("options not in data or options is not list")
                return None
        new_data['content'] = pickle.dumps(new_data['content'])

    return new_data