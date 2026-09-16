from app.utils.db import get_db_connection
from datetime import datetime, timedelta


class UserSession:
    @staticmethod
    def create(user_id, session_id, ip_address=None, user_agent=None):
        """Registra una nueva sesión activa al hacer login."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO user_sessions 
                    (user_id, session_id, ip_address, user_agent)
                VALUES (%s, %s, %s, %s)
            """, (user_id, session_id, ip_address, user_agent))
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            print(f"Error al crear sesión: {e}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def close(session_id):
        """Marca la sesión como inactiva al hacer logout."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE user_sessions
                SET is_active = 0, logout_time = NOW()
                WHERE session_id = %s AND is_active = 1
            """, (session_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception:
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_active_sessions():
        """Devuelve todas las sesiones activas con datos del usuario."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT s.*, u.username, u.role, u.email
            FROM user_sessions s
            JOIN users u ON s.user_id = u.id
            WHERE s.is_active = 1
            ORDER BY s.last_activity DESC
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def cleanup_stale(minutes=30):
        """Marca como inactivas las sesiones sin actividad en X minutos."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE user_sessions
                SET is_active = 0, logout_time = NOW()
                WHERE is_active = 1
                  AND last_activity < NOW() - INTERVAL %s MINUTE
            """, (minutes,))
            conn.commit()
            return cursor.rowcount
        except Exception:
            return 0
        finally:
            cursor.close()
            conn.close()