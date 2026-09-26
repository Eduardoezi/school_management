# app/routes/auth.py
import uuid
from urllib.parse import urlparse

from flask import (
    Blueprint,
    render_template,
    redirect,
    url_for,
    flash,
    request,
    session,
)
from flask_login import login_user, logout_user, login_required

from app.models.teacher import Teacher
from app.models.user_session import UserSession
from app.models.user import User
from app.utils.db import get_db_connection

# SEC-01: rate limiting y throttling
from app.security.rate_limit import limiter
from app.security.throttle import get_throttle_remaining, record_attempt

# SEC-02: validación centralizada de contraseñas
from app.security.passwords import validate_password


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ============================================================
# Helper: validar URL de redirección (evita open redirect)
# ============================================================
def is_safe_local_url(target: str | None) -> bool:
    """
    Verifica que la URL de redirección sea una ruta local de la aplicación.

    Acepta:
        /dashboard
        /students/
        /students/15

    Rechaza:
        https://sitio-externo.com
        http://sitio-externo.com
        //sitio-externo.com
        javascript:alert(1)
    """
    if not target:
        return False

    parsed = urlparse(target)
    if parsed.scheme or parsed.netloc:
        return False
    if not target.startswith('/'):
        return False
    if target.startswith('//'):
        return False
    return True


# ============================================================
# Helper: key_func para el rate limit por username
# ============================================================
def _login_username_key() -> str:
    """Clave de rate-limit por username (normalizado)."""
    return (request.form.get('username') or 'unknown').strip().lower()


# ============================================================
# LOGIN
# ============================================================
@auth_bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('20 per minute', methods=['POST'])
@limiter.limit('5 per minute',  methods=['POST'],
               key_func=_login_username_key)
