from flask_socketio import join_room, leave_room

from app.extensions import socketio
from app.modules import User


def join_room_(data):
    # ["nickname", "cid"]
    print("event join")
    room = "room:" + str(data['cid'])
    join_room(room)
    socketio.emit("join_room", data['nickname'], room=room)
    print("emit finish")


def leave_room_(data):
    print("event leave")
    room = "room:" + str(data['cid'])
    leave_room(room)
    socketio.emit("leave_room", data["nickname"], room=room)
    print("emit finish")


def send_message(data):
    # ["content", "uid", "cid", "content"]
    print("event send")
    room = "room:" + str(data['cid'])
    message = dict()
    message['content'] = data['content']
    user = User.query.get(int(data['uid']))
    message['user'] = user.to_json()
    socketio.emit("send_message", message, room=room)
    print("emit finish")


socketio.on_event("join_room", join_room_)
socketio.on_event("leave_room", leave_room_)
socketio.on_event("send_message", send_message)
