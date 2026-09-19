from app.utils.db import get_db_connection
from datetime import date


class AttendanceBatchLoad:
    PREFIX = 'AL'

    @staticmethod
    def _next_sequence(year):
        conn = get_db_connection()
        if not conn:
            return 1
        cursor = conn.cursor()
        cursor.execute("""
            SELECT COALESCE(MAX(sequence), 0) + 1
            FROM attendance_batch_loads
            WHERE year = %s
        """, (year,))
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return result[0] if result else 1

    @staticmethod
    def create(attendance_date, reason, loaded_by, teachers_count):
        year = date.today().year
        seq = AttendanceBatchLoad._next_sequence(year)
        number = f"{AttendanceBatchLoad.PREFIX}-{year}-{seq:04d}"

        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO attendance_batch_loads
                    (batch_number, year, sequence, attendance_date,
                     reason, loaded_by, teachers_count)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (number, year, seq, attendance_date,
                  reason, loaded_by, teachers_count))
            conn.commit()
            return {
                'id': cursor.lastrowid,
                'batch_number': number,
                'year': year,
                'sequence': seq
            }
        except Exception as e:
            print(f"[AttendanceBatchLoad.create] {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(batch_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT abl.*,
                   u_loader.username AS loaded_by_username,
                   u_editor.username AS reason_updated_by_username
            FROM attendance_batch_loads abl
            LEFT JOIN users u_loader ON abl.loaded_by = u_loader.id
            LEFT JOIN users u_editor ON abl.reason_updated_by = u_editor.id
            WHERE abl.id = %s
        """, (batch_id,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row
    
    @staticmethod
    def get_all(limit=100):
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT abl.*,
                   u_loader.username AS loaded_by_username,
                   u_editor.username AS reason_updated_by_username
            FROM attendance_batch_loads abl
            LEFT JOIN users u_loader ON abl.loaded_by = u_loader.id
            LEFT JOIN users u_editor ON abl.reason_updated_by = u_editor.id
            ORDER BY abl.created_at DESC
            LIMIT %s
        """, (limit,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_by_attendance_date(attendance_date):
        """Busca un lote previo para esa fecha (para advertir duplicados)."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT abl.*, u.username AS loaded_by_username
            FROM attendance_batch_loads abl
            LEFT JOIN users u ON abl.loaded_by = u.id
            WHERE abl.attendance_date = %s
            ORDER BY abl.created_at DESC
            LIMIT 1
        """, (attendance_date,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row
    @staticmethod
    def update_reason(batch_id, new_reason, updated_by):
        """Permite editar la razón de un lote existente (agregar aval, aclaratorias, etc.)."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE attendance_batch_loads
                SET reason = %s,
                    reason_updated_at = NOW(),
                    reason_updated_by = %s
                WHERE id = %s
            """, (new_reason, updated_by, batch_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[AttendanceBatchLoad.update_reason] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def create_v2(attendance_date, reason, loaded_by, teachers_count, days_after_event):
        """
        Versión mejorada que registra si fue una carga tardía.
        days_after_event: días transcurridos entre la fecha de asistencia y hoy.
        """
        year = date.today().year
        seq = AttendanceBatchLoad._next_sequence(year)
        number = f"{AttendanceBatchLoad.PREFIX}-{year}-{seq:04d}"

        is_late = 1 if days_after_event > 7 else 0

        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO attendance_batch_loads
                    (batch_number, year, sequence, attendance_date,
                     reason, loaded_by, teachers_count,
                     is_late_load, days_after_event)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (number, year, seq, attendance_date,
                  reason, loaded_by, teachers_count,
                  is_late, days_after_event))
            conn.commit()
            return {
                'id': cursor.lastrowid,
                'batch_number': number,
                'year': year,
                'sequence': seq,
                'is_late_load': bool(is_late)
            }
        except Exception as e:
            print(f"[AttendanceBatchLoad.create_v2] {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_teacher_remarks(attendance_id, remarks):
        """Permite editar las observaciones de un registro individual."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE teacher_attendance
                SET remarks = %s
                WHERE id = %s
            """, (remarks, attendance_id))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[AttendanceBatchLoad.update_teacher_remarks] {e}")
            return False
        finally:
            cursor.close()
            conn.close()