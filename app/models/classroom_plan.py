"""
Modelo del plan de aula.

Estructura:
    classroom_plans      → un plan (cabecera)
        plan_areas       → áreas de formación del plan
            plan_activities → actividades pedagógicas por área

Reglas:
    - Un docente solo puede ver/editar SUS planes.
    - Un plan solo puede editarse si está en estado 'borrador' o 'devuelto'.
    - Al enviar, pasa a 'enviado'.
    - El director (o secretario, si se autoriza) revisa y cambia a
      'aprobado' o 'devuelto' con comentario.
    - Cuando se aprueba, se publica (Fase 4) → 'publicado'.
    - El soft delete usa `deleted_at`.
"""

from __future__ import annotations

from typing import Optional

import mysql.connector

from app.utils.db import get_db_connection


# ============================================================
# Constantes
# ============================================================
PLANNING_TYPES = ('semanal', 'quincenal', 'mensual', 'bimensual', 'trimestral')
TEACHER_ROLES  = ('titular', 'especialista', 'auxiliar')
LOCATION_TYPES = ('aula', 'fuera_aula', 'ambos')
STATUSES       = ('borrador', 'enviado', 'devuelto', 'aprobado', 'publicado', 'archivado')

EDITABLE_STATUSES = ('borrador', 'devuelto')


