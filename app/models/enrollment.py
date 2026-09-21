"""
Modelo de inscripciones (enrollments).

Responsabilidades:
    - CRUD de inscripciones.
    - Consultas por estudiante, por curso y matrícula histórica.
    - Gestión del ciclo académico (activo → egresado/retirado).

Estados posibles: activo, inactivo, no_inscrito, graduado, retirado.
"""

from __future__ import annotations

from typing import Optional

import mysql.connector

from app.utils.db import get_db_connection


# ============================================================
# Constantes del dominio
# ============================================================
VALID_STATUSES = ('activo', 'inactivo', 'no_inscrito', 'graduado', 'retirado')


class Enrollment:
    """Inscripción de un estudiante en un curso."""

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_all():
        """
        Devuelve todas las inscripciones con datos del estudiante y del curso.

        Campos adicionales que se agregan al dict original:
            - student_id:    id interno del estudiante (para enlaces al perfil).
            - academic_year: año académico del curso (para filtros).
            - grade, section: para mostrar en la tabla.
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT e.*,
                       s.id            AS student_id,
                       s.first_name    AS first_name,
                       s.last_name     AS last_name,
                       c.name          AS course_name,
                       c.academic_year AS academic_year,
                       c.grade         AS grade,
                       c.section       AS section
                  FROM enrollments e
                  LEFT JOIN students s ON e.school_id = s.school_id
                  LEFT JOIN courses  c ON e.course_code = c.code
                 ORDER BY e.enrollment_date DESC, e.id DESC
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(enrollment_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT e.*,
                       s.id            AS student_id,
                       s.first_name    AS first_name,
                       s.last_name     AS last_name,
                       c.name          AS course_name,
                       c.academic_year AS academic_year,
                       c.grade         AS grade,
                       c.section       AS section
                  FROM enrollments e
                  LEFT JOIN students s ON e.school_id = s.school_id
                  LEFT JOIN courses  c ON e.course_code = c.code
                 WHERE e.id = %s
            """, (enrollment_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_student(student_id: int) -> list[dict]:
        """Histórico completo de inscripciones de un estudiante."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT e.*,
                       c.name AS course_name,
                       c.grade, c.section, c.academic_year,
                       t.first_name AS teacher_first_name,
                       t.last_name AS teacher_last_name
                  FROM enrollments e
                  JOIN students s ON e.school_id = s.school_id
                  LEFT JOIN courses c ON e.course_code = c.code
                  LEFT JOIN teachers t ON c.teacher_id = t.id
                 WHERE s.id = %s
                 ORDER BY e.enrollment_date DESC
            """, (student_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def count_active() -> int:
        """Cantidad de inscripciones con estado 'activo'."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM enrollments WHERE status = 'activo'"
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_matricula(course_code: str, on_date: str) -> dict:
        """
        Cuenta estudiantes inscritos en un curso en una fecha dada.

        Filtra por:
            - enrollment_date <= on_date
            - sin egreso o con egreso_date >= on_date

        Args:
            course_code: código del curso.
            on_date: fecha en formato 'YYYY-MM-DD'.

        Returns:
            dict con claves: total, girls, boys, unknown
        """
        empty = {'total': 0, 'girls': 0, 'boys': 0, 'unknown': 0}
        conn = get_db_connection()
        if not conn:
            return empty
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT
                    COUNT(*) AS total,
                    COALESCE(SUM(CASE WHEN sd.sex = 'F' THEN 1 ELSE 0 END), 0) AS girls,
                    COALESCE(SUM(CASE WHEN sd.sex = 'M' THEN 1 ELSE 0 END), 0) AS boys,
                    COALESCE(SUM(CASE WHEN sd.sex IS NULL OR sd.sex NOT IN ('M','F')
                                      THEN 1 ELSE 0 END), 0) AS unknown
                  FROM enrollments e
                  JOIN students s ON e.school_id = s.school_id
                  LEFT JOIN student_details sd ON sd.student_id = s.id
                 WHERE e.course_code = %s
                   AND e.enrollment_date <= %s
                   AND (e.egreso_date IS NULL OR e.egreso_date >= %s)
            """, (course_code, on_date, on_date))
            return cursor.fetchone() or empty
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(data: dict) -> Optional[int]:
        """Crea una inscripción. Devuelve el ID creado o None."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO enrollments
                    (school_id, course_code, enrollment_date, status,
                     promoted, repeater, observations,
                     lopna_authorized_by, lopna_authorized_cedula,
                     lopna_tutor_cedula, lopna_reason,
                     egreso_date)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['school_id'],
                data['course_code'],
                data.get('enrollment_date'),
                data.get('status', 'activo'),
                data.get('promoted'),
                data.get('repeater'),
                data.get('observations'),
                data.get('lopna_authorized_by'),
                data.get('lopna_authorized_cedula'),
                data.get('lopna_tutor_cedula'),
                data.get('lopna_reason'),
                data.get('egreso_date'),
            ))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as exc:
            print(f'[Enrollment.create] {exc}')
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(enrollment_id: int, data: dict) -> bool:
        """Actualiza una inscripción existente."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE enrollments SET
                    school_id=%s,
                    course_code=%s,
                    enrollment_date=%s,
                    status=%s,
                    promoted=%s,
                    repeater=%s,
                    observations=%s,
                    lopna_authorized_by=%s,
                    lopna_authorized_cedula=%s,
                    lopna_tutor_cedula=%s,
                    lopna_reason=%s,
                    egreso_date=%s
                 WHERE id=%s
            """, (
                data['school_id'],
                data['course_code'],
                data.get('enrollment_date'),
                data.get('status'),
                data.get('promoted'),
                data.get('repeater'),
                data.get('observations'),
                data.get('lopna_authorized_by'),
                data.get('lopna_authorized_cedula'),
                data.get('lopna_tutor_cedula'),
                data.get('lopna_reason'),
                data.get('egreso_date'),
                enrollment_id,
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f'[Enrollment.update] {exc}')
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(enrollment_id: int) -> bool:
        """Elimina físicamente una inscripción."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM enrollments WHERE id = %s", (enrollment_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f'[Enrollment.delete] {exc}')
            return False
        finally:
            cursor.close()
            conn.close()