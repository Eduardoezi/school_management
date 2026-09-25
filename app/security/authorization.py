"""
Motor de autorización RBAC + ABAC.

Estrategia de decisión:

    has_permission(user, permiso, recurso):

        1. ¿El usuario está autenticado?  →  no → False
        2. ¿Su rol tiene el permiso base? →  no → False
        3. ¿El permiso requiere verificar relación con el recurso?
           - No  → True
           - Sí  → Ejecuta el checker (con caché por request)

Las reglas ABAC viven en _RESOURCE_CHECKERS, indexadas por permiso.
Cada checker recibe (user, resource) y devuelve bool.
"""

import logging

from flask import g, has_request_context
from flask_login import current_user
from app.security.permissions import Permission


logger = logging.getLogger(__name__)


# ============================================================
# Excepción de autorización
# ============================================================
class AuthorizationError(Exception):
    """Se lanza cuando un usuario no está autorizado a una acción."""
    def __init__(self, message: str, required_permission: str = None):
        super().__init__(message)
        self.required_permission = required_permission


# ============================================================
# Matriz RBAC: permisos base por rol
# Las restricciones por recurso se aplican en la capa ABAC.
# ============================================================
_FULL_ACCESS_PERMISSIONS = {
    Permission.STUDENT_VIEW_BASIC,
    Permission.STUDENT_VIEW_FAMILY,
    Permission.STUDENT_VIEW_MEDICAL,
    Permission.STUDENT_VIEW_SOCIOECONOMIC,
    Permission.STUDENT_VIEW_ENROLLMENTS,
    Permission.STUDENT_VIEW_HISTORY,
    Permission.STUDENT_CREATE,
    Permission.STUDENT_EDIT_BASIC,
    Permission.STUDENT_EDIT_FAMILY,
    Permission.STUDENT_EDIT_MEDICAL,
    Permission.STUDENT_EDIT_SOCIOECONOMIC,
    Permission.STUDENT_DELETE,
    Permission.EVALUATION_VIEW,
    Permission.EVALUATION_CREATE,
    Permission.EVALUATION_EDIT,
    Permission.EVALUATION_CONFIGURE,
    Permission.DOCUMENT_ISSUE_CONSTANCIA,
    Permission.DOCUMENT_ISSUE_CERTIFICACION,
    Permission.DASHBOARD_VIEW,
    Permission.REPORT_VIEW_GLOBAL,
    Permission.DAILY_STATS_VIEW,
    Permission.DAILY_STATS_CREATE,
}

_SECRETARY_PERMISSIONS = _FULL_ACCESS_PERMISSIONS - {
    Permission.STUDENT_DELETE,
    Permission.EVALUATION_CONFIGURE,
}
# El secretario hereda DAILY_STATS_* del conjunto completo (menos los excluidos).
# No hay que hacer nada extra aquí.

_TEACHER_PERMISSIONS = {
    Permission.STUDENT_VIEW_BASIC,
    Permission.STUDENT_VIEW_FAMILY,
    Permission.STUDENT_VIEW_ENROLLMENTS,
    Permission.STUDENT_VIEW_HISTORY,
    Permission.EVALUATION_VIEW,
    Permission.EVALUATION_CREATE,
    Permission.EVALUATION_EDIT,
    Permission.DOCUMENT_ISSUE_CONSTANCIA,
    Permission.DASHBOARD_VIEW,
    Permission.DAILY_STATS_VIEW,
    Permission.DAILY_STATS_CREATE,
}


ROLE_PERMISSIONS = {
    'directivo':  _FULL_ACCESS_PERMISSIONS,
    'secretario': _SECRETARY_PERMISSIONS,
    'maestro':    _TEACHER_PERMISSIONS,
}


# ============================================================
# API pública
# ============================================================
def has_permission(user, permission: str, resource=None) -> bool:
    """
    Devuelve True si `user` puede ejecutar `permission` sobre `resource`.

    Args:
        user:       objeto User de Flask-Login.
        permission: constante de Permission.
        resource:   opcional; dict o modelo sobre el que se actúa.

    Returns:
        bool
    """
    if not user or not getattr(user, 'is_authenticated', False):
        return False

    # 1) Permiso base por rol
    allowed = ROLE_PERMISSIONS.get(user.role, frozenset())
    if permission not in allowed:
        return False

    # 2) Regla por recurso (ABAC), solo si aplica
    checker = _RESOURCE_CHECKERS.get(permission)
    if checker is None or resource is None:
        return True

    return checker(user, resource)


def authorize(permission: str, resource=None) -> None:
    """
    Como has_permission, pero lanza AuthorizationError si deniega.
    Pensado para uso en helpers y decoradores.
    """
    if not has_permission(current_user, permission, resource):
        raise AuthorizationError(
            f"Permiso denegado: {permission}",
            required_permission=permission,
        )


# ============================================================
# Registro de checkers ABAC
# ============================================================
_RESOURCE_CHECKERS = {}


