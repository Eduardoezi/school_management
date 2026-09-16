from app.utils.db import get_db_connection
import mysql.connector

class Enrollment:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, s.first_name, s.last_name, c.name as course_name
            FROM enrollments e
            LEFT JOIN students s ON e.school_id = s.school_id
            LEFT JOIN courses c ON e.course_code = c.code
            ORDER BY e.enrollment_date DESC
        """)
        enrollments = cursor.fetchall()
        cursor.close(); conn.close()
        return enrollments

    @staticmethod
    def get_by_id(enrollment_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, s.first_name, s.last_name, c.name as course_name
            FROM enrollments e
            LEFT JOIN students s ON e.school_id = s.school_id
            LEFT JOIN courses c ON e.course_code = c.code
            WHERE e.id = %s
        """, (enrollment_id,))
        enrollment = cursor.fetchone()
        cursor.close(); conn.close()
        return enrollment

    @staticmethod
    def create(data):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        sql = """INSERT INTO enrollments 
                 (school_id, course_code, enrollment_date, status, egreso_date)
                 VALUES (%s, %s, %s, %s, %s)"""
        values = (data['school_id'], data['course_code'],
                  data.get('enrollment_date'), data.get('status', 'activo'),
                  data.get('egreso_date'))
        try:
            cursor.execute(sql, values)
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as e:
            print(f"Error: {e}")
            return None
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def update(enrollment_id, data):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        sql = """UPDATE enrollments SET 
                 school_id=%s, course_code=%s, enrollment_date=%s,
                 status=%s, egreso_date=%s
                 WHERE id=%s"""
        values = (data['school_id'], data['course_code'], data.get('enrollment_date'),
                  data.get('status'), data.get('egreso_date'), enrollment_id)
        try:
            cursor.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(e)
            return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def delete(enrollment_id):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM enrollments WHERE id = %s", (enrollment_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(e)
            return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def count_active():
        """Devuelve la cantidad de inscripciones con estado 'activo'."""
        conn = get_db_connection()
        if not conn: return 0
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM enrollments WHERE status = 'activo'")
        total = cursor.fetchone()[0]
        cursor.close(); conn.close()
        return total

    @staticmethod
    def get_by_student(student_id):
        """Devuelve todas las inscripciones (activas e históricas) de un estudiante."""
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT e.*, c.name AS course_name, c.grade, c.section,
                c.academic_year, t.first_name AS teacher_first_name,
                t.last_name AS teacher_last_name
            FROM enrollments e
            JOIN students s ON e.school_id = s.school_id
            LEFT JOIN courses c ON e.course_code = c.code
            LEFT JOIN teachers t ON c.teacher_id = t.id
            WHERE s.id = %s
            ORDER BY e.enrollment_date DESC
        """, (student_id,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows
    @staticmethod
    def get_matricula(course_code, on_date):
        """
        Devuelve cuántos estudiantes están matriculados en un curso en una fecha.
        
        Considera:
        - Inscripciones con enrollment_date <= on_date
        - Sin egreso o con egreso_date >= on_date
        - Sin importar el status actual (activo, egresado, retirado) porque
            se calcula la matrícula al momento de esa fecha.
        
        Retorna dict con: total, girls, boys, unknown
        """
        conn = get_db_connection()
        if not conn:
            return {'total': 0, 'girls': 0, 'boys': 0, 'unknown': 0}
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                COUNT(*) AS total,
                COALESCE(SUM(CASE WHEN sd.sex = 'F' THEN 1 ELSE 0 END), 0) AS girls,
                COALESCE(SUM(CASE WHEN sd.sex = 'M' THEN 1 ELSE 0 END), 0) AS boys,
                COALESCE(SUM(CASE WHEN sd.sex IS NULL OR sd.sex NOT IN ('M','F') THEN 1 ELSE 0 END), 0) AS unknown
            FROM enrollments e
            JOIN students s ON e.school_id = s.school_id
            LEFT JOIN student_details sd ON sd.student_id = s.id
            WHERE e.course_code = %s
            AND e.enrollment_date <= %s
            AND (e.egreso_date IS NULL OR e.egreso_date >= %s)
        """, (course_code, on_date, on_date))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row or {'total': 0, 'girls': 0, 'boys': 0, 'unknown': 0}