"""
Decoradores de autorización para rutas Flask.

Uso típico (permiso sin recurso):
    @require(Permission.DASHBOARD_VIEW)
    def dashboard(): ...

Uso típico (permiso con recurso, aplicado fuera de la vista):
    student = get_student_or_403(student_id, Permission.STUDENT_VIEW_MEDICAL)
"""

from functools import wraps
from flask import abort, current_app, request
from flask_login import current_user

from app.security.authorization import authorize, AuthorizationError


def require(permission, resource_getter=None):
    """
    Decorador que exige un permiso para acceder a la vista.

    Args:
        permission:      constante de Permission.
        resource_getter: opcional. Callable (user, **view_kwargs) → recurso.
                         Se usa cuando la ruta necesita ABAC y quiere
                         resolver el recurso dentro del decorador.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(*args, **kwargs):
            resource = None
            if resource_getter is not None:
                resource = resource_getter(current_user, **kwargs)

            try:
                authorize(permission, resource)
            except AuthorizationError:
                current_app.logger.warning(
                    "Acceso denegado | user=%s | role=%s | permission=%s | path=%s",
                    getattr(current_user, 'id', None),
                    getattr(current_user, 'role', None),
                    permission,
                    request.path,
                )
                abort(403)

            return view_func(*args, **kwargs)
        return wrapper
    return decorator