import uuid
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required
from app.models.teacher import Teacher
from app.models.user_session import UserSession
from app.models.user import User
from flask import session
from app.models.user_session import UserSession
from app.utils.db import get_db_connection

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_by_username(username)



        if user and user.check_password(password):
            # Verifica que el usuario tenga un rol válido y no esté pendiente de aprobación
            if user.role.lower() == 'pendiente':
                flash(
                    'Tu cuenta fue registrada, pero aún debe ser aprobada por un directivo.',
                    'warning'
                )
                return render_template('login.html')
            
            # Verificar que la cuenta esté activa
            if not user.active:
                flash('Tu cuenta está desactivada. Contacta al directivo.', 'danger')
                return render_template('login.html')

            login_user(user)

            session['session_id'] = str(uuid.uuid4())
            UserSession.create(
                user_id=user.id,
                session_id=session['session_id'],
                ip_address=request.remote_addr,
                user_agent=(request.user_agent.string or '')[:255]
            )

            next_page = request.args.get('next')
            return redirect(next_page or url_for('main.dashboard'))

        flash('Usuario o contraseña incorrectos.', 'danger')
    return render_template('login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Cerrar la sesión registrada
    session_id = session.get('session_id')
    if session_id:
        UserSession.close(session_id)

    logout_user()
    flash('Sesión cerrada', 'info')
    return redirect(url_for('main.index'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        # ---------- Rol válido ----------
        # El usuario no puede seleccionar ni enviar su rol.
        # El directivo lo asignará desde el panel administrativo.
        role = 'pendiente'
        teacher_id = request.form.get('teacher_id', '').strip()


        # ---------- Validaciones básicas ----------
        if not username or not email or not password:
            flash('Todos los campos obligatorios deben estar llenos.', 'danger')
            return render_template('register.html')


        # ---------- Validar cédula del personal ----------
        if not teacher_id:
            flash('Debe indicar la cédula del personal de la escuela.', 'danger')
            return render_template('register.html')

        # Convertir a entero (la cédula es INT en teachers)
        try:
            teacher_id_int = int(teacher_id)
        except (ValueError, TypeError):
            flash('La cédula debe ser un número válido.', 'danger')
            return render_template('register.html')

        # 1. ¿Existe el docente en la tabla teachers?
        teacher = Teacher.get_by_id(teacher_id_int)
        if not teacher:
            flash(
                f'La cédula {teacher_id} no está registrada como personal '
                f'de la escuela. Contacte al directivo.',
                'danger'
            )
            return render_template('register.html')

        # 2. ¿Ya tiene un usuario asignado?
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username FROM users WHERE teacher_id = %s", (teacher_id_int,))
        existente = cursor.fetchone()
        cursor.close()
        conn.close()

        if existente:
            flash(
                f'El personal con cédula {teacher_id} ya tiene un usuario '
                f'registrado ("{existente["username"]}").',
                'danger'
            )
            return render_template('register.html')

        # ---------- Crear usuario ----------
        user_id = User.create(username, email, password, role, teacher_id_int)

        if user_id:
            flash('Usuario registrado exitosamente. Tu nivel de acceso debe ser asignado por un directivo antes de iniciar sesión.',
    'success')
            return redirect(url_for('auth.login'))

        flash('El nombre de usuario o el correo ya están en uso.', 'danger')

    return render_template('register.html')