# app/models/webauthn_credential.py
import json
from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


class WebAuthnCredential:
    """Gestiona las credenciales biométricas de los docentes.

    IMPORTANTE: Esta tabla solo guarda claves PÚBLICAS.
    Nunca se almacenan huellas, rostros ni plantillas biométricas.
    """

    @staticmethod
    def create(teacher_id: int, credential_data: dict) -> bool:
        """Guarda una nueva credencial tras el registro exitoso."""
        conn = get_db_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO webauthn_credentials
                    (teacher_id, credential_id, credential_public_key,
                     sign_count, device_name, aaguid,
                     backup_eligible, backup_state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                teacher_id,
                credential_data['credential_id'],
                credential_data['credential_public_key'],
                credential_data.get('sign_count', 0),
                credential_data.get('device_name'),
                credential_data.get('aaguid'),
                1 if credential_data.get('backup_eligible') else 0,
                1 if credential_data.get('backup_state') else 0,
            ))
            conn.commit()
            return cur.rowcount > 0
        except Exception as e:
            logger.exception("Error en el metodo create de la clase WebAuthnCredential: %s", e)
            return False
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_by_teacher(teacher_id: int) -> list:
        """Devuelve todas las credenciales de un docente."""
        conn = get_db_connection()
        if not conn:
            return []
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT id, credential_id, credential_public_key,
                       sign_count, device_name, created_at, last_used_at
                FROM webauthn_credentials
                WHERE teacher_id = %s
                ORDER BY created_at DESC
            """, (teacher_id,))
            return cur.fetchall()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def get_by_credential_id(credential_id: str) -> dict | None:
        """Busca una credencial por su ID (para autenticación)."""
        conn = get_db_connection()
        if not conn:
            return None
        try:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT * FROM webauthn_credentials
                WHERE credential_id = %s
            """, (credential_id,))
            return cur.fetchone()
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def update_sign_count(credential_id: str, new_count: int, used: bool = True) -> bool:
        """Actualiza el contador de firmas tras una autenticación."""
        conn = get_db_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            if used:
                cur.execute("""
                    UPDATE webauthn_credentials
                    SET sign_count = %s, last_used_at = NOW()
                    WHERE credential_id = %s
                """, (new_count, credential_id))
            else:
                cur.execute("""
                    UPDATE webauthn_credentials
                    SET sign_count = %s
                    WHERE credential_id = %s
                """, (new_count, credential_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()

    @staticmethod
    def delete(credential_id: str, teacher_id: int) -> bool:
        """Elimina una credencial (ej: el docente cambió de teléfono)."""
        conn = get_db_connection()
        if not conn:
            return False
        try:
            cur = conn.cursor()
            cur.execute("""
                DELETE FROM webauthn_credentials
                WHERE credential_id = %s AND teacher_id = %s
            """, (credential_id, teacher_id))
            conn.commit()
            return cur.rowcount > 0
        finally:
            cur.close()
            conn.close()