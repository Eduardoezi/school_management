"""
Modelo de usuario del sistema escolar.

Encapsula credenciales, rol y estado. NO contiene lógica de presentación
contextual (eso vive en `app/__init__.py` como context processor).
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

import bcrypt
import mysql.connector
from flask_login import UserMixin

from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


# ============================================================
# Etiquetas legibles de rol (única fuente de verdad)
# ============================================================
ROLE_LABELS: dict[str, str] = {
    'directivo':  'Directivo',
    'secretario': 'Secretario',
    'maestro':    'Maestro',
    'pendiente':  'Pendiente de aprobación',
}


class User(UserMixin):
    """Usuario autenticable del sistema."""

    def __init__(
        self,
        id: int,
        username: str,
        email: str,
        role: str,
        password_hash: Optional[str] = None,
        teacher_id: Optional[int] = None,
        last_seen: Optional[datetime] = None,
        avatar: Optional[str] = None,
        active: bool = True,
    ):
        self.id = id
        self.username = username
        self.email = email
        self.role = role
        self.password_hash = password_hash
        self.teacher_id = teacher_id
        self.last_seen = last_seen
        self.avatar = avatar
        self.active = active

    # ------------------------------------------------------------
    # Propiedades de Flask-Login
    # ------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        """Flask-Login bloquea el login si es False."""
        return bool(self.active)

    # ------------------------------------------------------------
    # Propiedades de UI (solo dependen del propio usuario)
    # ------------------------------------------------------------
    @property
    def initials(self) -> str:
        """Iniciales para el avatar por defecto."""
        if not self.username:
            return '?'
        partes = self.username.strip().split()
        if len(partes) >= 2:
            return (partes[0][0] + partes[1][0]).upper()
        return self.username[:2].upper()

    @property
    def is_online(self) -> bool:
        """True si tuvo actividad en los últimos 5 minutos."""
        if not self.last_seen:
            return False
        return (datetime.now() - self.last_seen) < timedelta(minutes=5)

    @property
    def avatar_url(self) -> Optional[str]:
        """URL pública del avatar o None."""
        if not self.avatar:
            return None
        return f'/static/{self.avatar}'

    @property
    def role_label(self) -> str:
        """
        Etiqueta legible del rol (capitalizada y traducida).

        Returns:
            Cadena lista para mostrar en UI.
        """
        return ROLE_LABELS.get(
            (self.role or '').lower(),
            self.role or 'Desconocido',
        )

    # ------------------------------------------------------------
    # Constructor desde fila de BD
    # ------------------------------------------------------------
    @staticmethod
    def _row_to_user(user_data: dict) -> 'User':
        """Convierte un dict de BD en instancia de User."""
        return User(
            user_data['id'],
            user_data['username'],
            user_data['email'],
            user_data['role'],
            user_data['password_hash'],
            user_data.get('teacher_id'),
            user_data.get('last_seen'),
            user_data.get('avatar'),
            user_data.get('active', True),
        )

    # ------------------------------------------------------------
    # Consultas
    # ------------------------------------------------------------
    @staticmethod
    def get_by_id(user_id: int) -> Optional['User']:
        """Busca un usuario por su ID."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            data = cursor.fetchone()
            return User._row_to_user(data) if data else None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_username(username: str) -> Optional['User']:
        """Busca un usuario por su username."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s", (username,)
            )
            data = cursor.fetchone()
            return User._row_to_user(data) if data else None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_all() -> list[dict]:
        """Devuelve todos los usuarios como diccionarios."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("SELECT * FROM users ORDER BY username")
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_all_with_teacher() -> list[dict]:
        """Devuelve usuarios + datos del docente vinculado (si aplica)."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
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
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_online_users(minutes: int = 5) -> list[dict]:
        """
        Usuarios con actividad en los últimos N minutos.

        Devuelve UNA fila por usuario, con el número de sesiones
        activas y los datos de la sesión más reciente.

        Sin GROUP BY, el LEFT JOIN a user_sessions produce una fila
        por cada sesión activa: un usuario con 3 pestañas abiertas
        aparecería 3 veces.
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT
                    u.id,
                    u.username,
                    u.email,
                    u.role,
                    u.last_seen,
                    u.avatar,
                    u.teacher_id,
                    u.active,
                    u.created_at,
                    COUNT(s.id) AS active_sessions,
                    MAX(s.ip_address) AS ip_address,
                    MAX(s.user_agent) AS user_agent,
                    MAX(s.login_time) AS login_time,
                    MAX(s.last_activity) AS last_activity
                FROM users u
                LEFT JOIN user_sessions s
                    ON s.user_id = u.id AND s.is_active = 1
                WHERE u.last_seen >= NOW() - INTERVAL %s MINUTE
                GROUP BY
                    u.id, u.username, u.email, u.role,
                    u.last_seen, u.avatar, u.teacher_id,
                    u.active, u.created_at
                ORDER BY u.last_seen DESC
            """, (minutes,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # ------------------------------------------------------------
    # Mutaciones
    # ------------------------------------------------------------
    @staticmethod
    def create(
        username: str,
        email: str,
        password: str,
        role: str = 'pendiente',
        teacher_id: Optional[int] = None,
    ) -> Optional[int]:
        """
        Crea un usuario con contraseña hasheada.

        Returns:
            ID del usuario creado, o None si hay conflicto único.
        """
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                """INSERT INTO users (username, email, password_hash, role, teacher_id)
                   VALUES (%s, %s, %s, %s, %s)""",
                (username, email, hashed.decode('utf-8'), role, teacher_id),
            )
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError:
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_role(user_id: int, new_role: str) -> bool:
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
                (new_role, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            logger.exception("Error en el metodo update_role de la clase User: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_avatar(user_id: int, avatar_path: Optional[str]) -> bool:
        """Actualiza la ruta del avatar."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET avatar = %s WHERE id = %s",
                (avatar_path, user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            logger.exception("Error en el metodo update_avatar de la clase User: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update_password(user_id: int, new_password: str) -> bool:
        """Cambia la contraseña (hasheada)."""
        hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt())
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (hashed.decode('utf-8'), user_id),
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            logger.exception("Error en el metodo update_password de la clase User: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def deactivate(user_id: int) -> bool:
        """Marca la cuenta como inactiva."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET active = 0 WHERE id = %s", (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            logger.exception("Error en el metodo deactivate de la clase User: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def reactivate(user_id: int) -> bool:
        """Marca la cuenta como activa."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "UPDATE users SET active = 1 WHERE id = %s", (user_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            logger.exception("Error en el metodo reactivate de la clase User: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    def check_password(self, password: str) -> bool:
        """Compara la contraseña contra el hash almacenado."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8'),
        )