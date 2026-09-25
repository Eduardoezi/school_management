from app.utils.db import get_db_connection
from datetime import date, datetime, timedelta
import mysql.connector
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


class TeacherAttendance:
    GRACE_MINUTES = 10
    AUTO_CLOSE_BUFFER_MINUTES = 30   # cierre automático: end_time + 30 min
    AUTO_CLOSE_FALLBACK_TIME = '17:00:00'

    # ============================================================
    # HELPERS DE FORMATO
    # ============================================================
    @staticmethod
    def format_time(value):
        """
        Convierte TIME de MySQL (datetime.timedelta) o datetime.time
        a string 'HH:MM:SS' listo para JSON. Devuelve None si value is None.
        """
        if value is None:
            return None
        if isinstance(value, timedelta):
            total = int(value.total_seconds())
            hh = total // 3600
            mm = (total % 3600) // 60
            ss = total % 60
            return f"{hh:02d}:{mm:02d}:{ss:02d}"
        if hasattr(value, 'strftime'):
            return value.strftime('%H:%M:%S')
        return str(value)

    # ============================================================
    # HORARIO Y ESTADO
    # ============================================================
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

    # ============================================================
    # CONSULTAS
    # ============================================================
    @staticmethod
    def get_today(teacher_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM teacher_attendance
            WHERE teacher_id = %s AND attendance_date = CURDATE()
        """, (teacher_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def get_by_id(attendance_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ta.*, t.first_name, t.last_name
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.id = %s
        """, (attendance_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def get_all_by_date(date_str=None):
        if not date_str:
            date_str = date.today().strftime('%Y-%m-%d')
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT ta.*, t.first_name, t.last_name
            FROM teacher_attendance ta
            JOIN teachers t ON ta.teacher_id = t.id
            WHERE ta.attendance_date = %s
            ORDER BY t.last_name
        """, (date_str,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_by_date_range(teacher_id, from_date, to_date):
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM teacher_attendance
            WHERE teacher_id = %s AND attendance_date BETWEEN %s AND %s
            ORDER BY attendance_date DESC
        """, (teacher_id, from_date, to_date))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    # ============================================================
    # MARCAR ENTRADA / SALIDA
    # ============================================================
    @staticmethod
    def check_in(teacher_id):
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión'}
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
            logger.exception("Error en el metodo check_in de la clase TeacherAttendance: %s", e)
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def check_out(teacher_id):
        conn = get_db_connection()
        if not conn:
            return {'success': False, 'error': 'Error de conexión'}
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE teacher_attendance
                   SET check_out = CURTIME()
                 WHERE teacher_id = %s
                   AND attendance_date = CURDATE()
                   AND check_in IS NOT NULL
                   AND check_out IS NULL
            """, (teacher_id,))
            conn.commit()
            if cursor.rowcount == 0:
                return {'success': False, 'error': 'No hay entrada pendiente de salida para hoy.'}
            return {'success': True}
        except Exception as e:
            logger.exception("Error en el metodo check_out de la clase TeacherAttendance: %s", e)
            return {'success': False, 'error': str(e)}
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(attendance_id, data):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        sql = """UPDATE teacher_attendance
                    SET check_in=%s, check_out=%s, status=%s, remarks=%s
                  WHERE id=%s"""
        values = (data.get('check_in'), data.get('check_out'),
                  data.get('status'), data.get('remarks'), attendance_id)
        try:
            cursor.execute(sql, values)
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en el metodo update de la clase TeacherAttendance: %s", e)
            return False
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # AUTO-CIERRE DE SALIDAS
    # ============================================================
    @staticmethod
    def auto_close_pending(target_date=None):
        """
        Cierra automáticamente las salidas pendientes (check_in sin check_out)
        para la fecha indicada. La hora de salida se toma del horario del día;
        si no hay horario, usa 17:00.
        """
        if target_date is None:
            target_date = date.today()
        if isinstance(target_date, str):
            try:
                target_date = datetime.strptime(target_date, '%Y-%m-%d').date()
            except ValueError:
                return 0

        close_time_str = TeacherAttendance.AUTO_CLOSE_FALLBACK_TIME
        try:
            from app.models.school_schedule import SchoolSchedule
            schedule = SchoolSchedule.get_by_day(target_date.isoweekday())
            if schedule and schedule.get('end_time'):
                close_time_str = TeacherAttendance.format_time(schedule['end_time'])
        except Exception as exc:
            logger.exception("Error en el metodo auto_close_pending schedule lookup de la clase TeacherAttendance: %s", exc)

        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE teacher_attendance
                   SET check_out = %s,
                       remarks = CONCAT(
                           COALESCE(remarks, ''),
                           CASE WHEN COALESCE(remarks, '') = '' THEN '' ELSE ' | ' END,
                           'Salida registrada automáticamente'
                       )
                 WHERE attendance_date = %s
                   AND check_in IS NOT NULL
                   AND check_out IS NULL
            """, (close_time_str, target_date))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.exception("Error en el metodo auto_clase_pending de la clase TeacherAttendance: %s", e)
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def auto_close_all_past():
        """Cierra salidas pendientes de fechas anteriores a hoy (una sola vez)."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE teacher_attendance
                   SET check_out = %s,
                       remarks = CONCAT(
                           COALESCE(remarks, ''),
                           CASE WHEN COALESCE(remarks, '') = '' THEN '' ELSE ' | ' END,
                           'Salida auto-registrada (olvido)'
                       )
                 WHERE attendance_date < CURDATE()
                   AND check_in IS NOT NULL
                   AND check_out IS NULL
            """, (TeacherAttendance.AUTO_CLOSE_FALLBACK_TIME,))
            conn.commit()
            return cursor.rowcount
        except Exception as e:
            logger.exception("Error en el metodo auto_close_all_past de la clase TeacherAttendance: %s", e)
            conn.rollback()
            return 0
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def maybe_auto_close_today():
        """
        Cierra las salidas pendientes de HOY solo si ya pasó la hora de salida
        del horario + buffer. Se llama de forma perezosa al abrir la vista admin.
        """
        now = datetime.now()
        try:
            schedule = TeacherAttendance._get_today_schedule()
        except Exception as exc:
            logger.exception("Error en el metodo maybe_auto_close_today de la clase TeacherAttendance: %s", exc)
            
            return 0

        if not schedule or not schedule.get('end_time'):
            return 0

        end_t = schedule['end_time']
        if isinstance(end_t, timedelta):
            end_time = (datetime.min + end_t).time()
        else:
            end_time = end_t

        end_dt = datetime.combine(date.today(), end_time) + \
                 timedelta(minutes=TeacherAttendance.AUTO_CLOSE_BUFFER_MINUTES)

        if now < end_dt:
            return 0

        return TeacherAttendance.auto_close_pending(date.today())

    # ============================================================
    # REPORTES
    # ============================================================
    @staticmethod
    def get_report(filters):
        conn = get_db_connection()
        if not conn:
            return []
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
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_summary_by_teacher(filters):
        conn = get_db_connection()
        if not conn:
            return []
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
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def justify(attendance_id, user_id, reason):
        conn = get_db_connection()
        if not conn:
            return False
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
            logger.exception("Error en el metodo justify de la clase TeacherAttendance: %s", e)
            return False
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # CARGA MANUAL
    # ============================================================
    @staticmethod
    def get_all_teachers_for_date(attendance_date):
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
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
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
            logger.exception("Error en el metodo save_manual de la clase TeacherAttendance: %s", e)
            return None
        finally:
            cursor.close()
            conn.close()