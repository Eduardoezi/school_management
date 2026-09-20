"""Decoradores de autorización por rol."""

from functools import wraps
from typing import Callable

from flask import abort, flash, redirect, request, url_for
from flask_login import current_user


def role_required(*roles: str) -> Callable:
    """Restringe el acceso a usuarios autenticados cuyo rol esté en `roles`.

    - Si no está autenticado → redirige al login (respeta ?next=).
    - Si está autenticado pero su rol no aplica → 403.

    Uso:
        @role_required('admin', 'teacher')
        def dashboard(): ...
    """
    allowed = {r.strip().lower() for r in roles if r}

    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                # Guarda la URL para volver después del login
                return redirect(url_for('auth.login', next=request.full_path))

            user_role = (getattr(current_user, "role", "") or "").strip().lower()
            if user_role not in allowed:
                flash("No tienes permisos para acceder a esa sección.", "danger")
                abort(403)

            return f(*args, **kwargs)
        return decorated_function
    return decorator