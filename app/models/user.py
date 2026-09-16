from flask_login import UserMixin
from app.utils.db import get_db_connection
import bcrypt
import mysql.connector


class User(UserMixin):
    def __init__(self, id, username, email, role, password_hash=None,
                 teacher_id=None, last_seen=None, avatar=None):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.password_hash = password_hash
        self.teacher_id = teacher_id
        self.last_seen = last_seen
        self.avatar = avatar

    # ---------- Propiedades para la UI ----------
    @property
    def initials(self):
        """Iniciales para generar avatar si no tiene imagen."""
        if not self.username:
            return "?"
        partes = self.username.strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return self.username[:2].upper()

    @property
    def is_online(self):
        """Determina si el usuario está online (últimos 5 min)."""
        if not self.last_seen:
            return False
        from datetime import datetime, timedelta
        return (datetime.now() - self.last_seen) < timedelta(minutes=5)

    # ---------- Constructor desde fila ----------
    @staticmethod
    def _row_to_user(user_data):
        return User(
            user_data['id'],
            user_data['username'],
            user_data['email'],
            user_data['role'],
            user_data['password_hash'],
            user_data.get('teacher_id'),
            user_data.get('last_seen'),
            user_data.get('avatar')
        )

    # ---------- Consultas ----------
    @staticmethod
    def get_by_id(user_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        return User._row_to_user(data) if data else None

    @staticmethod
    def get_by_username(username):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        return User._row_to_user(data) if data else None

    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users ORDER BY username")
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_online_users(minutes=5):
        """Devuelve usuarios activos en los últimos X minutos."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.*, s.ip_address, s.user_agent, s.login_time, s.last_activity
            FROM users u
            LEFT JOIN user_sessions s 
                ON s.user_id = u.id AND s.is_active = 1
            WHERE u.last_seen >= NOW() - INTERVAL %s MINUTE
            ORDER BY u.last_seen DESC
        """, (minutes,))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def create(username, email, password, role='maestro', teacher_id=None):
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, role, teacher_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (username, email, hashed.decode('utf-8'), role, teacher_id)
            )
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError:
            return None
        finally:
            cursor.close()
            conn.close()

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'),
                              self.password_hash.encode('utf-8'))

    @property
    def avatar_url(self):
        """Devuelve la URL pública del avatar, o None si no tiene."""
        if not self.avatar:
            return None
        return f"/static/{self.avatar}"


    @staticmethod
    def update_avatar(user_id, avatar_path):
        """Actualiza la ruta del avatar del usuario."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET avatar = %s WHERE id = %s",
                (avatar_path, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[User.update_avatar] {e}")
            return False
        finally:
            cursor.close()
            conn.close()