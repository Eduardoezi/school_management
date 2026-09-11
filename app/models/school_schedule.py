from app.utils.db import get_db_connection

class SchoolSchedule:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM school_schedules ORDER BY day_of_week, start_time")
        rows = cursor.fetchall()
        cursor.close(); conn.close()
        return rows

    @staticmethod
    def get_by_id(schedule_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM school_schedules WHERE id = %s", (schedule_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def get_by_day(day_of_week):
        """Devuelve el horario del día (1=Lunes...7=Domingo)."""
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM school_schedules 
            WHERE day_of_week = %s ORDER BY start_time LIMIT 1
        """, (day_of_week,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def create(data):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        sql = """INSERT INTO school_schedules 
                 (code_schedules, day_of_week, start_time, end_time)
                 VALUES (%s, %s, %s, %s)"""
        values = (data.get('code_schedules'), data['day_of_week'],
                  data['start_time'], data['end_time'])
        try:
            cursor.execute(sql, values)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(e); return None
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def update(schedule_id, data):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        sql = """UPDATE school_schedules SET 
                 code_schedules=%s, day_of_week=%s, start_time=%s, end_time=%s
                 WHERE id=%s"""
        values = (data.get('code_schedules'), data['day_of_week'],
                  data['start_time'], data['end_time'], schedule_id)
        try:
            cursor.execute(sql, values)
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(e); return False
        finally:
            cursor.close(); conn.close()

    @staticmethod
    def delete(schedule_id):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM school_schedules WHERE id = %s", (schedule_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(e); return False
        finally:
            cursor.close(); conn.close()