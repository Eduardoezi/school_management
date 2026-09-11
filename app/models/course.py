from app.utils.db import get_db_connection
import mysql.connector

class Course:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, t.first_name as teacher_first_name, t.last_name as teacher_last_name
            FROM courses c
            LEFT JOIN teachers t ON c.teacher_id = t.id
            ORDER BY c.name
        """)
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses

    @staticmethod
    def get_by_code(course_code):
        """Obtiene un curso por su código (clave primaria)"""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT c.*, t.first_name as teacher_first_name, t.last_name as teacher_last_name
            FROM courses c
            LEFT JOIN teachers t ON c.teacher_id = t.id
            WHERE c.code = %s
        """, (course_code,))
        course = cursor.fetchone()
        cursor.close()
        conn.close()
        return course

    @staticmethod
    def create(data):
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión a la base de datos'}
        cursor = conn.cursor()
        sql = """INSERT INTO courses 
                 (name, code, teacher_id, grade, section, academic_year)
                 VALUES (%s, %s, %s, %s, %s, %s)"""
        values = (data['name'], data['code'], data.get('teacher_id'),
                  data.get('grade'), data.get('section'), data.get('academic_year'))
        try:
            cursor.execute(sql, values)
            conn.commit()
            return {'success': True, 'code': data['code']}
        except mysql.connector.IntegrityError as e:
            if e.errno == 1062:
                return {'success': False, 'error': f'El código "{data["code"]}" ya existe en la base de datos.'}
            else:
                return {'success': False, 'error': f'Error de integridad: {e}'}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(course_code, data):
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión'}
        cursor = conn.cursor()
        # El código no se actualiza (es clave primaria), solo el resto de campos
        sql = """UPDATE courses SET 
                 name=%s, teacher_id=%s, grade=%s, section=%s, academic_year=%s
                 WHERE code=%s"""
        values = (data['name'], data.get('teacher_id'),
                  data.get('grade'), data.get('section'), data.get('academic_year'),
                  course_code)
        try:
            cursor.execute(sql, values)
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'No se encontró el curso o no hubo cambios'}
            return {'success': True}
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(course_code):
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
        except Exception as e:
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            conn.close()