def _register(*permissions):
    """Asocia el mismo checker a varios permisos."""
    def decorator(fn):
        for p in permissions:
            _RESOURCE_CHECKERS[p] = fn
        return fn
    return decorator


# ------------------------------------------------------------
# Checker unificado de acceso a un estudiante
# ------------------------------------------------------------
@_register(
    Permission.STUDENT_VIEW_BASIC,
    Permission.STUDENT_VIEW_FAMILY,
    Permission.STUDENT_VIEW_ENROLLMENTS,
    Permission.STUDENT_VIEW_HISTORY,
    Permission.EVALUATION_VIEW,
    Permission.EVALUATION_CREATE,
    Permission.EVALUATION_EDIT,
    Permission.DOCUMENT_ISSUE_CONSTANCIA,
)
def _check_student_access(user, student) -> bool:
    """
    Regla única de acceso a un estudiante.

    - Directivo/Secretario → siempre.
    - Maestro especialista → toda la matrícula.
    - Maestro regular     → solo estudiantes de sus cursos.
    """
    if user.role in ('directivo', 'secretario'):
        return True

    if user.role != 'maestro':
        return False

    teacher = _get_teacher_for_user(user)
    if not teacher:
        return False

    if _is_specialist(teacher):
        return True

    student_id = _extract_id(student)
    if student_id is None:
        return False

    return _cached_is_in_teacher_courses(student_id, teacher['id'])


# ------------------------------------------------------------
# Helpers privados
# ------------------------------------------------------------
def _extract_id(resource):
    """Extrae el 'id' de un dict o modelo sin fallar."""
    if isinstance(resource, dict):
        return resource.get('id')
    return getattr(resource, 'id', None)


def _get_teacher_for_user(user):
    from app.models.teacher import Teacher
    return Teacher.get_by_user_id(user.id)


def _is_specialist(teacher) -> bool:
    spec = teacher.get('specialist_type')
    return bool(spec and spec != 'ninguno')


def _cached_is_in_teacher_courses(student_id: int, teacher_id: int) -> bool:
    """
    Consulta con caché por request.
    Evita repetir el JOIN cuando la ruta llama varias veces al checker.
    """
    if not has_request_context():
        # Fuera de una request (scripts CLI, tests) → sin caché
        from app.models.student import Student
        return Student.is_in_teacher_courses(student_id, teacher_id)

    cache_key = f'_authz_student_{student_id}_teacher_{teacher_id}'
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached

    from app.models.student import Student
    result = Student.is_in_teacher_courses(student_id, teacher_id)
    setattr(g, cache_key, result)
    return result


# ------------------------------------------------------------
# Checker unificado de acceso a un curso
# ------------------------------------------------------------
@_register(
    Permission.DAILY_STATS_CREATE,
    Permission.DAILY_STATS_VIEW,
)
def _check_course_access(user, course) -> bool:
    """
    Regla única de acceso a un curso.

    - Directivo/Secretario → siempre.
    - Maestro especialista → siempre (ve toda la matrícula).
    - Maestro regular     → solo cursos donde es titular o está en la M2M.
    """
    if user.role in ('directivo', 'secretario'):
        return True

    if user.role != 'maestro':
        return False

    teacher = _get_teacher_for_user(user)
    if not teacher:
        return False

    if _is_specialist(teacher):
        return True

    course_code = _extract_course_code(course)
    if not course_code:
        return False

    return _cached_is_teacher_of_course(course_code, teacher['id'])


def _extract_course_code(course):
    """Extrae el 'code' de un curso sin fallar."""
    if course is None:
        return None
    if isinstance(course, dict):
        return course.get('code')
    return getattr(course, 'code', None)


def _cached_is_teacher_of_course(course_code: str, teacher_id: int) -> bool:
    """Consulta con caché por request para no repetir el chequeo."""
    if not has_request_context():
        return _query_is_teacher_of_course(course_code, teacher_id)

    cache_key = f'_authz_course_{course_code}_teacher_{teacher_id}'
    cached = getattr(g, cache_key, None)
    if cached is not None:
        return cached

    result = _query_is_teacher_of_course(course_code, teacher_id)
    setattr(g, cache_key, result)
    return result


def _query_is_teacher_of_course(course_code: str, teacher_id: int) -> bool:
    """
    Devuelve True si el docente es titular del curso o está
    asignado en course_teachers (M2M).
    """
    from app.utils.db import get_db_connection
    conn = get_db_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 FROM courses c
                LEFT JOIN course_teachers ct ON ct.course_code = c.code
                WHERE c.code = %s
                  AND (c.teacher_id = %s OR ct.teacher_id = %s)
            )
        """, (course_code, teacher_id, teacher_id))
        row = cursor.fetchone()
        return bool(row and row[0])
    except Exception as e:
        logger.exception("[_query_is_teacher_of_course] %s", e)
        return False
    finally:
        cursor.close()
        conn.close()