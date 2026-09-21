"""
Modelo de cursos (grados/secciones).

Responsabilidades:
    - Consultas de cursos (listado, por código, por docente).
    - CRUD con validación.
    - Relación M2M con docentes (course_teachers).

Nota: los cursos con código NI-* son especiales (sin curso asignado).
"""

from __future__ import annotations

from typing import Optional

import mysql.connector

from app.utils.db import get_db_connection


class Course:
    """Representa un curso (grado + sección + año)."""

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_all() -> list[dict]:
        """Devuelve todos los cursos con datos del docente titular."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT c.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       CONCAT_WS(' ', t.first_name, t.last_name) AS teacher_name,
                       (SELECT COUNT(*)
                          FROM course_teachers ct
                         WHERE ct.course_code = c.code) AS extra_teachers
                  FROM courses c
                  LEFT JOIN teachers t ON c.teacher_id = t.id
                 ORDER BY c.grade, c.section, c.name
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_teacher(teacher_id: int) -> list[dict]:
        """Cursos donde el docente es titular O está asignado en M2M."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT DISTINCT c.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       CONCAT_WS(' ', t.first_name, t.last_name) AS teacher_name
                  FROM courses c
                  LEFT JOIN teachers t ON c.teacher_id = t.id
                  LEFT JOIN course_teachers ct ON ct.course_code = c.code
                 WHERE c.teacher_id = %s OR ct.teacher_id = %s
                 ORDER BY c.grade, c.section, c.name
            """, (teacher_id, teacher_id))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_code(course_code: str) -> Optional[dict]:
        """Devuelve un curso por su código o None."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT c.*,
                       t.first_name AS teacher_first_name,
                       t.last_name  AS teacher_last_name,
                       CONCAT_WS(' ', t.first_name, t.last_name) AS teacher_name
                  FROM courses c
                  LEFT JOIN teachers t ON c.teacher_id = t.id
                 WHERE c.code = %s
            """, (course_code,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def count_students(course_code: str) -> int:
        """Cuenta estudiantes inscritos activos en el curso."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT COUNT(*)
                  FROM enrollments
                 WHERE course_code = %s
                   AND status = 'activo'
            """, (course_code,))
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(data: dict) -> dict:
        """
        Crea un curso.

        Returns:
            {'success': True, 'code': str} o {'success': False, 'error': str}
        """
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión a la base de datos'}

        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO courses (name, code, teacher_id, grade, section, academic_year)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                data['name'], data['code'], data.get('teacher_id'),
                data.get('grade'), data.get('section'), data.get('academic_year'),
            ))

            if data.get('teacher_id'):
                cursor.execute("""
                    INSERT IGNORE INTO course_teachers (course_code, teacher_id, role)
                    VALUES (%s, %s, 'titular')
                """, (data['code'], data['teacher_id']))

            conn.commit()
            return {'success': True, 'code': data['code']}

        except mysql.connector.IntegrityError as exc:
            if exc.errno == 1062:
                return {'success': False,
                        'error': f'El código "{data["code"]}" ya existe.'}
            return {'success': False, 'error': f'Error de integridad: {exc}'}

        except Exception as exc:
            return {'success': False, 'error': str(exc)}

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(course_code: str, data: dict) -> dict:
        """Actualiza un curso (excepto su código, que es PK)."""
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión'}

        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE courses
                   SET name=%s, teacher_id=%s, grade=%s, section=%s, academic_year=%s
                 WHERE code=%s
            """, (
                data['name'], data.get('teacher_id'),
                data.get('grade'), data.get('section'), data.get('academic_year'),
                course_code,
            ))

            # Refrescar titular en M2M
            cursor.execute(
                "DELETE FROM course_teachers WHERE course_code = %s AND role = 'titular'",
                (course_code,),
            )
            if data.get('teacher_id'):
                cursor.execute("""
                    INSERT IGNORE INTO course_teachers (course_code, teacher_id, role)
                    VALUES (%s, %s, 'titular')
                """, (course_code, data['teacher_id']))

            conn.commit()
            return {'success': True}

        except Exception as exc:
            conn.rollback()
            return {'success': False, 'error': str(exc)}

        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(course_code: str) -> dict:
        """Elimina un curso (falla si tiene inscripciones)."""
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión'}

        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM courses WHERE code = %s", (course_code,))
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'Curso no encontrado'}
            return {'success': True}

        except mysql.connector.IntegrityError:
            conn.rollback()
            return {'success': False,
                    'error': 'El curso tiene estudiantes inscritos y no puede eliminarse.'}

        except Exception as exc:
            conn.rollback()
            return {'success': False, 'error': str(exc)}

        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Relación M2M con docentes
    # ============================================================
    @staticmethod
    def assign_teacher(course_code: str, teacher_id: int, role: str = 'especialista') -> bool:
        """Agrega un docente a un curso (sin quitar al titular)."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO course_teachers (course_code, teacher_id, role)
                VALUES (%s, %s, %s)
                ON DUPLICATE KEY UPDATE role = VALUES(role)
            """, (course_code, teacher_id, role))
            conn.commit()
            return True
        except Exception as exc:
            print(f'[Course.assign_teacher] {exc}')
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def unassign_teacher(course_code: str, teacher_id: int) -> bool:
        """Quita un docente de un curso (M2M)."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                DELETE FROM course_teachers
                 WHERE course_code = %s AND teacher_id = %s
            """, (course_code, teacher_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            print(f'[Course.unassign_teacher] {exc}')
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_teachers_by_course(course_code: str) -> list[dict]:
        """Devuelve titular + especialistas + auxiliares del curso."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT t.id, t.first_name, t.last_name, ct.role
                  FROM course_teachers ct
                  JOIN teachers t ON ct.teacher_id = t.id
                 WHERE ct.course_code = %s
                 ORDER BY FIELD(ct.role, 'titular','especialista','auxiliar'), t.last_name
            """, (course_code,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()