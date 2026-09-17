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
            SELECT c.*,
                   t.first_name AS teacher_first_name,
                   t.last_name  AS teacher_last_name,
                   (SELECT COUNT(*) FROM course_teachers ct WHERE ct.course_code = c.code) AS extra_teachers
            FROM courses c
            LEFT JOIN teachers t ON c.teacher_id = t.id
            ORDER BY c.grade, c.section, c.name
        """)
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses

    @staticmethod
    def get_by_teacher(teacher_id):
        """Cursos donde el docente es titular O está asignado en la M2M."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT c.*,
                   t.first_name AS teacher_first_name,
                   t.last_name  AS teacher_last_name
            FROM courses c
            LEFT JOIN teachers t ON c.teacher_id = t.id
            LEFT JOIN course_teachers ct ON ct.course_code = c.code
            WHERE c.teacher_id = %s OR ct.teacher_id = %s
            ORDER BY c.grade, c.section, c.name
        """, (teacher_id, teacher_id))
        courses = cursor.fetchall()
        cursor.close()
        conn.close()
        return courses

    @staticmethod
    def get_by_code(course_code):
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
            # Si viene teacher_id, registrar también como titular en M2M
            if data.get('teacher_id'):
                cursor.execute("""
                    INSERT IGNORE INTO course_teachers (course_code, teacher_id, role)
                    VALUES (%s, %s, 'titular')
                """, (data['code'], data['teacher_id']))
            conn.commit()
            return {'success': True, 'code': data['code']}
        except mysql.connector.IntegrityError as e:
            if e.errno == 1062:
                return {'success': False, 'error': f'El código "{data["code"]}" ya existe.'}
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
        sql = """UPDATE courses SET 
                 name=%s, teacher_id=%s, grade=%s, section=%s, academic_year=%s
                 WHERE code=%s"""
        values = (data['name'], data.get('teacher_id'),
                  data.get('grade'), data.get('section'), data.get('academic_year'),
                  course_code)
        try:
            cursor.execute(sql, values)
            # Actualizar titular en M2M
            cursor.execute("DELETE FROM course_teachers WHERE course_code = %s AND role = 'titular'", (course_code,))
            if data.get('teacher_id'):
                cursor.execute("""
                    INSERT IGNORE INTO course_teachers (course_code, teacher_id, role)
                    VALUES (%s, %s, 'titular')
                """, (course_code, data['teacher_id']))
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

    # ============================================================
    # ASIGNACIONES M2M (titular + especialistas)
    # ============================================================
    @staticmethod
    def assign_teacher(course_code, teacher_id, role='especialista'):
        """Agrega un docente a un curso (no quita al titular)."""
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
        except Exception as e:
            print(f"[Course.assign_teacher] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def unassign_teacher(course_code, teacher_id):
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
        except Exception as e:
            print(f"[Course.unassign_teacher] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_teachers_by_course(course_code):
        """Todos los docentes de un curso (titular + M2M)."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT t.id, t.first_name, t.last_name, ct.role
            FROM course_teachers ct
            JOIN teachers t ON ct.teacher_id = t.id
            WHERE ct.course_code = %s
            ORDER BY FIELD(ct.role, 'titular','especialista','auxiliar'), t.last_name
        """, (course_code,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows