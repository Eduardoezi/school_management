"""
Helpers reutilizables para rutas.

Patrón principal: obtener un recurso garantizando autorización.
Si el recurso no existe o el usuario no puede verlo, se deniega
sin revelar la diferencia (anti-enumeración).
"""

from flask import abort, current_app, request
from flask_login import current_user

from app.models.student import Student
from app.security.authorization import authorize, AuthorizationError
from app.security.permissions import Permission


def get_student_or_403(student_id: int, permission: str = Permission.STUDENT_VIEW_BASIC):
    """
    Devuelve el estudiante si el usuario actual puede accederlo.

    Args:
        student_id: id interno del estudiante.
        permission: permiso requerido (por defecto STUDENT_VIEW_BASIC).

    Raises:
        403: si el estudiante no existe o el usuario no tiene permiso.
              Se unifica para no revelar existencia de IDs ajenos.
    """
    student = Student.get_by_id(student_id)
    if not student:
        abort(403)

    try:
        authorize(permission, student)
    except AuthorizationError:
        current_app.logger.warning(
            "Acceso denegado a estudiante | user=%s | role=%s | student_id=%s | permission=%s | path=%s",
            current_user.id,
            current_user.role,
            student_id,
            permission,
            request.path,
        )
        abort(403)

    return student


def assert_family_belongs_to_student(member_id: int, student_id: int):
    """
    Verifica que un familiar pertenezca al estudiante indicado.
    Lanza 403 si no coincide (defensa contra IDOR).
    """
    from app.models.family_member import FamilyMember
    member = FamilyMember.get_by_id(member_id)
    if not member or member['student_id'] != student_id:
        current_app.logger.warning(
            "IDOR bloqueado | user=%s | member_id=%s | student_id=%s | path=%s",
            current_user.id, member_id, student_id, request.path,
        )
        abort(403)
    return member

def get_course_or_403(course_code: str, permission: str = Permission.DAILY_STATS_CREATE):
    """
    Devuelve el curso si el usuario actual puede accederlo.

    Args:
        course_code: código del curso (clave primaria en `courses`).
        permission:  permiso requerido.

    Raises:
        403: si el curso no existe o el usuario no tiene permiso.
             Se unifica para no revelar la existencia de cursos ajenos.
    """
    from app.models.course import Course

    course = Course.get_by_code(course_code)
    if not course:
        abort(403)

    try:
        authorize(permission, course)
    except AuthorizationError:
        current_app.logger.warning(
            "Acceso denegado a curso | user=%s | role=%s | course_code=%s | permission=%s | path=%s",
            current_user.id,
            current_user.role,
            course_code,
            permission,
            request.path,
        )
        abort(403)

    return course