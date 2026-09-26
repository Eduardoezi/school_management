# app/utils/uploads.py
"""
Utilidades para servir archivos desde `private_uploads/`.

Regla general (SEC-04):
    Los archivos subidos NUNCA se sirven por `/static/...`. Se sirven
    por endpoints autenticados que verifican quién puede verlos.

Este módulo NO decide autorización. Solo valida:
    - Que el nombre de archivo sea seguro (sin traversal).
    - Que el archivo exista y esté dentro de la carpeta permitida.
    - El mime type básico.

La autorización (login, roles, ABAC) la aplica cada ruta que lo usa.
"""
from pathlib import Path

from flask import abort, send_file


def safe_path_within(base_dir: str, filename: str) -> Path:
    """
    Devuelve la ruta absoluta dentro de `base_dir` para `filename`,
    o aborta 404 si el nombre intenta escapar del directorio
    (path traversal, subdirectorios, nombre vacío, etc.).
    """
    if not filename:
        abort(404)

    # Solo aceptamos un nombre de archivo, sin separadores de ruta.
    if Path(filename).name != filename:
        abort(404)

    base = Path(base_dir).resolve()
    path = (base / filename).resolve()

    # Cinturón y tirantes: verificar que sigue dentro de base_dir.
    try:
        path.relative_to(base)
    except ValueError:
        abort(404)

    if not path.is_file():
        abort(404)

    return path


def send_private_image(base_dir: str, filename: str, max_age: int = 3600):
    """Sirve una imagen privada. Cache 1 hora por defecto."""
    path = safe_path_within(base_dir, filename)
    return send_file(
        path,
        mimetype=_guess_image_mimetype(path.suffix.lower()),
        max_age=max_age,
        conditional=True,
    )


def send_private_pdf(base_dir: str, filename: str, download_name: str | None = None):
    """Sirve un PDF privado como descarga."""
    path = safe_path_within(base_dir, filename)
    return send_file(
        path,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=download_name or path.name,
    )


def _guess_image_mimetype(suffix: str) -> str:
    return {
        '.jpg':  'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png':  'image/png',
        '.webp': 'image/webp',
    }.get(suffix, 'application/octet-stream')