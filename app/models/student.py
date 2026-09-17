from app.utils.db import get_db_connection
from datetime import datetime
import mysql.connector

class Student:
    @staticmethod
    def generate_school_id(multiple_birth_order, birth_date, representative_cedula):
        if not birth_date or not representative_cedula:
            return None
        try:
            if isinstance(birth_date, str):
                birth_date = datetime.strptime(birth_date, '%Y-%m-%d')
            year_two_digits = birth_date.strftime('%y')
        except Exception:
            return None
        cedula_limpia = str(representative_cedula).replace('-', '').replace('V', '').replace('E', '').strip()
        return f"{multiple_birth_order}{year_two_digits}{cedula_limpia}"

    @staticmethod
    def get_all_with_details(course_code=None, status=None):
        """
        Devuelve estudiantes con sus datos vinculados.
        
        Parámetros:
            course_code (str): si se especifica, solo estudiantes de ese curso.
            status (str): 'activo' para solo inscritos activos, None para todos.
        """
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)

        sql = """
            SELECT s.*,
                r.first_name AS rep_first_name, r.last_name AS rep_last_name,
                r.phone AS rep_phone, r.cedula_id AS rep_cedula,
                c.name AS course_name, c.code AS course_code,
                e.status AS enrollment_status
            FROM students s
            LEFT JOIN representatives r ON s.representative_cedula = r.cedula_id
            LEFT JOIN enrollments e ON s.school_id = e.school_id
            LEFT JOIN courses c ON e.course_code = c.code
            WHERE 1=1
        """
        params = []

        if course_code:
            sql += " AND e.course_code = %s"
            params.append(course_code)

        if status:
            sql += " AND e.status = %s"
            params.append(status)

        sql += " ORDER BY s.last_name, s.first_name"

        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_by_id(student_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*,
                r.cedula_id     AS rep_cedula_id,
                r.first_name    AS rep_first_name,
                r.last_name     AS rep_last_name,
                r.email         AS rep_email,
                r.phone         AS rep_phone,
                r.address       AS rep_address,
                r.relationship  AS rep_relationship,
                c.code          AS course_code,
                c.name          AS course_name,
                e.status        AS enrollment_status
            FROM students s
            LEFT JOIN representatives r ON s.representative_cedula = r.cedula_id
            LEFT JOIN enrollments e ON s.school_id = e.school_id AND e.status = 'activo'
            LEFT JOIN courses c ON e.course_code = c.code
            WHERE s.id = %s
        """, (student_id,))
        student = cursor.fetchone()
        cursor.close()
        conn.close()
        return student

    @staticmethod
    def create_full(data):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        try:
            school_id = Student.generate_school_id(
                data.get('multiple_birth_order', 1),
                data.get('birth_date'),
                data.get('representative_cedula')
            )
            if not school_id:
                return None

            # Insertar estudiante SIN course_code
            sql = """INSERT INTO students 
                     (school_id, first_name, last_name, multiple_birth_order, birth_date,
                      representative_cedula, disability)
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            values = (school_id, data['first_name'], data['last_name'],
                      data.get('multiple_birth_order', 1), data.get('birth_date'),
                      data.get('representative_cedula'), data.get('disability'))
            cursor.execute(sql, values)

            # Si se proporcionó curso, crear la inscripción activa
            if data.get('course_code'):
                sql_enr = """INSERT INTO enrollments 
                             (school_id, course_code, enrollment_date, status)
                             VALUES (%s, %s, CURDATE(), 'activo')"""
                cursor.execute(sql_enr, (school_id, data['course_code']))

            conn.commit()
            return school_id
        except mysql.connector.IntegrityError as e:
            print(f"Error de integridad: {e}")
            conn.rollback()
            return None
        except Exception as e:
            print(f"Error al crear estudiante: {e}")
            conn.rollback()
            return None
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def update_full(student_id, data):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            nueva_cedula = data['representative_cedula']

            # 1. Verificar si ya existe un representante con esa cédula
            cursor.execute("SELECT cedula_id FROM representatives WHERE cedula_id = %s", (nueva_cedula,))
            existe = cursor.fetchone()

            if not existe:
                # No existe: buscar cuál era la cédula anterior del estudiante
                cursor.execute("SELECT representative_cedula FROM students WHERE id = %s", (student_id,))
                row = cursor.fetchone()
                cedula_anterior = row[0] if row else None

                if cedula_anterior:
                    # Actualizar el representante actual cambiándole la cédula
                    cursor.execute("""
                        UPDATE representatives SET
                            cedula_id=%s, first_name=%s, last_name=%s,
                            email=%s, phone=%s, address=%s, relationship=%s
                        WHERE cedula_id=%s
                    """, (nueva_cedula, data['rep_first_name'], data['rep_last_name'],
                        data.get('rep_email'), data.get('rep_phone'),
                        data.get('rep_address'), data.get('rep_relationship'),
                        cedula_anterior))
                else:
                    # No había representante: crear uno nuevo
                    cursor.execute("""
                        INSERT INTO representatives
                            (cedula_id, first_name, last_name, email, phone, address, relationship)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (nueva_cedula, data['rep_first_name'], data['rep_last_name'],
                        data.get('rep_email'), data.get('rep_phone'),
                        data.get('rep_address'), data.get('rep_relationship')))
            else:
                # Ya existe: actualizamos sus datos por si el usuario los editó
                cursor.execute("""
                    UPDATE representatives SET
                        first_name=%s, last_name=%s, email=%s, phone=%s, address=%s, relationship=%s
                    WHERE cedula_id=%s
                """, (data['rep_first_name'], data['rep_last_name'],
                    data.get('rep_email'), data.get('rep_phone'),
                    data.get('rep_address'), data.get('rep_relationship'),
                    nueva_cedula))

            # 2. Actualizar el estudiante
            cursor.execute("""
                UPDATE students SET
                    first_name=%s, last_name=%s, multiple_birth_order=%s,
                    birth_date=%s, representative_cedula=%s, disability=%s
                WHERE id=%s
            """, (data['first_name'], data['last_name'], data.get('multiple_birth_order', 1),
                data.get('birth_date'), nueva_cedula,
                data.get('disability'), student_id))

            # 3. Sincronizar curso con enrollments
            cursor.execute("SELECT school_id FROM students WHERE id = %s", (student_id,))
            row = cursor.fetchone()
            if row:
                school_id = row[0]
                cursor.execute("""
                    SELECT course_code FROM enrollments
                    WHERE school_id = %s AND status = 'activo'
                """, (school_id,))
                current = cursor.fetchone()
                curso_actual = current[0] if current else None
                nuevo_curso = data.get('course_code') or None

                if nuevo_curso != curso_actual:
                    cursor.execute("""
                        UPDATE enrollments SET status='inactivo', egreso_date=CURDATE()
                        WHERE school_id = %s AND status = 'activo'
                    """, (school_id,))
                    if nuevo_curso:
                        cursor.execute("""
                            INSERT INTO enrollments (school_id, course_code, enrollment_date, status)
                            VALUES (%s, %s, CURDATE(), 'activo')
                        """, (school_id, nuevo_curso))

            conn.commit()
            return True
        except Exception as e:
            print(f"Error al actualizar estudiante: {e}")
            conn.rollback()
            return False
        finally:
            cursor.close()
            conn.close()
            
    @staticmethod
    def delete(student_id):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(e)
            return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def get_by_teacher_course(teacher_id):
        """Estudiantes de los cursos donde el docente es titular O está asignado en M2M."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT DISTINCT s.*,
                r.first_name AS rep_first_name, r.last_name AS rep_last_name,
                r.phone AS rep_phone, r.cedula_id AS rep_cedula,
                c.name AS course_name, c.code AS course_code,
                e.status AS enrollment_status
            FROM students s
            LEFT JOIN representatives r ON s.representative_cedula = r.cedula_id
            JOIN enrollments e ON s.school_id = e.school_id AND e.status = 'activo'
            JOIN courses c ON e.course_code = c.code
            LEFT JOIN course_teachers ct ON ct.course_code = c.code
            WHERE c.teacher_id = %s OR ct.teacher_id = %s
            ORDER BY s.last_name, s.first_name
        """, (teacher_id, teacher_id))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    
        #    @staticmethod
    #    def get_all_with_details():
    #        conn = get_db_connection()
    #        if not conn: return []
    #        cursor = conn.cursor(dictionary=True)
    #        cursor.execute("""
    #            SELECT s.*, 
    #                   r.first_name as rep_first_name, r.last_name as rep_last_name,
    #                   r.phone as rep_phone, r.cedula_id as rep_cedula,
    #                   c.name as course_name, c.code as course_code
    #            FROM students s
    #            LEFT JOIN representatives r ON s.representative_cedula = r.cedula_id
    #            LEFT JOIN enrollments e ON s.school_id = e.school_id AND e.status = 'activo'
    #            LEFT JOIN courses c ON e.course_code = c.code
    #            ORDER BY s.last_name
    #        """)
    #        students = cursor.fetchall()
    #        cursor.close(); conn.close()
    #        return students
    #### ---
            #cursor.execute("""
            #    SELECT s.*, 
            #           r.cedula_id as rep_cedula_id, r.first_name as rep_first_name,
            #           r.last_name as rep_last_name, r.email as rep_email,
            #           r.phone as rep_phone, r.address as rep_address,
            #           r.relationship as rep_relationship,
            #           c.code as course_code, c.name as course_name
            #    FROM students s
            #    LEFT JOIN representatives r ON s.representative_cedula = r.cedula_id
            #    LEFT JOIN enrollments e ON s.school_id = e.school_id AND e.status = 'activo'
            #    LEFT JOIN courses c ON e.course_code = c.code
            #    WHERE s.id = %s
            #""", (student_id,))