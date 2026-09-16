from flask import Blueprint, render_template
from flask_login import login_required
from app.models.user import User
from app.models.user_session import UserSession
from app.utils.decorators import role_required

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


@admin_bp.route('/users-online')
@login_required
@role_required('directivo')
def users_online():
    # Limpia sesiones viejas automáticamente
    UserSession.cleanup_stale(minutes=30)

    online_users = User.get_online_users(minutes=5)
    active_sessions = UserSession.get_active_sessions()

    return render_template('admin/users_online.html',
                           online_users=online_users,
                           active_sessions=active_sessions)