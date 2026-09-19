from app.utils.db import get_db_connection
from datetime import date, datetime, timedelta
import mysql.connector


class TeacherAttendance:
    GRACE_MINUTES = 10

    @staticmethod
    def _get_today_schedule():
        from app.models.school_schedule import SchoolSchedule
        day = datetime.now().isoweekday()
        return SchoolSchedule.get_by_day(day)

    @staticmethod
    def _compute_status(check_in_time):
        schedule = TeacherAttendance._get_today_schedule()
        if not schedule:
            return 'present'
        start = schedule['start_time']
        if isinstance(start, timedelta):
            start = (datetime.min + start).time()
        start_dt = datetime.combine(date.today(), start)
        limite = start_dt + timedelta(minutes=TeacherAttendance.GRACE_MINUTES)
        return 'late' if check_in_time > limite.time() else 'present'

    @staticmethod
    def get_today(teacher_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM teacher_attendance
            WHERE teacher_id = %s AND attendance_date = CURDATE()
        """, (teacher_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def get_by_id(attendance_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ta.*, t.first_name, t.last_name
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.id = %s
        """, (attendance_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def get_all_by_date(date_str=None):
        if not date_str:
            date_str = date.today().strftime('%Y-%m-%d')
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ta.*, t.first_name, t.last_name
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.attendance_date = %s
            ORDER BY t.last_name
        """, (date_str,))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def check_in(teacher_id):
        conn = get_db_connection()
        if not conn: return {'success': False, 'error': 'Error de conexión'}
        cursor = conn.cursor(dictionary=True)
        try:
            now = datetime.now().time()
            status = TeacherAttendance._compute_status(now)
            cursor.execute("""
                INSERT INTO teacher_attendance
                    (teacher_id, attendance_date, check_in, status)
                VALUES (%s, CURDATE(), %s, %s)
                ON DUPLICATE KEY UPDATE
                    check_in = IF(check_in IS NULL, VALUES(check_in), check_in),
                    status   = IF(status IS NULL OR status = 'absent', VALUES(status), status)
            """, (teacher_id, now, status))
            conn.commit()
            row = TeacherAttendance.get_today(teacher_id)
            return {'success': True, 'record': row}
        except Exception as e:
            print(e); return {'success': False, 'error': str(e)}
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def check_out(teacher_id):
        conn = get_db_connection()
        if not conn: return {'success': False, 'error': 'Error de conexión'}
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE teacher_attendance
                SET check_out = CURTIME()
                WHERE teacher_id = %s AND attendance_date = CURDATE()
            """, (teacher_id,))
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'No hay registro de entrada para hoy.'}
            return {'success': True}
        except Exception as e:
            print(e); return {'success': False, 'error': str(e)}
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def update(attendance_id, data):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        sql = """UPDATE teacher_attendance SET
                 check_in=%s, check_out=%s, status=%s, remarks=%s
                 WHERE id=%s"""
        values = (data.get('check_in'), data.get('check_out'),
                  data.get('status'), data.get('remarks'), attendance_id)
        try:
            cursor.execute(sql, values)
            conn.commit()
            return True
        except Exception as e:
            print(e); return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def get_report(filters):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT ta.*, t.first_name, t.last_name
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.attendance_date BETWEEN %s AND %s
        """
        params = [filters['from_date'], filters['to_date']]
        if filters.get('teacher_ids'):
            placeholders = ','.join(['%s'] * len(filters['teacher_ids']))
            sql += f" AND ta.teacher_id IN ({placeholders})"
            params.extend(filters['teacher_ids'])
        if filters.get('status'):
            sql += " AND ta.status = %s"
            params.append(filters['status'])
        if filters.get('days_of_week'):
            mysql_days = [(d % 7) + 1 for d in filters['days_of_week']]
            placeholders = ','.join(['%s'] * len(mysql_days))
            sql += f" AND DAYOFWEEK(ta.attendance_date) IN ({placeholders})"
            params.extend(mysql_days)
        sql += " ORDER BY ta.attendance_date DESC, t.last_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_summary_by_teacher(filters):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        sql = """
            SELECT
                t.id, t.first_name, t.last_name,
                COUNT(*) AS total_dias,
                SUM(CASE WHEN ta.status='present'   THEN 1 ELSE 0 END) AS presentes,
                SUM(CASE WHEN ta.status='late'      THEN 1 ELSE 0 END) AS tardanzas,
                SUM(CASE WHEN ta.status='absent'    THEN 1 ELSE 0 END) AS ausencias,
                SUM(CASE WHEN ta.status='justified' THEN 1 ELSE 0 END) AS justificados,
                SEC_TO_TIME(AVG(TIME_TO_SEC(ta.check_in))) AS promedio_entrada
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.attendance_date BETWEEN %s AND %s
        """
        params = [filters['from_date'], filters['to_date']]
        if filters.get('teacher_ids'):
            placeholders = ','.join(['%s'] * len(filters['teacher_ids']))
            sql += f" AND ta.teacher_id IN ({placeholders})"
            params.extend(filters['teacher_ids'])
        sql += " GROUP BY t.id, t.first_name, t.last_name ORDER BY t.last_name"
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_by_date_range(teacher_id, from_date, to_date):
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM teacher_attendance
            WHERE teacher_id = %s AND attendance_date BETWEEN %s AND %s
            ORDER BY attendance_date DESC
        """, (teacher_id, from_date, to_date))
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def justify(attendance_id, user_id, reason):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE teacher_attendance
                SET status = 'justified',
                    justified_by = %s,
                    justification_reason = %s,
                    justification_date = NOW()
                WHERE id = %s
            """, (user_id, reason, attendance_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(e); return False
        finally:
            cursor.close(); conn.close()
    # ============================================================
    # CARGA MANUAL POR EL DIRECTIVO
    # ============================================================
    @staticmethod
    def get_all_teachers_for_date(attendance_date):
        """
        Devuelve la lista de todos los docentes activos con su registro
        actual (si existe) para una fecha específica.
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                t.id AS teacher_id,
                t.first_name,
                t.last_name,
                t.email,
                ta.id AS attendance_id,
                ta.check_in,
                ta.check_out,
                ta.status,
                ta.remarks,
                ta.original_source,
                ta.batch_id,
                abl.batch_number,
                u.username AS loaded_by_username,
                abl.created_at AS batch_created_at
            FROM teachers t
            LEFT JOIN teacher_attendance ta 
                ON ta.teacher_id = t.id AND ta.attendance_date = %s
            LEFT JOIN attendance_batch_loads abl ON ta.batch_id = abl.id
            LEFT JOIN users u ON abl.loaded_by = u.id
            WHERE t.active = 1
            ORDER BY t.last_name, t.first_name
        """, (attendance_date,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def save_manual(teacher_id, attendance_date, data, batch_id, source='manual_director'):
        """
        Crea o actualiza un registro de asistencia cargado manualmente.
        Devuelve el ID del registro o None si falla.
        """
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            # ON DUPLICATE actualiza si ya existía uno (por la unique teacher_id + date)
            cursor.execute("""
                INSERT INTO teacher_attendance
                    (teacher_id, attendance_date, check_in, check_out,
                     status, remarks, batch_id, original_source)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    check_in = VALUES(check_in),
                    check_out = VALUES(check_out),
                    status = VALUES(status),
                    remarks = VALUES(remarks),
                    batch_id = VALUES(batch_id),
                    original_source = VALUES(original_source)
            """, (teacher_id, attendance_date,
                  data.get('check_in') or None,
                  data.get('check_out') or None,
                  data.get('status') or 'present',
                  data.get('remarks') or None,
                  batch_id, source))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"[TeacherAttendance.save_manual] {e}")
            return None
        finally:
            cursor.close()
            conn.close()