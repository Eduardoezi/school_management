import logging
from app.utils.db import get_db_connection
import mysql.connector

logger = logging.getLogger(__name__)

class DailyAttendanceStat:
    @staticmethod
    def get_or_create(course_code, stat_date, teacher_id, data):
        """Crea o actualiza el reporte de un curso en una fecha."""
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO daily_attendance_stats
                    (course_code, stat_date, girls_present, boys_present,
                     girls_absent, boys_absent, teacher_id, notes)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    girls_present = VALUES(girls_present),
                    boys_present  = VALUES(boys_present),
                    girls_absent  = VALUES(girls_absent),
                    boys_absent   = VALUES(boys_absent),
                    teacher_id    = VALUES(teacher_id),
                    notes         = VALUES(notes)
            """, (course_code, stat_date,
                  data.get('girls_present', 0), data.get('boys_present', 0),
                  data.get('girls_absent', 0), data.get('boys_absent', 0),
                  teacher_id, data.get('notes')))
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en get_or_create de la clase DailyAttendanceStat: %s", e)
            return False
        finally:
            cursor.close() 
            conn.close()

    @staticmethod
    def get_by_course_and_date(course_code, stat_date):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM daily_attendance_stats
            WHERE course_code = %s AND stat_date = %s
        """, (course_code, stat_date))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def get_all_by_date(stat_date):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT das.*, c.name AS course_name, c.grade, c.section,
                   t.first_name AS teacher_first_name, t.last_name AS teacher_last_name
            FROM daily_attendance_stats das
            LEFT JOIN courses c ON das.course_code = c.code
            LEFT JOIN teachers t ON das.teacher_id = t.id
            WHERE das.stat_date = %s
            ORDER BY c.grade, c.section
        """, (stat_date,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_summary_by_date(stat_date):
        """Totales por grado y general de la escuela."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.grade,
                   SUM(das.girls_present) AS niñas,
                   SUM(das.boys_present)  AS niños,
                   SUM(das.girls_present + das.boys_present) AS total
            FROM daily_attendance_stats das
            JOIN courses c ON das.course_code = c.code
            WHERE das.stat_date = %s
            GROUP BY c.grade
            ORDER BY c.grade
        """, (stat_date,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_history(from_date, to_date, course_code=None):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT das.*, c.name AS course_name, c.grade, c.section
            FROM daily_attendance_stats das
            LEFT JOIN courses c ON das.course_code = c.code
            WHERE das.stat_date BETWEEN %s AND %s
        """
        params = [from_date, to_date]
        if course_code:
            sql += " AND das.course_code = %s"
            params.append(course_code)
        sql += " ORDER BY das.stat_date DESC, c.grade, c.section"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows