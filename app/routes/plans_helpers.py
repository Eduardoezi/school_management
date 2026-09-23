"""
Helpers de permisos y vinculación de datos para el módulo de planes.

Centraliza TODA la lógica de autorización para que ningún endpoint
tenga que reimplementarla. Si un endpoint olvida llamar a estos
helpers, la consiguiente validación desde `plan_access_required`
falla.
"""

from __future__ import annotations

from functools import wraps

from flask import abort
from flask_login import current_user

from app.models.academic_year import AcademicYear
from app.models.classroom_plan import ClassroomPlan
from app.models.course import Course
from app.models.plan_area import PlanArea
from app.models.plan_activity import PlanActivity
from app.models.teacher import Teacher


# ============================================================
# Obtención del docente actual
# ============================================================
def get_current_teacher_or_403():
    """Devuelve el docente vinculado al usuario o aborta con 403."""
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher:
        abort(403, 'Tu usuario no está vinculado a un docente.')
    return teacher


def get_active_year_or_abort():
    """Devuelve el año escolar activo o aborta si no hay."""
    year = AcademicYear.get_active()
    if not year:
        abort(409, 'No hay un año escolar activo.')
    return year


# ============================================================
# Validación de acceso a un plan
# ============================================================
def can_view_plan(plan: dict | None) -> bool:
    """
    Puede ver el plan:
        - Directivo y secretario: cualquiera.
        - Maestro: solo los suyos.
    """
    if not plan:
        return False
    if current_user.role in ('directivo', 'secretario'):
        return True
    teacher = Teacher.get_by_user_id(current_user.id)
    return bool(teacher and plan['teacher_id'] == teacher['id'])


def can_edit_plan(plan: dict | None) -> bool:
    """
    Puede editar el plan:
        - Solo el docente autor.
        - Solo si el plan está en 'borrador' o 'devuelto'.
    """
    if not plan:
        return False
    teacher = Teacher.get_by_user_id(current_user.id)
    if not teacher or plan['teacher_id'] != teacher['id']:
        return False
    return plan['status'] in ('borrador', 'devuelto')


def can_review_plan(plan: dict | None) -> bool:
    """
    Puede revisar el plan (aprobar/devolver):
        - Solo directivo.
        - Solo si el plan está en 'enviado'.
    """
    if not plan:
        return False
    if current_user.role != 'directivo':
        return False
    return plan['status'] == 'enviado'


# ============================================================
# Asignaciones reales del docente
# ============================================================
def get_teacher_assignments(teacher_id: int, academic_year_id: int) -> list[dict]:
    """
    Devuelve los cursos que el docente tiene REALMENTE asignados
    en el año escolar dado.

    Un docente puede estar asignado como:
        - Titular (courses.teacher_id)
        - Especialista o auxiliar (course_teachers)

    Cada item incluye:
        course_code, course_name, grade, section,
        academic_year, role_in_course, enrollment_count
    """
    from app.utils.db import get_db_connection

    conn = get_db_connection()
    if not conn:
        return []

    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT
                c.code           AS course_code,
                c.name           AS course_name,
                c.grade          AS grade,
                c.section        AS section,
                c.academic_year  AS academic_year,
                CASE
                    WHEN c.teacher_id = %s THEN 'titular'
                    ELSE COALESCE(ct.role, 'especialista')
                END              AS role_in_course,
                (
                    SELECT COUNT(*)
                      FROM enrollments e
                     WHERE e.course_code = c.code
                       AND e.status = 'activo'
                )                AS enrollment_count
            FROM courses c
            LEFT JOIN course_teachers ct
                   ON ct.course_code = c.code
                  AND ct.teacher_id = %s
            WHERE c.teacher_id = %s
               OR ct.teacher_id = %s
            ORDER BY c.grade, c.section, c.name
        """, (teacher_id, teacher_id, teacher_id, teacher_id))
        return cursor.fetchall()
    finally:
        cursor.close()
        conn.close()


def teacher_can_use_course(teacher_id: int, course_code: str) -> bool:
    """Verifica si el docente tiene asignado ese curso."""
    if not course_code:
        return True  # permitir planes sin curso específico
    conn_courses = get_teacher_assignments(teacher_id, 0)
    return any(c['course_code'] == course_code for c in conn_courses)


def get_course_enrollment_count(course_code: str) -> int:
    """Cantidad de estudiantes activos en un curso."""
    if not course_code:
        return 0
    from app.utils.db import get_db_connection
    conn = get_db_connection()
    if not conn:
        return 0
    cursor = conn.cursor()
    try:
        cursor.execute(
            "SELECT COUNT(*) FROM enrollments WHERE course_code = %s AND status = 'activo'",
            (course_code,)
        )
        row = cursor.fetchone()
        return int(row[0]) if row else 0
    finally:
        cursor.close()
        conn.close()


# ============================================================
# Decorador para rutas que operan sobre un plan
# ============================================================
def plan_access_required(permission='view'):
    """
    Decorador para rutas que reciben `plan_id`.

    Uso:
        @plan_access_required('edit')
        def edit_view(plan_id): ...

    Permisos válidos: 'view', 'edit', 'review'.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            plan_id = kwargs.get('plan_id')
            if plan_id is None:
                abort(400, 'plan_id requerido')

            plan = ClassroomPlan.get_by_id(plan_id)
            if not plan:
                abort(404)

            if permission == 'view' and not can_view_plan(plan):
                abort(403)
            elif permission == 'edit' and not can_edit_plan(plan):
                abort(403)
            elif permission == 'review' and not can_review_plan(plan):
                abort(403)

            # Inyectar el plan para evitar otra consulta
            kwargs['plan'] = plan
            return f(*args, **kwargs)
        return wrapper
    return decorator


def area_access_required(permission='edit'):
    """Decorador para rutas que reciben `area_id`."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            area_id = kwargs.get('area_id')
            area = PlanArea.get_by_id(area_id)
            if not area:
                abort(404)
            plan = ClassroomPlan.get_by_id(area['plan_id'])
            if not plan or not can_edit_plan(plan):
                abort(403)
            kwargs['area'] = area
            kwargs['plan'] = plan
            return f(*args, **kwargs)
        return wrapper
    return decorator


def activity_access_required(permission='edit'):
    """Decorador para rutas que reciben `activity_id`."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            activity_id = kwargs.get('activity_id')
            activity = PlanActivity.get_by_id(activity_id)
            if not activity:
                abort(404)
            area = PlanArea.get_by_id(activity['plan_area_id'])
            plan = ClassroomPlan.get_by_id(area['plan_id']) if area else None
            if not plan or not can_edit_plan(plan):
                abort(403)
            kwargs['activity'] = activity
            kwargs['area'] = area
            kwargs['plan'] = plan
            return f(*args, **kwargs)
        return wrapper
    return decorator