def login():
    """
    Inicia sesión para usuarios aprobados.

    Capas de protección (SEC-01):
        1. Rate limit por IP         → 20/min
        2. Rate limit por username   → 5/min
        3. Throttling por cuenta     → tras 5 fallos, delay exponencial
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        ip = request.remote_addr or 'unknown'

        if not username or not password:
            flash('Debes indicar tu usuario y contraseña.', 'danger')
            return render_template('login.html')

        # ---- Throttling progresivo por cuenta ----
        remaining = get_throttle_remaining(username)
        if remaining > 0:
            minutos = remaining // 60
            segundos = remaining % 60
            if minutos > 0:
                espera = f'{minutos} min y {segundos}s'
            else:
                espera = f'{segundos}s'
            flash(
                f'Demasiados intentos fallidos para "{username}". '
                f'Esperá {espera} antes de reintentar.',
                'danger',
            )
            return render_template('login.html'), 429

        user = User.get_by_username(username)

        if user and user.check_password(password):
            # Verificar que la cuenta esté activa.
            if not user.active:
                record_attempt(username, ip, success=False)
                flash(
                    'Tu cuenta está desactivada. Contacta al directivo.',
                    'danger',
                )
                return render_template('login.html')

            # Los usuarios nuevos deben ser aprobados por un directivo.
            user_role = (user.role or '').strip().lower()
            if user_role == 'pendiente':
                record_attempt(username, ip, success=False)
                flash(
                    'Tu cuenta fue registrada, pero aún debe ser aprobada '
                    'por un directivo.',
                    'warning',
                )
                return render_template('login.html')

            # ---- Login exitoso: resetear throttle y crear sesión ----
            record_attempt(username, ip, success=True)

            login_user(user, remember=bool(request.form.get('remember')))

            session['session_id'] = str(uuid.uuid4())
            UserSession.create(
                user_id=user.id,
                session_id=session['session_id'],
                ip_address=request.remote_addr,
                user_agent=(request.user_agent.string or '')[:255],
            )

            next_page = request.args.get('next')
            if is_safe_local_url(next_page):
                return redirect(next_page)
            return redirect(url_for('main.index'))

        # ---- Fallo: registrar intento y mensaje genérico ----
        record_attempt(username, ip, success=False)
        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')


# ============================================================
# LOGOUT (SEC-03 — POST + CSRF)
# ============================================================
@auth_bp.route('/logout', methods=['POST'])
@login_required
def logout():
    """
    Cierra la sesión del usuario y marca su sesión como inactiva.

    Solo acepta POST con CSRF token válido. Un GET permitiría
    cerrar sesión a través de <img src="/auth/logout"> desde
    cualquier sitio externo (CSRF trivial).
    """
    session_id = session.get('session_id')

    if session_id:
        UserSession.close(session_id)

    logout_user()

    flash('Sesión cerrada.', 'info')
    return redirect(url_for('main.index'))


# ============================================================
# REGISTRO
# ============================================================
@auth_bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per hour',  methods=['POST'])
@limiter.limit('20 per day',  methods=['POST'])
def register():
    """
    Registro público de usuarios del personal.

    El usuario no puede elegir su rol. Todas las cuentas nuevas se crean
    inicialmente con rol 'pendiente'. El directivo asignará posteriormente
    el rol definitivo desde el panel administrativo.

    Protección (SEC-01): 5 registros/hora y 20/día por IP.
    Validación de contraseña (SEC-02): 12+ caracteres, mayúscula,
    minúscula, número, no filtrada (HIBP).
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        teacher_id = request.form.get('teacher_id', '').strip()

        role = 'pendiente'  # nunca se obtiene desde request.form

        # ---------- Validaciones básicas ----------
        if not username or not email or not password:
            flash(
                'Todos los campos obligatorios deben estar llenos.',
                'danger',
            )
            return render_template('register.html')

        # ---------- Validación centralizada de contraseña ----------
        ok, errores = validate_password(password)
        if not ok:
            for error in errores:
                flash(error, 'danger')
            return render_template('register.html')

        # ---------- Validar cédula ----------
        if not teacher_id:
            flash(
                'Debe indicar la cédula del personal de la escuela.',
                'danger',
            )
            return render_template('register.html')

        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            flash('La cédula debe ser un número válido.', 'danger')
            return render_template('register.html')

        # ---------- Verificar que exista el personal ----------
        teacher = Teacher.get_by_id(teacher_id_int)
        if not teacher:
            flash(
                f'La cédula {teacher_id} no está registrada como personal '
                'de la escuela. Contacte al directivo.',
                'danger',
            )
            return render_template('register.html')

        # ---------- Verificar usuario ya existente para esa cédula ----------
        conn = get_db_connection()
        if not conn:
            flash(
                'No fue posible conectarse con la base de datos. '
                'Intenta nuevamente más tarde.',
                'danger',
            )
            return render_template('register.html')

        cursor = None
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(
                """
                SELECT id, username
                FROM users
                WHERE teacher_id = %s
                """,
                (teacher_id_int,),
            )
            existente = cursor.fetchone()
        except Exception:
            flash(
                'Ocurrió un error al verificar los datos del personal.',
                'danger',
            )
            return render_template('register.html')
        finally:
            if cursor:
                cursor.close()
            conn.close()

        if existente:
            flash(
                f'El personal con cédula {teacher_id} ya tiene un usuario '
                f'registrado ("{existente["username"]}").',
                'danger',
            )
            return render_template('register.html')

        # ---------- Crear usuario pendiente ----------
        user_id = User.create(
            username=username,
            email=email,
            password=password,
            role=role,
            teacher_id=teacher_id_int,
        )

        if user_id:
            flash(
                'Usuario registrado exitosamente. '
                'Tu cuenta debe ser aprobada por un directivo antes '
                'de iniciar sesión.',
                'success',
            )
            return redirect(url_for('auth.login'))

        flash(
            'El nombre de usuario o el correo ya están en uso.',
            'danger',
        )

    return render_template('register.html')