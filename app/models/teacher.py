from app.utils.db import get_db_connection
import mysql.connector


class Teacher:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teachers ORDER BY last_name, first_name")
        teachers = cursor.fetchall()
        cursor.close()
        conn.close()
        return teachers

    @staticmethod
    def get_by_id(teacher_id):
        """Obtiene un docente por su cédula (id)."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM teachers WHERE id = %s", (teacher_id,))
        teacher = cursor.fetchone()
        cursor.close()
        conn.close()
        return teacher

    @staticmethod
    def get_by_user_id(user_id):
        """Devuelve el docente asociado a un user_id (a través de users.teacher_id)."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.* FROM teachers t
            JOIN users u ON u.teacher_id = t.id
            WHERE u.id = %s
        """, (user_id,))
        teacher = cursor.fetchone()
        cursor.close()
        conn.close()
        return teacher

    @staticmethod
    def create(data):
        """Crea un docente. data debe incluir: id (cédula), first_name, last_name, email, hire_date."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        sql = """INSERT INTO teachers (id, first_name, last_name, email, hire_date)
                 VALUES (%s, %s, %s, %s, %s)"""
        values = (data['id'], data['first_name'], data['last_name'],
                  data.get('email'), data.get('hire_date'))
        try:
            cursor.execute(sql, values)
            conn.commit()
            return data['id']
        except mysql.connector.IntegrityError as e:
            print(f"Error de integridad: {e}")
            return None
        except Exception as e:
            print(f"Error al crear docente: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(teacher_id, data):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        sql = """UPDATE teachers SET
                 first_name=%s, last_name=%s, email=%s, hire_date=%s
                 WHERE id=%s"""
        values = (data['first_name'], data['last_name'],
                  data.get('email'), data.get('hire_date'), teacher_id)
        try:
            cursor.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error al actualizar docente: {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(teacher_id):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM teachers WHERE id = %s", (teacher_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error al eliminar docente: {e}")
            return False
        finally:
            cursor.close()
            conn.close()