import xlrd


def parse_excel(request, filename):
    file = request.files[filename]
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
    return li
