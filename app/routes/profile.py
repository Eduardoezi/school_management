import os
import uuid
from flask import (
    Blueprint, render_template, redirect, url_for, flash,
    request, current_app
)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from PIL import Image, UnidentifiedImageError

from app.models.user import User

profile_bp = Blueprint('profile', __name__, url_prefix='/profile')

AVATAR_MAX_SIZE = (400, 400)   # píxeles máximos (ancho x alto)
AVATAR_QUALITY = 85            # calidad JPEG


def _avatar_dir():
    """Devuelve la ruta absoluta de la carpeta de avatares."""
    return os.path.join(current_app.config['UPLOAD_FOLDER'], 'avatars')


def _delete_existing_avatars(user_id):
    """Elimina cualquier avatar previo del usuario (sin importar extensión)."""
    folder = _avatar_dir()
    if not os.path.isdir(folder):
        return
    for ext in ('jpg', 'jpeg', 'png', 'webp'):
        ruta = os.path.join(folder, f"{user_id}.{ext}")
        if os.path.isfile(ruta):
            try:
                os.remove(ruta)
            except OSError as e:
                print(f"[avatar] No se pudo borrar {ruta}: {e}")


def _process_and_save(file_storage, user_id):
    """
    Valida, procesa y guarda la imagen.
    Devuelve la ruta relativa (ej. 'uploads/avatars/3.jpg') o None si falla.
    """
    # ---------- 1. Extensión permitida ----------
    nombre_original = file_storage.filename or ''
    if '.' not in nombre_original:
        return None, "El archivo no tiene extensión válida."

    extension = nombre_original.rsplit('.', 1)[1].lower()
    if extension not in current_app.config['ALLOWED_IMAGE_EXTENSIONS']:
        return None, "Formato no permitido. Usa JPG, PNG o WEBP."

    # ---------- 2. Abrir con Pillow para verificar que es imagen real ----------
    try:
        file_storage.stream.seek(0)
        img = Image.open(file_storage.stream)
        img.verify()                       # detecta archivos corruptos
    except (UnidentifiedImageError, Exception):
        return None, "El archivo no es una imagen válida."

    # Volver a abrir (verify() cierra el stream)
    file_storage.stream.seek(0)
    try:
        img = Image.open(file_storage.stream)
    except Exception:
        return None, "No se pudo procesar la imagen."

    # ---------- 3. Normalizar formato (siempre JPEG) ----------
    # Los PNG con transparencia se aplanan sobre fondo blanco
    if img.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', img.size, (255, 255, 255))
        background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
        img = background
    else:
        img = img.convert('RGB')

    # ---------- 4. Redimensionar manteniendo aspecto ----------
    img.thumbnail(AVATAR_MAX_SIZE, Image.LANCZOS)

    # ---------- 5. Guardar ----------
    folder = _avatar_dir()
    os.makedirs(folder, exist_ok=True)

    # Eliminar cualquier archivo anterior del mismo usuario
    _delete_existing_avatars(user_id)

    # Nombre final: {user_id}.jpg
    nombre_final = f"{user_id}.jpg"
    ruta_absoluta = os.path.join(folder, nombre_final)

    img.save(ruta_absoluta, 'JPEG', quality=AVATAR_QUALITY, optimize=True)

    # Ruta relativa que guardamos en BD
    ruta_relativa = f"uploads/avatars/{nombre_final}"
    return ruta_relativa, None


@profile_bp.route('/', methods=['GET'])
@login_required
def index():
    """Página de perfil del usuario."""
    return render_template('profile/index.html')


@profile_bp.route('/avatar', methods=['POST'])
@login_required
def upload_avatar():
    # ---------- Verificar que llegó un archivo ----------
    if 'avatar' not in request.files:
        flash('No se envió ningún archivo.', 'danger')
        return redirect(url_for('profile.index'))

    file = request.files['avatar']
    if not file or file.filename == '':
        flash('Debes seleccionar una imagen.', 'danger')
        return redirect(url_for('profile.index'))

    # ---------- Procesar y guardar ----------
    ruta_relativa, error = _process_and_save(file, current_user.id)
    if error:
        flash(error, 'danger')
        return redirect(url_for('profile.index'))

    # ---------- Actualizar la BD ----------
    if User.update_avatar(current_user.id, ruta_relativa):
        # Refrescar el objeto en memoria para que current_user lo vea al instante
        current_user.avatar = ruta_relativa
        flash('Avatar actualizado correctamente.', 'success')
    else:
        flash('Error al guardar el avatar en la base de datos.', 'danger')

    return redirect(url_for('profile.index'))


@profile_bp.route('/avatar/delete', methods=['POST'])
@login_required
def delete_avatar():
    """Elimina el avatar del usuario."""
    _delete_existing_avatars(current_user.id)

    if User.update_avatar(current_user.id, None):
        current_user.avatar = None
        flash('Avatar eliminado.', 'info')
    else:
        flash('Error al eliminar el avatar.', 'danger')

    return redirect(url_for('profile.index'))