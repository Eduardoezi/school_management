"""
Registro anecdótico del estudiante.

Complementa la evaluación de período. Mientras la evaluación tiene un
literal (L/EP/PL) por área y lapso, la anécdota es una observación
puntual asociada opcionalmente a una actividad específica del plan de aula.

Reglas:
    - Un docente solo ve/edita las anécdotas que él mismo registró.
    - Los directivos y secretarios pueden ver todas.
    - Si se elimina la actividad referenciada, la anécdota se conserva
      (plan_activity_id queda NULL).
"""
from __future__ import annotations
import logging
from typing import Optional
import mysql.connector
from app.utils.db import get_db_connection

logger = logging.getLogger(__name__)

class AnecdotalRecord:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_by_id(record_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT ar.*,
                       s.first_name  AS student_first_name,
                       s.last_name   AS student_last_name,
                       t.first_name  AS teacher_first_name,
                       t.last_name   AS teacher_last_name,
                       pa.title      AS activity_title,
                       plan.id       AS plan_id,
                       plan.learning_project_title AS plan_title
                  FROM anecdotal_records ar
                  JOIN students s        ON ar.student_school_id = s.school_id
                  JOIN teachers t        ON ar.teacher_id = t.id
                  LEFT JOIN plan_activities pa ON ar.plan_activity_id = pa.id
                  LEFT JOIN plan_areas      area ON pa.plan_area_id = area.id
                  LEFT JOIN classroom_plans plan ON area.plan_id = plan.id
                 WHERE ar.id = %s
            """, (record_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_student(student_school_id: str,
                       teacher_id: Optional[int] = None,
                       limit: int = 100) -> list[dict]:
        """
        Anécdotas de un estudiante.
        Si `teacher_id` se pasa, filtra por ese docente.
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT ar.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       pa.title     AS activity_title
                  FROM anecdotal_records ar
                  JOIN teachers t        ON ar.teacher_id = t.id
                  LEFT JOIN plan_activities pa ON ar.plan_activity_id = pa.id
                 WHERE ar.student_school_id = %s
            """
            params: list = [student_school_id]

            if teacher_id is not None:
                sql += " AND ar.teacher_id = %s"
                params.append(teacher_id)

            sql += " ORDER BY ar.observed_at DESC, ar.id DESC LIMIT %s"
            params.append(limit)

            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_activity(activity_id: int) -> list[dict]:
        """Todas las anécdotas registradas para una actividad."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT ar.*,
                       s.first_name AS student_first_name,
                       s.last_name  AS student_last_name
                  FROM anecdotal_records ar
                  JOIN students s ON ar.student_school_id = s.school_id
                 WHERE ar.plan_activity_id = %s
                 ORDER BY s.last_name, s.first_name, ar.observed_at DESC
            """, (activity_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_period(student_school_id: str, start_date, end_date,
                      teacher_id: Optional[int] = None) -> list[dict]:
        """
        Anécdotas de un estudiante en un rango de fechas (ej: un lapso).
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = """
                SELECT ar.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       pa.title     AS activity_title
                  FROM anecdotal_records ar
                  JOIN teachers t        ON ar.teacher_id = t.id
                  LEFT JOIN plan_activities pa ON ar.plan_activity_id = pa.id
                 WHERE ar.student_school_id = %s
                   AND ar.observed_at BETWEEN %s AND %s
            """
            params: list = [student_school_id, start_date, end_date]

            if teacher_id is not None:
                sql += " AND ar.teacher_id = %s"
                params.append(teacher_id)

            sql += " ORDER BY ar.observed_at DESC"
            cursor.execute(sql, params)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(data: dict) -> Optional[int]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO anecdotal_records (
                    student_school_id, plan_activity_id, observed_at,
                    observation, recommendation, teacher_id
                ) VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                data['student_school_id'],
                data.get('plan_activity_id') or None,
                data['observed_at'],
                data['observation'],
                data.get('recommendation') or None,
                data['teacher_id'],
            ))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as exc:
            conn.rollback()
            logger.exception("Error de integridad en AnecdotalRecord.create: %s", exc)
            return None
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en AnecdotalRecord.create: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(record_id: int, data: dict) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE anecdotal_records SET
                    observed_at     = %s,
                    observation     = %s,
                    recommendation  = %s,
                    plan_activity_id = %s
                 WHERE id = %s
            """, (
                data['observed_at'],
                data['observation'],
                data.get('recommendation') or None,
                data.get('plan_activity_id') or None,
                record_id,
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en AnecdotalRecord.update: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(record_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM anecdotal_records WHERE id = %s", (record_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en AnecdotalRecord.delete: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def count_by_student(student_school_id: str) -> int:
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM anecdotal_records WHERE student_school_id = %s",
                (student_school_id,)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            cursor.close()
            conn.close()