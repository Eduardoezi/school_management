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


auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


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

    # No permitir esquemas ni dominios externos.
    if parsed.scheme or parsed.netloc:
        return False

    # Solo se aceptan rutas absolutas internas.
    if not target.startswith('/'):
        return False

    # Evita redirecciones del tipo //dominio-externo.com.
    if target.startswith('//'):
        return False

    return True


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Inicia sesión para usuarios aprobados.

    Los usuarios con rol 'pendiente' no pueden iniciar sesión hasta que
    un directivo les asigne el rol definitivo.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Debes indicar tu usuario y contraseña.', 'danger')
            return render_template('login.html')

        user = User.get_by_username(username)

        if user and user.check_password(password):
            # Verificar que la cuenta esté activa.
            if not user.active:
                flash(
                    'Tu cuenta está desactivada. Contacta al directivo.',
                    'danger'
                )
                return render_template('login.html')

            # Los usuarios nuevos deben ser aprobados por un directivo.
            user_role = (user.role or '').strip().lower()

            if user_role == 'pendiente':
                flash(
                    'Tu cuenta fue registrada, pero aún debe ser aprobada '
                    'por un directivo.',
                    'warning'
                )
                return render_template('login.html')

            # Crear la sesión de Flask-Login.
            login_user(user, remember=bool(request.form.get('remember')))

            # Registrar la sesión en la base de datos.
            session['session_id'] = str(uuid.uuid4())

            UserSession.create(
                user_id=user.id,
                session_id=session['session_id'],
                ip_address=request.remote_addr,
                user_agent=(request.user_agent.string or '')[:255]
            )

            # Mantener la ruta protegida que el usuario intentaba visitar,
            # siempre que sea una ruta local y segura.
            next_page = request.args.get('next')

            if is_safe_local_url(next_page):
                return redirect(next_page)

            return redirect(url_for('main.index'))

        flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """
    Cierra la sesión del usuario y marca su sesión como inactiva.
    """
    session_id = session.get('session_id')

    if session_id:
        UserSession.close(session_id)

    logout_user()

    flash('Sesión cerrada.', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Registro público de usuarios del personal.

    El usuario no puede elegir su rol. Todas las cuentas nuevas se crean
    inicialmente con rol 'pendiente'. El directivo asignará posteriormente
    el rol definitivo desde el panel administrativo.
    """
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        teacher_id = request.form.get('teacher_id', '').strip()

        # El rol nunca se obtiene desde request.form.
        # Se define exclusivamente en el servidor.
        role = 'pendiente'

        # ---------- Validaciones básicas ----------
        if not username or not email or not password:
            flash(
                'Todos los campos obligatorios deben estar llenos.',
                'danger'
            )
            return render_template('register.html')

        if len(password) < 6:
            flash(
                'La contraseña debe tener al menos 6 caracteres.',
                'danger'
            )
            return render_template('register.html')

        # ---------- Validar cédula ----------
        if not teacher_id:
            flash(
                'Debe indicar la cédula del personal de la escuela.',
                'danger'
            )
            return render_template('register.html')

        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            flash(
                'La cédula debe ser un número válido.',
                'danger'
            )
            return render_template('register.html')

        # ---------- Verificar que exista el personal ----------
        teacher = Teacher.get_by_id(teacher_id_int)

        if not teacher:
            flash(
                f'La cédula {teacher_id} no está registrada como personal '
                'de la escuela. Contacte al directivo.',
                'danger'
            )
            return render_template('register.html')

        # ---------- Verificar usuario ya existente para esa cédula ----------
        conn = get_db_connection()

        if not conn:
            flash(
                'No fue posible conectarse con la base de datos. '
                'Intenta nuevamente más tarde.',
                'danger'
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
                (teacher_id_int,)
            )
            existente = cursor.fetchone()

        except Exception:
            flash(
                'Ocurrió un error al verificar los datos del personal.',
                'danger'
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
                'danger'
            )
            return render_template('register.html')

        # ---------- Crear usuario pendiente ----------
        user_id = User.create(
            username=username,
            email=email,
            password=password,
            role=role,
            teacher_id=teacher_id_int
        )

        if user_id:
            flash(
                'Usuario registrado exitosamente. '
                'Tu cuenta debe ser aprobada por un directivo antes '
                'de iniciar sesión.',
                'success'
            )
            return redirect(url_for('auth.login'))

        flash(
            'El nombre de usuario o el correo ya están en uso.',
            'danger'
        )

    return render_template('register.html')