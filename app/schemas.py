from flask import jsonify


def make_resp(data, status=200, message='succeed'):
    resp = jsonify({
        'status': status,
        'message': message,
        'data': data
    })
    resp.status_code = status
    return resp


def user_schema(user, detail=False):
    data = {
        "uid": user.id,
        "nickname": user.nickname,
        "gender": user.gender,
        "school": user.school,
    }
    data_detail = {
        "school_id": user.school_id,
        "telephone": user.telephone,
        "grade": user.grade,
        "class": user.class_
    }

    if detail:
        data.update(data_detail)

    return data


def course_schema(course, detail=False):
    data = {
        "id": course.id,
        "name": course.name,
        "introduce": course.introduce,
        "public": course.public,
        "teacher_name": course.teacher.name if course.teacher.name is not None else course.teacher.nickname
    }
    data_detail = {
        "teacher": course.teacher.to_json(),
        "students": [student.to_json() for student in course.students]
    }
    if detail:
        data.update(data_detail)
    return data_detail