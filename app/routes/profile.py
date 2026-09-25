import os
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app
)
from flask_login import login_required, current_user
from PIL import Image, UnidentifiedImageError
import bcrypt

from app.models.user import User
from app.models.teacher import Teacher
from app.models.staff_detail import StaffDetail
from app.models.course import Course
from app.models.teacher_attendance import TeacherAttendance
from app.utils.db import get_db_connection

import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

AVATAR_MAX_SIZE = (400, 400)
AVATAR_QUALITY = 85


def _avatar_dir():
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')


def _delete_existing_avatars(user_id):
    folder = _avatar_dir()
    if not os.path.isdir(folder):
        return
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        ruta = os.path.join(folder, f"{user_id}.{ext}")
        if os.path.isfile(ruta):
            try:
                os.remove(ruta)
            except OSError as e:
                logger.exception("[avatar] No se pudo borrar %s", ruta)


def _process_and_save(file_storage, user_id):
    nombre_original = file_storage.filename or ''
    if '.' not in nombre_original:
        return None, "El archivo no tiene extensión válida."

    extension = nombre_original.rsplit('.', 1)[1].lower()
    if extension not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return None, "Formato no permitido. Usa JPG, PNG o WEBP."

    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.verify()
    except (UnidentifiedImageError, Exception):
        return None, "El archivo no es una imagen válida."

    file_storage.stream.seek(0)
    try:
        img = Image.open(file_storage.stream)
    except Exception:
        return None, "No se pudo procesar la imagen."

    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    else:
        img = img.convert('RGB')

    img.thumbnail(AVATAR_MAX_SIZE, Image.LANCZOS)

    folder = _avatar_dir()
    os.makedirs(folder, exist_ok=True)
    _delete_existing_avatars(user_id)

    nombre_final = f"{user_id}.jpg"
    ruta_absoluta = os.path.join(folder, nombre_final)
    img.save(ruta_absoluta, 'JPEG', quality=AVATAR_QUALITY, optimize=True)

    ruta_relativa = f"uploads/avatars/{nombre_final}"
    return ruta_relativa, None


@profile_bp.route('/', methods=['GET'])
@login_required
def index():
    """Página de perfil del usuario con todas sus secciones."""
    # Datos del docente vinculado (si aplica)
    teacher = None
    details = None
    courses_taught = []
    attendance_history = []

    if current_user.teacher_id:
        teacher = Teacher.get_by_id(current_user.teacher_id)
        if teacher:
            details = StaffDetail.get_by_teacher(current_user.teacher_id)

            # Cursos asignados
            all_courses = Course.get_all()
            courses_taught = [c for c in all_courses if c.get('teacher_id') == current_user.teacher_id]

            # Asistencia últimos 30 días
            from datetime import date, timedelta
            to_date = date.today().strftime('%Y-%m-%d')
            from_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            try:
                attendance_history = TeacherAttendance.get_by_date_range(
                    current_user.teacher_id, from_date, to_date
                )
            except Exception as e:
                logger.exception("[profile] Error attendance")

    return render_template('profile/index.html',
                           teacher=teacher,
                           details=details,
                           courses_taught=courses_taught,
                           attendance_history=attendance_history)


@profile_bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    if 'avatar' not in request.files:
        flash('No se envió ningún archivo.', 'danger')
        return redirect(url_for('profile.index'))

    file = request.files['avatar']
    if not file or file.filename == '':
        flash('Debes seleccionar una imagen.', 'danger')
        return redirect(url_for('profile.index'))

    ruta_relativa, error = _process_and_save(file, current_user.id)
    if error:
        flash(error, 'danger')
        return redirect(url_for('profile.index'))

    if User.update_avatar(current_user.id, ruta_relativa):
        current_user.avatar = ruta_relativa
        flash('Avatar actualizado correctamente.', 'success')
    else:
        flash('Error al guardar el avatar en la base de datos.', 'danger')

    return redirect(url_for('profile.index'))


@profile_bp.route('/avatar/delete', methods=['POST'])
@login_required
def delete_avatar():
    _delete_existing_avatars(current_user.id)

    if User.update_avatar(current_user.id, None):
        current_user.avatar = None
        flash('Avatar eliminado.', 'info')
    else:
        flash('Error al eliminar el avatar.', 'danger')

    return redirect(url_for('profile.index'))


@profile_bp.route('/change-password', methods=['POST'])
@login_required
def change_password():
    current_password = request.form.get('current_password', '')
    new_password = request.form.get('new_password', '')
    confirm_password = request.form.get('confirm_password', '')

    if not current_password or not new_password or not confirm_password:
        flash('Todos los campos son obligatorios.', 'danger')
        return redirect(url_for('profile.index'))

    if not current_user.check_password(current_password):
        flash('La contraseña actual no es correcta.', 'danger')
        return redirect(url_for('profile.index'))

    if len(new_password) < 6:
        flash('La nueva contraseña debe tener al menos 6 caracteres.', 'danger')
        return redirect(url_for('profile.index'))

    if new_password != confirm_password:
        flash('Las contraseñas nuevas no coinciden.', 'danger')
        return redirect(url_for('profile.index'))

    # Actualizar contraseña
    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    if conn:
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed.decode('utf-8'), current_user.id)
            )
            conn.commit()
            flash('Contraseña actualizada correctamente.', 'success')
        except Exception as e:
            logger.exception("[change_password] Error cambiando contraseña")
            flash('Error al cambiar la contraseña.', 'danger')
        finally:
            cursor.close()
            conn.close()
    else:
        flash('Error de conexión.', 'danger')

    return redirect(url_for('profile.index'))