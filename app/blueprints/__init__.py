from .auth import create_auth_bp
from .user import create_user_bp
from .course import create_course_bp
from .task import crate_task_bp
from .test import create_test_bp
from .avatars import create_avatar_bp


auth_bp = create_auth_bp()
user_bp = create_user_bp()
course_bp = create_course_bp()
task_bp = crate_task_bp()
test_bp = create_test_bp()
avatar_bp = create_avatar_bp()