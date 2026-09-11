from flask_login import UserMixin
from app.utils.db import get_db_connection
import bcrypt
import mysql.connector


class User(UserMixin):
    def __init__(self, id, username, email, role, password_hash=None, teacher_id=None):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.password_hash = password_hash
        self.teacher_id = teacher_id

    @staticmethod
    def _row_to_user(user_data):
        """Convierte un dict de la BD en un objeto User."""
        return User(
            user_data['id'],
            user_data['username'],
            user_data['email'],
            user_data['role'],
            user_data['password_hash'],
            user_data.get('teacher_id')
        )

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
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))