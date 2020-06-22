import xlrd
from flask import Blueprint, request


def create_test_bp(name='test_bp'):
    test_bp = Blueprint(name, __name__)

    @test_bp.route("/excel", methods=['POST', 'GET'])
    def filelist1():
        file = request.files['file']
        f = file.stream.read()
        data = xlrd.open_workbook(file_contents=f)
        table = data.sheets()[0]
        col_name = table.row_values(0)
        li = list()
        for i in range(1, table.nrows):
            d = dict()
            for j in range(table.ncols):
                d[col_name[j]] = table.row_values(i)[j]
            li.append(d)
        print(li)
        return "OK"

    @test_bp.route('/')
    def index():
        token = request.headers.get("Authorization")
        print(token)
        print(type(token))
        return token

    return test_bp


# n = input()
# month = 2
# now = 1
# pre = 1
# while now < n:
#     t = now
#     now = now + pre
#     pre = t
#     month += 1
# print(month)