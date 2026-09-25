import logging
from app.utils.db import get_db_connection
import mysql.connector

# Re-export para compatibilidad con imports antiguos
from app.models.evaluation_period import EvaluationPeriod  # noqa: F401

logger = logging.getLogger(__name__)

class EvaluationArea:
    @staticmethod
    def get_all(only_active=True):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        sql = "SELECT * FROM evaluation_areas"
        if only_active:
            sql += " WHERE active = 1"
        sql += " ORDER BY sort_order, name"
        cursor.execute(sql)
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

# ============================================================
# Conteos de uso (para el panel de áreas)
# ============================================================

    @staticmethod
    def count_plans_using(area_id: int) -> int:
        """Cuántos planes usan esta área (plan_areas.development_area_id)."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM plan_areas WHERE development_area_id = %s",
                (area_id,)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            cursor.close()
            conn.close()


    @staticmethod
    def count_evaluations_using(area_id: int) -> int:
        """Cuántas evaluaciones usan esta área."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM evaluations WHERE area_id = %s",
                (area_id,)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            cursor.close()
            conn.close()


    @staticmethod
    def get_by_id(area_id: int):
        """Devuelve un área por su ID."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM evaluation_areas WHERE id = %s", (area_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()


    @staticmethod
    def update(area_id: int, name: str, description: str = '',
            sort_order: int = 0, active: bool = True) -> bool:
        """Actualiza un área."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE evaluation_areas
                SET name = %s,
                    description = %s,
                    sort_order = %s,
                    active = %s
                WHERE id = %s
            """, (name.strip(), (description or '').strip(),
                sort_order, 1 if active else 0, area_id))
            conn.commit()

            if cursor.rowcount > 0:
                return True
            cursor.execute("SELECT id FROM evaluation_areas WHERE id = %s", (area_id,))
            return cursor.fetchone() is not None
        except Exception as exc:
            conn.rollback()
            print(f"[EvaluationArea.update] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create(data):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO evaluation_areas (name, description, sort_order)
            VALUES (%s, %s, %s)
        """, (data['name'], data.get('description'), data.get('sort_order', 0)))
        conn.commit()
        new_id = cursor.lastrowid
        cursor.close(); conn.close()
        return new_id


class Evaluation:
    @staticmethod
    def get_by_student(student_school_id):
        """Histórico completo del estudiante."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, a.name AS area_name, p.name AS period_name,
                   p.academic_year, t.first_name AS teacher_first_name,
                   t.last_name AS teacher_last_name
            FROM evaluations e
            JOIN evaluation_areas a ON e.area_id = a.id
            JOIN evaluation_periods p ON e.period_id = p.id
            JOIN teachers t ON e.teacher_id = t.id
            WHERE e.student_school_id = %s
            ORDER BY p.academic_year DESC, p.sort_order DESC, a.sort_order
        """, (student_school_id,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_by_student_and_period(student_school_id, period_id):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, a.name AS area_name
            FROM evaluations e
            JOIN evaluation_areas a ON e.area_id = a.id
            WHERE e.student_school_id = %s AND e.period_id = %s
            ORDER BY a.sort_order
        """, (student_school_id, period_id))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def save(data):
        """Crea o actualiza una evaluación (por unique key)."""
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO evaluations
                    (student_school_id, area_id, period_id, literal,
                     description, recommendations, teacher_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    literal = VALUES(literal),
                    description = VALUES(description),
                    recommendations = VALUES(recommendations),
                    teacher_id = VALUES(teacher_id)
            """, (data['student_school_id'], data['area_id'], data['period_id'],
                  data['literal'], data['description'], data.get('recommendations'),
                  data['teacher_id']))
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en Evaluation save de la base de datos: %s", e)
            return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def get_history_grouped(student_school_id):
        """Devuelve el histórico agrupado por año y periodo, listo para plantilla."""
        rows = Evaluation.get_by_student(student_school_id)
        grouped = {}
        for r in rows:
            year = r['academic_year']
            period = r['period_name']
            grouped.setdefault(year, {}).setdefault(period, []).append(r)
        return grouped