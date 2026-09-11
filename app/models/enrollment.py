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