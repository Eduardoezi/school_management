# app/security/throttle.py
"""
Throttling progresivo de intentos de login (SEC-01).

Diseño:
    - Cada intento (éxito o fallo) se registra en `login_attempts`.
    - Se cuentan los fallos consecutivos desde el último éxito.
    - A partir del 5º fallo se aplica un delay exponencial:
          1s, 2s, 4s, 8s, 16s, ... hasta un tope de 15 minutos.
    - Un login exitoso resetea el contador del usuario.
    - La cuenta NUNCA se bloquea (active=0), solo se retrasa.
      Esto evita que un atacante pueda DoS-ear usuarios legítimos.

Ventana de conteo: 1 hora. Intentos más viejos se ignoran.
Limpieza: `cleanup_old_attempts()` se llama desde un cron diario.
"""
import logging
from datetime import datetime, timedelta

from app.utils.db import get_db_connection

logger = logging.getLogger(__name__)


# ============================================================
# CONFIGURACIÓN
# ============================================================
MAX_ATTEMPTS_BEFORE_DELAY = 5      # fallos antes de empezar a retrasar
MAX_DELAY_SECONDS = 15 * 60        # tope: 15 minutos
WINDOW_MINUTES = 60                # ventana de conteo


# ============================================================
# CÁLCULO DEL DELAY
# ============================================================
def _delay_for(failures: int) -> int:
    """
    Delay exponencial según la cantidad de fallos consecutivos.

    failures < 5  -> 0s (sin throttle)
    failures = 5  -> 1s
    failures = 6  -> 2s
    failures = 7  -> 4s
    ...
    failures >= 15 -> 900s (tope)
    """
    if failures < MAX_ATTEMPTS_BEFORE_DELAY:
        return 0
    return min(2 ** (failures - MAX_ATTEMPTS_BEFORE_DELAY), MAX_DELAY_SECONDS)


# ============================================================
# CONSULTAS
# ============================================================
def get_consecutive_failures(username: str) -> int:
    """
    Cantidad de fallos consecutivos desde el último login exitoso
    (o desde siempre si nunca logró entrar). Ventana: 1 hora.
    """
    conn = get_db_connection()
    if not conn:
        return 0
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT COUNT(*) AS n
            FROM login_attempts
            WHERE username = %s
              AND success = 0
              AND attempted_at > NOW() - INTERVAL %s MINUTE
              AND attempted_at > COALESCE(
                  (SELECT MAX(attempted_at)
                     FROM login_attempts
                    WHERE username = %s AND success = 1),
                  '1970-01-01 00:00:00'
              )
        """, (username, WINDOW_MINUTES, username))
        row = cursor.fetchone()
        return int(row['n']) if row else 0
    finally:
        cursor.close()
        conn.close()


def get_throttle_remaining(username: str) -> int:
    """
    Segundos que faltan para poder intentar de nuevo.
    0 si no hay throttle activo (se puede intentar ya).
    """
    failures = get_consecutive_failures(username)
    delay = _delay_for(failures)
    if delay == 0:
        return 0

    conn = get_db_connection()
    if not conn:
        return 0
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT attempted_at
              FROM login_attempts
             WHERE username = %s AND success = 0
             ORDER BY attempted_at DESC
             LIMIT 1
        """, (username,))
        row = cursor.fetchone()
        if not row:
            return 0

        unlock_at = row['attempted_at'] + timedelta(seconds=delay)
        remaining = (unlock_at - datetime.now()).total_seconds()
        return max(0, int(remaining))
    finally:
        cursor.close()
        conn.close()


# ============================================================
# REGISTRO
# ============================================================
def record_attempt(username: str, ip: str, success: bool) -> None:
    """
    Registra un intento de login. Nunca lanza excepción: si falla el
    INSERT, solo lo loguea. Un fallo de auditoría no debe romper el login.
    """
    conn = get_db_connection()
    if not conn:
        return
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO login_attempts (username, ip_address, success)
            VALUES (%s, %s, %s)
        """, (username, ip, 1 if success else 0))
        conn.commit()
    except Exception as exc:
        logger.warning('[throttle] No se pudo registrar intento: %s', exc)
    finally:
        cursor.close()
        conn.close()


# ============================================================
# MANTENIMIENTO
# ============================================================
def cleanup_old_attempts(days: int = 30) -> int:
    """
    Borra intentos con más de N días de antigüedad.
    Pensado para correr desde un cron diario (ver README).
    Devuelve la cantidad de filas borradas.
    """
    conn = get_db_connection()
    if not conn:
        return 0
    cursor = conn.cursor()
    try:
        cursor.execute("""
            DELETE FROM login_attempts
             WHERE attempted_at < NOW() - INTERVAL %s DAY
        """, (days,))
        conn.commit()
        return cursor.rowcount
    except Exception as exc:
        logger.warning('[throttle] Error en cleanup: %s', exc)
        return 0
    finally:
        cursor.close()
        conn.close()