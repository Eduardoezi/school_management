from flask import Flask, app
from flask_login import LoginManager
from app.config import Config
from app.models.user import User

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder.'

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(int(user_id))

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)   # <--- Esto carga todas las variables, incluida SECRET_KEY

    login_manager.init_app(app)      # <--- Debe ir después de app.config.from_object(Config)

    # Registrar blueprints (ya los tienes)
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

    app.register_blueprint(evaluations_bp)
    app.register_blueprint(daily_stats_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(schedule_bp)
    app.register_blueprint(enrollment_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(students_bp)
    app.register_blueprint(teachers_bp)
    app.register_blueprint(courses_bp)

    return app