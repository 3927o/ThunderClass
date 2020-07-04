from app import create_app
from app.extensions import db_sql as db
from app.modules import User, Course


app = create_app('testing', static_url_path='/files')
ctx = app.test_request_context()
ctx.push()
db.create_all()
user1 = User('3927', '13110560639', '123456')
user2 = User("lin", "13067258562", "123456")
course1 = Course('test_course1', 1, 1, 1592144807.9424236, 1602144807.9424236, "test_course1")
course2 = Course('test_course2', 0, 1, 1592144807.9424236, 1602144807.9424236, "test_course2")
course2.students.append(user2)
course1.students.append(user2)
db.session.add(user1)
db.session.add(user2)
db.session.add(course1)
db.session.add(course2)
db.session.commit()

app.run(debug=True)