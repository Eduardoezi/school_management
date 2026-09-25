from app.utils.db import get_db_connection
import mysql.connector
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)

class FamilyMember:
    ROLES = ['madre', 'padre', 'tutor', 'otro']

    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM student_family
            WHERE student_id = %s
            ORDER BY FIELD(role, 'madre','padre','tutor','otro'), id
        """, (student_id,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_by_id(member_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM student_family WHERE id = %s", (member_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def create(student_id, data):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO student_family
                    (student_id, role, first_name, last_name, cedula_id,
                     age, marital_status, birth_date, birth_place,
                     education_level, profession, position, occupation,
                     address, phone, email)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (student_id, data['role'], data['first_name'], data['last_name'],
                  data.get('cedula_id'), data.get('age'), data.get('marital_status'),
                  data.get('birth_date') or None, data.get('birth_place'),
                  data.get('education_level'), data.get('profession'),
                  data.get('position'), data.get('occupation'),
                  data.get('address'), data.get('phone'), data.get('email')))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as e:
            logger.exception("Error en el Metodo create de la clase FamilyMember: %s", e)
            return None
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def update(member_id, data):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE student_family SET
                    role=%s, first_name=%s, last_name=%s, cedula_id=%s,
                    age=%s, marital_status=%s, birth_date=%s, birth_place=%s,
                    education_level=%s, profession=%s, position=%s, occupation=%s,
                    address=%s, phone=%s, email=%s
                WHERE id=%s
            """, (data['role'], data['first_name'], data['last_name'],
                  data.get('cedula_id'), data.get('age'), data.get('marital_status'),
                  data.get('birth_date') or None, data.get('birth_place'),
                  data.get('education_level'), data.get('profession'),
                  data.get('position'), data.get('occupation'),
                  data.get('address'), data.get('phone'), data.get('email'),
                  member_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            logger.exception("Error en el metodo update de la clase FamilyMember: %s", e)
            return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def delete(member_id):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM student_family WHERE id = %s", (member_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close(); conn.close()