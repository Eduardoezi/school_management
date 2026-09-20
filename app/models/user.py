from flask_login import UserMixin
from app.utils.db import get_db_connection
import bcrypt
import mysql.connector


class User(UserMixin):
    def __init__(self, id, username, email, role, password_hash=None,
                 teacher_id=None, last_seen=None, avatar=None, active=True):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.password_hash = password_hash
        self.teacher_id = teacher_id
        self.last_seen = last_seen
        self.avatar = avatar
        self.active = active
    # ---------- Propiedades para la UI ----------
    @property
    def initials(self):
        if not self.username:
            return "?"
        partes = self.username.strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return self.username[:2].upper()

    @property
    def is_online(self):
        if not self.last_seen:
            return False
        from datetime import datetime, timedelta
        return (datetime.now() - self.last_seen) < timedelta(minutes=5)

    @property
    def is_active(self):
        """Flask-Login bloquea el login si esto es False."""
        return bool(self.active)

    @property
    def avatar_url(self):
        if not self.avatar:
            return None
        return f"/static/{self.avatar}"

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
            user_data.get('avatar'),
            user_data.get('active', True)
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
    def get_all_with_teacher():
        """Devuelve todos los usuarios + datos del docente vinculado."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT u.*,
                   t.first_name AS teacher_first_name,
                   t.last_name  AS teacher_last_name,
                   t.active     AS teacher_active,
                   sd.staff_type,
                   sd.specialist_type
            FROM users u
            LEFT JOIN teachers t ON u.teacher_id = t.id
            LEFT JOIN staff_details sd ON sd.teacher_id = t.id
            ORDER BY u.username
        """)
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    @staticmethod
    def get_online_users(minutes=5):
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
    def create(username, email, password, role='pendiente', teacher_id=None):
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

    @staticmethod
    def update_role(user_id, new_role):
        """Cambia el rol de un usuario."""
        if new_role not in ('pendiente', 'directivo', 'secretario', 'maestro'):
            return False
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET role = %s WHERE id = %s",
                (new_role, user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[User.update_role] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_avatar(user_id, avatar_path):
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

    @staticmethod
    def update_password(user_id, new_password):
        """Cambia la contraseña de un usuario. Retorna True si se actualizó."""
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed.decode('utf-8'), user_id)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[User.update_password] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def deactivate(user_id):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET active = 0 WHERE id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[User.deactivate] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def reactivate(user_id):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE users SET active = 1 WHERE id = %s", (user_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"[User.reactivate] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id_with_active(user_id):
        """Igual que get_by_id pero incluye el flag active."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        data = cursor.fetchone()
        cursor.close()
        conn.close()
        return data

    def check_password(self, password):
        return bcrypt.checkpw(password.encode('utf-8'),
                              self.password_hash.encode('utf-8'))