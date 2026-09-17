from flask import Flask, redirect, url_for, flash
from flask_login import LoginManager, current_user
from app.config import Config
from app.models.user import User
from app.utils.db import get_db_connection
from datetime import datetime


login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder.'


@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    login_manager.init_app(app)
    app.config['MAX_CONTENT_LENGTH'] = app.config.get('MAX_CONTENT_LENGTH', 2 * 1024 * 1024)

    # ---------- Registrar blueprints ----------
    from app.routes.auth import auth_bp
    from app.routes.main import main_bp
    from app.routes.students import students_bp
    from app.routes.enrollment import enrollment_bp
    from app.routes.teachers import teachers_bp
    from app.routes.courses import courses_bp
    from app.routes.attendance import attendance_bp
    from app.routes.schedule import schedule_bp
    from app.routes.daily_stats import daily_stats_bp
    from app.routes.evaluations import evaluations_bp
    from app.routes.admin import admin_bp
    from app.routes.profile import profile_bp
    from app.routes.student_profile import student_profile_bp
    from app.routes.staff_profile import staff_profile_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(enrollment_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(courses_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(daily_stats_bp)
    app.register_blueprint(evaluations_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(profile_bp)
    app.register_blueprint(student_profile_bp)
    app.register_blueprint(staff_profile_bp)

    # ---------- Manejo del 413 (archivo demasiado grande) ----------
    @app.errorhandler(413)
    def too_large(e):
        flash('El archivo es demasiado grande. Máximo 2 MB.', 'danger')
        return redirect(url_for('profile.index'))

    # ---------- Actualizar last_seen en cada petición ----------
    @app.before_request
    def update_last_seen():
        if current_user.is_authenticated:
            conn = get_db_connection()
            if conn:
                cursor = conn.cursor()
                try:
                    cursor.execute(
                        "UPDATE users SET last_seen = NOW() WHERE id = %s",
                        (current_user.id,)
                    )
                    cursor.execute("""
                        UPDATE user_sessions
                        SET last_activity = NOW()
                        WHERE user_id = %s AND is_active = 1
                    """, (current_user.id,))
                    conn.commit()
                except Exception as e:
                    print(f"[before_request] {e}")
                finally:
                    cursor.close()
                    conn.close()

    @app.context_processor
    def inject_now():
        return {'now': datetime.now()}

    return app