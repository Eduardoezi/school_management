from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.models.user import User
from app.models.user_session import UserSession
from app.utils.decorators import role_required
from app.models.institution_data import InstitutionData
from app.models.teacher import Teacher

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


# ============================================================
# USUARIOS EN LÍNEA
# ============================================================
@admin_bp.route('/users-online')
@login_required
@role_required('directivo')
def users_online():
    UserSession.cleanup_stale(minutes=30)
    online_users = User.get_online_users(minutes=5)
    active_sessions = UserSession.get_active_sessions()

    return render_template('admin/users_online.html',
                           online_users=online_users,
                           active_sessions=active_sessions)


# ============================================================
# GESTIÓN DE USUARIOS
# ============================================================
@admin_bp.route('/users')
@login_required
@role_required('directivo')
def users_list():
    users = User.get_all_with_teacher()
    return render_template('admin/users_list.html', users=users)


@admin_bp.route('/users/<int:user_id>/role', methods=['POST'])
@login_required
@role_required('directivo')
def change_role(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.users_list'))

    new_role = request.form.get('new_role')

    if new_role not in ('directivo', 'secretario', 'maestro'):
        flash('Rol no válido.', 'danger')
        return redirect(url_for('admin.users_list'))

    if user_id == current_user.id:
        flash('No puedes cambiar tu propio rol.', 'warning')
        return redirect(url_for('admin.users_list'))

    # No permitir dejar el sistema sin directivos
    if user.role == 'directivo' and new_role != 'directivo':
        conn_users = User.get_all()
        directivos = [u for u in conn_users if u['role'] == 'directivo']
        if len(directivos) <= 1:
            flash('No puedes cambiar el rol del único directivo del sistema.', 'danger')
            return redirect(url_for('admin.users_list'))

    if User.update_role(user_id, new_role):
        flash(f'Rol de "{user.username}" cambiado a {new_role}.', 'success')
    else:
        flash('Error al cambiar el rol.', 'danger')

    return redirect(url_for('admin.users_list'))


# ============================================================
# RESETEAR CONTRASEÑA
# ============================================================
@admin_bp.route('/users/<int:user_id>/reset-password', methods=['POST'])
@login_required
@role_required('directivo')
def reset_password(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.users_list'))

    if user_id == current_user.id:
        flash('Para cambiar tu propia contraseña usa "Mi perfil".', 'warning')
        return redirect(url_for('admin.users_list'))

    new_password = request.form.get('new_password', '').strip()

    if not new_password:
        flash('Debes indicar la nueva contraseña.', 'danger')
        return redirect(url_for('admin.users_list'))

    if len(new_password) < 6:
        flash('La contraseña debe tener al menos 6 caracteres.', 'danger')
        return redirect(url_for('admin.users_list'))

    if User.update_password(user_id, new_password):
        # Cerrar sesiones activas del usuario (por seguridad)
        try:
            conn = __import__('app.utils.db', fromlist=['get_db_connection']).get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_sessions SET is_active = 0, logout_time = NOW() WHERE user_id = %s AND is_active = 1",
                    (user_id,)
                )
                conn.commit()
                cursor.close()
                conn.close()
        except Exception as e:
            print(f"[reset_password] Error cerrando sesiones: {e}")

        flash(
            f'Contraseña de "{user.username}" restablecida correctamente. '
            f'Comunícala al usuario y pídele que la cambie al iniciar sesión.',
            'success'
        )
    else:
        flash('Error al restablecer la contraseña.', 'danger')

    return redirect(url_for('admin.users_list'))


# ============================================================
# DESACTIVAR / REACTIVAR
# ============================================================
@admin_bp.route('/users/<int:user_id>/deactivate', methods=['POST'])
@login_required
@role_required('directivo')
def deactivate_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.users_list'))

    if user_id == current_user.id:
        flash('No puedes desactivar tu propia cuenta.', 'warning')
        return redirect(url_for('admin.users_list'))

    if user.role == 'directivo':
        conn_users = User.get_all()
        directivos = [u for u in conn_users if u['role'] == 'directivo']
        if len(directivos) <= 1:
            flash('No puedes desactivar al único directivo del sistema.', 'danger')
            return redirect(url_for('admin.users_list'))

    if User.deactivate(user_id):
        # Cerrar sesiones activas
        try:
            conn = __import__('app.utils.db', fromlist=['get_db_connection']).get_db_connection()
            if conn:
                cursor = conn.cursor()
                cursor.execute(
                    "UPDATE user_sessions SET is_active = 0, logout_time = NOW() WHERE user_id = %s AND is_active = 1",
                    (user_id,)
                )
                conn.commit()
                cursor.close()
                conn.close()
        except Exception:
            pass

        flash(f'Usuario "{user.username}" desactivado.', 'success')
    else:
        flash('Error al desactivar el usuario.', 'danger')

    return redirect(url_for('admin.users_list'))


@admin_bp.route('/users/<int:user_id>/reactivate', methods=['POST'])
@login_required
@role_required('directivo')
def reactivate_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('Usuario no encontrado.', 'danger')
        return redirect(url_for('admin.users_list'))

    if User.reactivate(user_id):
        flash(f'Usuario "{user.username}" reactivado.', 'success')
    else:
        flash('Error al reactivar el usuario.', 'danger')

    return redirect(url_for('admin.users_list'))

# ============================================================
# DATOS INSTITUCIONALES
# ============================================================


@admin_bp.route('/institution', methods=['GET', 'POST'])
@login_required
@role_required('directivo')
def institution():
    if request.method == 'POST':
        data = {
            'nombre':                request.form.get('nombre'),
            'nombre_corto':          request.form.get('nombre_corto'),
            'codigo_dea':            request.form.get('codigo_dea'),
            'codigo_dependencia':    request.form.get('codigo_dependencia'),
            'codigo_administrativo': request.form.get('codigo_administrativo'),
            'direccion':             request.form.get('direccion'),
            'municipio':             request.form.get('municipio'),
            'estado':                request.form.get('estado'),
            'telefono':              request.form.get('telefono'),
            'email':                 request.form.get('email'),
            'rif':                   request.form.get('rif'),
            'logo_path':             request.form.get('logo_path') or 'img/logo_institucional.png'
        }
        if InstitutionData.save(data):
            flash('Datos institucionales actualizados.', 'success')
        else:
            flash('Error al guardar.', 'danger')
        return redirect(url_for('admin.institution'))

    institution = InstitutionData.get()
    director = Teacher.get_director()
    return render_template('admin/institution.html',
                           institution=institution,
                           director=director)