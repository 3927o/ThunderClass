from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO
import redis

db_sql = SQLAlchemy()
pool = redis.ConnectionPool(host='127.0.0.1', port=6379)
socketio = SocketIO(cors_allowed_origins="*")