class ClassroomPlan:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_by_id(plan_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT p.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       ay.name      AS academic_year_name,
                       c.name       AS course_name
                  FROM classroom_plans p
                  JOIN teachers       t  ON p.teacher_id = t.id
                  JOIN academic_years ay ON p.academic_year_id = ay.id
                  LEFT JOIN courses   c  ON p.course_code = c.code
                 WHERE p.id = %s AND p.deleted_at IS NULL
            """, (plan_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_teacher(teacher_id: int,
                       academic_year_id: Optional[int] = None,
                       include_archived: bool = False) -> list[dict]:
        """Planes de un docente. Por defecto excluye archivados."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT p.*,
                       ay.name AS academic_year_name,
                       c.name  AS course_name
                  FROM classroom_plans p
                  JOIN academic_years ay ON p.academic_year_id = ay.id
                  LEFT JOIN courses   c  ON p.course_code = c.code
                 WHERE p.teacher_id = %s
                   AND p.deleted_at IS NULL
            """
            params: list = [teacher_id]

            if academic_year_id:
                sql += " AND p.academic_year_id = %s"
                params.append(academic_year_id)

            if not include_archived:
                sql += " AND p.status <> 'archivado'"

            sql += " ORDER BY p.start_date DESC, p.id DESC"

            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_pending_review(academic_year_id: Optional[int] = None) -> list[dict]:
        """Planes en estado 'enviado' que esperan revisión del director."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT p.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       ay.name      AS academic_year_name,
                       c.name       AS course_name
                  FROM classroom_plans p
                  JOIN teachers       t  ON p.teacher_id = t.id
                  JOIN academic_years ay ON p.academic_year_id = ay.id
                  LEFT JOIN courses   c  ON p.course_code = c.code
                 WHERE p.status = 'enviado'
                   AND p.deleted_at IS NULL
            """
            params: list = []
            if academic_year_id:
                sql += " AND p.academic_year_id = %s"
                params.append(academic_year_id)
            sql += " ORDER BY p.submitted_at ASC"
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_academic_year(academic_year_id: int,
                             include_archived: bool = False) -> list[dict]:
        """
        Todos los planes de un año escolar (para la bandeja del director).
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT p.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       c.name       AS course_name,
                       ay.name      AS academic_year_name
                  FROM classroom_plans p
                  JOIN teachers       t  ON p.teacher_id = t.id
                  JOIN academic_years ay ON p.academic_year_id = ay.id
                  LEFT JOIN courses   c  ON p.course_code = c.code
                 WHERE p.academic_year_id = %s
                   AND p.deleted_at IS NULL
            """
            params: list = [academic_year_id]
            if not include_archived:
                sql += " AND p.status <> 'archivado'"
            sql += " ORDER BY p.submitted_at DESC, p.id DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Crear / actualizar cabecera
    # ============================================================
    @staticmethod
    def create(data: dict) -> Optional[int]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO classroom_plans (
                    academic_year_id, teacher_id, teacher_role_in_plan,
                    course_code, grade, section,
                    planning_type, pedagogical_moment,
                    start_date, end_date, location_type, enrollment_count,
                    situational_diagnosis, theoretical_foundation,
                    learning_project_title, purposes, research_line,
                    general_observations, status
                ) VALUES (
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, 'borrador'
                )
            """, (
                data['academic_year_id'],
                data['teacher_id'],
                data.get('teacher_role_in_plan', 'titular'),
                data.get('course_code') or None,
                data.get('grade') or None,
                data.get('section') or None,
                data.get('planning_type', 'semanal'),
                data.get('pedagogical_moment') or None,
                data['start_date'],
                data['end_date'],
                data.get('location_type', 'aula'),
                data.get('enrollment_count') or None,
                data.get('situational_diagnosis') or None,
                data.get('theoretical_foundation') or None,
                data.get('learning_project_title') or None,
                data.get('purposes') or None,
                data.get('research_line') or None,
                data.get('general_observations') or None,
            ))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as exc:
            conn.rollback()
            print(f"[ClassroomPlan.create] {exc}")
            return None
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.create] {exc}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(plan_id: int, data: dict) -> bool:
        if not ClassroomPlan.is_editable(plan_id):
            return False
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans SET
                    course_code            = %s,
                    grade                  = %s,
                    section                = %s,
                    planning_type          = %s,
                    pedagogical_moment      = %s,
                    start_date             = %s,
                    end_date               = %s,
                    location_type          = %s,
                    enrollment_count       = %s,
                    situational_diagnosis  = %s,
                    theoretical_foundation = %s,
                    learning_project_title = %s,
                    purposes               = %s,
                    research_line          = %s,
                    general_observations   = %s
                 WHERE id = %s AND deleted_at IS NULL
            """, (
                data.get('course_code') or None,
                data.get('grade') or None,
                data.get('section') or None,
                data.get('planning_type', 'semanal'),
                data.get('pedagogical_moment') or None,
                data['start_date'],
                data['end_date'],
                data.get('location_type', 'aula'),
                data.get('enrollment_count') or None,
                data.get('situational_diagnosis') or None,
                data.get('theoretical_foundation') or None,
                data.get('learning_project_title') or None,
                data.get('purposes') or None,
                data.get('research_line') or None,
                data.get('general_observations') or None,
                plan_id,
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.update] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Cambios de estado
    # ============================================================
    @staticmethod
    def is_editable(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT status FROM classroom_plans
                 WHERE id = %s AND deleted_at IS NULL
            """, (plan_id,))
            row = cursor.fetchone()
            if not row:
                return False
            return row['status'] in EDITABLE_STATUSES
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def submit_for_review(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans
                   SET status = 'enviado',
                       submitted_at = NOW()
                 WHERE id = %s
                   AND status IN ('borrador','devuelto')
                   AND deleted_at IS NULL
            """, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.submit_for_review] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def approve(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans
                   SET status = 'aprobado',
                       approved_at = NOW()
                 WHERE id = %s
                   AND status = 'enviado'
                   AND deleted_at IS NULL
            """, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.approve] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def return_for_correction(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans
                   SET status = 'devuelto'
                 WHERE id = %s
                   AND status = 'enviado'
                   AND deleted_at IS NULL
            """, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.return_for_correction] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def publish(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans
                   SET status = 'publicado'
                 WHERE id = %s
                   AND status = 'aprobado'
                   AND deleted_at IS NULL
            """, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.publish] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def archive(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans
                   SET status = 'archivado'
                 WHERE id = %s AND deleted_at IS NULL
            """, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.archive] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def soft_delete(plan_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE classroom_plans
                   SET deleted_at = NOW()
                 WHERE id = %s AND deleted_at IS NULL
            """, (plan_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[ClassroomPlan.soft_delete] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()