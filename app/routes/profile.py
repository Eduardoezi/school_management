# app/routes/profile.py
import os

from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app, abort,
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
from app.utils.uploads import send_private_image
from app.security.passwords import validate_password
import logging


logger = logging.getLogger(__name__)


profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

AVATAR_MAX_SIZE = (400, 400)
AVATAR_QUALITY = 85


# ============================================================
# Helpers de avatares
# ============================================================
def _avatar_dir() -> str:
    """Carpeta donde viven los avatares (SEC-04: fuera de static/)."""
    return current_app.config['AVATAR_FOLDER']


def _delete_existing_avatars(user_id: int) -> None:
    """Elimina todas las variantes de extensión para el usuario dado."""
    folder = _avatar_dir()
    if not os.path.isdir(folder):
        return
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        ruta = os.path.join(folder, f"{user_id}.{ext}")
        if os.path.isfile(ruta):
            try:
                os.remove(ruta)
            except OSError:
                logger.exception("[avatar] No se pudo borrar %s", ruta)


def _process_and_save(file_storage, user_id: int):
    """
    Procesa y guarda el avatar del usuario.

    Returns:
        (filename, None) si OK. El filename es SOLO el nombre del archivo
        (ej. '3.jpg'), sin prefijo de carpeta.
        (None, mensaje_error) si falla.
    """
    nombre_original = file_storage.filename or ''
    if '.' not in nombre_original:
        return None, "El archivo no tiene extensión válida."

    extension = nombre_original.rsplit('.', 1)[1].lower()
    if extension not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return None, "Formato no permitido. Usa JPG, PNG o WEBP."

    # Verificar que sea imagen real (no confiar en la extensión)
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

    # Convertir a RGB con fondo blanco si hace falta
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(
            img,
            mask=img.split()[-1] if img.mode == 'RGBA' else None,
        )
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

    # Guardamos SOLO el filename en BD. La carpeta viene de config.
    return nombre_final, None


# ============================================================
# Servir avatar (SEC-04)
# ============================================================
@profile_bp.route('/avatar/<int:user_id>', methods=['GET'])
@login_required
def serve_avatar(user_id):
    """
    Sirve el avatar de un usuario autenticado.

    Requiere login. Si en el futuro querés restringir por rol,
    agregar @role_required.
    """
    user = User.get_by_id(user_id)
    if not user or not user.avatar:
        abort(404)

    return send_private_image(
        current_app.config['AVATAR_FOLDER'],
        filename=user.avatar,
        max_age=3600,
    )


# ============================================================
# Vistas
# ============================================================
@profile_bp.route('/', methods=['GET'])
@login_required
def index():
    """Página de perfil del usuario con todas sus secciones."""
    teacher = None
    details = None
    courses_taught = []
    attendance_history = []

    if current_user.teacher_id:
        teacher = Teacher.get_by_id(current_user.teacher_id)
        if teacher:
            details = StaffDetail.get_by_teacher(current_user.teacher_id)

            all_courses = Course.get_all()
            courses_taught = [
                c for c in all_courses
                if c.get('teacher_id') == current_user.teacher_id
            ]

            from datetime import date, timedelta
            to_date = date.today().strftime('%Y-%m-%d')
            from_date = (date.today() - timedelta(days=30)).strftime('%Y-%m-%d')
            try:
                attendance_history = TeacherAttendance.get_by_date_range(
                    current_user.teacher_id, from_date, to_date
                )
            except Exception:
                logger.exception("[profile] Error attendance")

    return render_template(
        'profile/index.html',
        teacher=teacher,
        details=details,
        courses_taught=courses_taught,
        attendance_history=attendance_history,
    )


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

    filename, error = _process_and_save(file, current_user.id)
    if error:
        flash(error, 'danger')
        return redirect(url_for('profile.index'))

    if User.update_avatar(current_user.id, filename):
        current_user.avatar = filename
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

    ok, errores = validate_password(new_password)
    if not ok:
        for error in errores:
            flash(error, 'danger')
        return redirect(url_for('profile.index'))

    if new_password != confirm_password:
        flash('Las contraseñas nuevas no coinciden.', 'danger')
        return redirect(url_for('profile.index'))

    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
    conn = get_db_connection()
    if not conn:
        flash('Error de conexión.', 'danger')
        return redirect(url_for('profile.index'))

    cursor = conn.cursor()
    try:
        cursor.execute(
            "UPDATE users SET password_hash = %s WHERE id = %s",
            (hashed.decode('utf-8'), current_user.id),
        )
        conn.commit()
        flash('Contraseña actualizada correctamente.', 'success')
    except Exception:
        logger.exception("[change_password] Error cambiando contraseña")
        flash('Error al cambiar la contraseña.', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('profile.index'))