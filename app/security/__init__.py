"""
Paquete de seguridad del sistema de gestión escolar.

Expone la API pública para chequeos de autorización:
    - Permission      → catálogo de permisos
    - authorize       → valida y lanza excepción si deniega
    - has_permission  → valida y devuelve booleano
    - require         → decorador para rutas sin recurso explícito
    - helpers         → utilidades get_or_403 para recursos

Diseño: RBAC + ABAC.
    - RBAC: cada rol tiene un conjunto base de permisos.
    - ABAC: cuando el recurso importa (ej: un estudiante), se verifica
      además la relación entre el usuario y ese recurso.
"""

from app.security.permissions import Permission
from app.security.authorization import (
    authorize,
    has_permission,
    AuthorizationError,
)
from app.security.decorators import require

__all__ = [
    'Permission',
    'authorize',
    'has_permission',
    'AuthorizationError',
    'require',
]