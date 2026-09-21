from datetime import datetime
from flask_wtf.csrf import CSRFProtect
from flask import Flask, redirect, url_for, flash, render_template, request
from flask_login import LoginManager, current_user
from app.models.teacher import Teacher
from app.config import Config
from app.models.user import User
from app.utils.db import get_db_connection


# ---------- Extensiones ----------
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Por favor inicia sesión para acceder.'
login_manager.login_message_category = 'warning'

csrf = CSRFProtect()                            

# ============================================================
# Context processors
# ============================================================
def _register_context_processors(app: Flask) -> None:
    """
    Registra variables disponibles en TODAS las plantillas.

    Inyecta:
        now           → datetime actual.
        teacher       → dict del docente vinculado o None.
        display_name  → nombre visible (docente completo o username).
        role_label    → etiqueta legible del rol.
    """
    from flask import g

    @app.context_processor
    def inject_now() -> dict:
        return {'now': datetime.now()}

    @app.context_processor
    def inject_user_display() -> dict:
        # ---------- Docente (cacheado por request) ----------
        if not hasattr(g, '_current_teacher'):
            teacher = None
            if current_user.is_authenticated:
                try:
                    teacher = Teacher.get_by_user_id(current_user.id)
                except Exception as exc:
                    app.logger.exception(
                        '[inject_user_display] Error obteniendo docente: %s', exc
                    )
                    teacher = None
            g._current_teacher = teacher

        # ---------- Nombre visible (cacheado) ----------
        if not hasattr(g, '_display_name'):
            g._display_name = _build_display_name(current_user, g._current_teacher)

        # ---------- Rol legible (cacheado) ----------
        if not hasattr(g, '_role_label'):
            g._role_label = _build_role_label(current_user)

        return {
            'teacher':      g._current_teacher,
            'display_name': g._display_name,
            'role_label':   g._role_label,
        }

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.get_by_id(int(user_id))
    except (TypeError, ValueError):
        return None


# ---------- Fábrica de la app ----------
def create_app(config_object=Config):
    app = Flask(__name__)
    app.config.from_object(config_object)

    # Inicializar extensiones
    csrf.init_app(app)                           # ← NUEVO
    login_manager.init_app(app)

    _register_blueprints(app)
    _register_error_handlers(app)
    _register_request_hooks(app)
    _register_context_processors(app)

    return app


# ---------- Helpers internos ----------
def _register_blueprints(app: Flask) -> None:
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
    from app.routes.documents import documents_bp
    from app.routes.webauthn_auth import webauthn_bp

    for bp in (
        documents_bp, auth_bp, main_bp, students_bp, enrollment_bp,
        teachers_bp, courses_bp, attendance_bp, schedule_bp,
        daily_stats_bp, evaluations_bp, admin_bp, profile_bp,
        student_profile_bp, staff_profile_bp, webauthn_bp,
    ):
        app.register_blueprint(bp)


def _register_error_handlers(app: Flask) -> None:
    @app.errorhandler(413)
    def too_large(e):
        flash('El archivo es demasiado grande. Máximo 2 MB.', 'danger')
        return redirect(request.referrer or url_for('main.index'))

    # ---------- Manejo de errores ----------
    @app.errorhandler(403)
    def forbidden(e):
        """Página 403 personalizada."""
        return render_template('errors/403.html'), 403


def _register_request_hooks(app: Flask) -> None:
    @app.before_request
    def update_last_seen():
        if request.endpoint == 'static' or not current_user.is_authenticated:
            return

        conn = get_db_connection()
        if not conn:
            return

        cursor = None
        try:
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE users SET last_seen = NOW() WHERE id = %s",
                (current_user.id,),
            )
            cursor.execute(
                """
                UPDATE user_sessions
                   SET last_activity = NOW()
                 WHERE user_id = %s AND is_active = 1
                """,
                (current_user.id,),
            )
            conn.commit()
        except Exception as exc:
            conn.rollback()
            app.logger.exception("[before_request] Error actualizando last_seen: %s", exc)
        finally:
            try:
                if cursor:
                    cursor.close()
            except Exception:
                pass
            conn.close()


# ============================================================
# Helpers de presentación
# ============================================================
def _build_display_name(user, teacher) -> str:
    """
    Construye el nombre visible del usuario.

    Reglas:
        - Usuario con docente vinculado → "Nombre Apellido".
        - Usuario sin docente            → username.
        - Usuario anónimo                → cadena vacía.

    Args:
        user:    instancia de User (puede ser anónimo).
        teacher: dict del docente o None.

    Returns:
        Cadena lista para mostrar en UI.
    """
    if not getattr(user, 'is_authenticated', False):
        return ''

    if teacher:
        parts = [teacher.get('first_name'), teacher.get('last_name')]
        full = ' '.join(p for p in parts if p)
        if full.strip():
            return full.strip()

    return user.username or ''


def _build_role_label(user) -> str:
    """
    Etiqueta legible del rol.

    Args:
        user: instancia de User.

    Returns:
        Rol capitalizado y traducido, o cadena vacía si anónimo.
    """
    if not getattr(user, 'is_authenticated', False):
        return ''

    from app.models.user import ROLE_LABELS
    return ROLE_LABELS.get(
        (user.role or '').lower(),
        user.role or '',
    )