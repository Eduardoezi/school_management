"""
Modelo de años escolares.

Reglas de negocio:
    - Solo UN año puede estar `is_active = 1` a la vez.
    - Solo UN año puede estar `is_next = 1` a la vez (el que se prepara).
    - Al activar un año, el anterior se desactiva automáticamente.
    - No se permite eliminar un año con planes asociados.
"""
from __future__ import annotations
import logging
from typing import Optional
import mysql.connector
from app.utils.db import get_db_connection

logger = logging.getLogger(__name__)

class AcademicYear:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_all() -> list[dict]:
        """Todos los años, más recientes primero."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT *
                  FROM academic_years
                 ORDER BY start_date DESC
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(year_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM academic_years WHERE id = %s", (year_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_active() -> Optional[dict]:
        """El año escolar activo actual. Base del módulo de planes."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM academic_years WHERE is_active = 1 LIMIT 1"
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_next() -> Optional[dict]:
        """El año que se está preparando para el siguiente ciclo."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM academic_years WHERE is_next = 1 LIMIT 1"
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(name: str, start_date: str, end_date: str) -> Optional[int]:
        """
        Crea un año escolar.
        No lo activa ni lo marca como próximo: eso se hace con
        activate() o mark_as_next().
        """
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO academic_years (name, start_date, end_date)
                VALUES (%s, %s, %s)
            """, (name.strip(), start_date, end_date))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as exc:
            logger.exception("Error de integridad en AcademicYear.create: %s", exc)
            return None
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en AcademicYear.create: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def activate(year_id: int) -> bool:
        """
        Activa un año y desactiva el anterior.
        Todo en una transacción.
        """
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            # Desactivar cualquier otro año activo
            cursor.execute("""
                UPDATE academic_years
                   SET is_active = 0
                 WHERE is_active = 1 AND id <> %s
            """, (year_id,))

            # Activar el solicitado
            cursor.execute("""
                UPDATE academic_years
                   SET is_active = 1, is_next = 0
                 WHERE id = %s
            """, (year_id,))

            if cursor.rowcount == 0:
                conn.rollback()
                return False

            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en AcademicYear.activate: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def mark_as_next(year_id: int) -> bool:
        """
        Marca un año como 'próximo' (en preparación). No lo activa.
        Solo puede haber uno.
        """
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE academic_years
                   SET is_next = 0
                 WHERE is_next = 1 AND id <> %s
            """, (year_id,))

            cursor.execute("""
                UPDATE academic_years
                   SET is_next = 1
                 WHERE id = %s AND is_active = 0
            """, (year_id,))

            if cursor.rowcount == 0:
                conn.rollback()
                return False

            conn.commit()
            return True
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en AcademicYear.mark_as_next: %s", exc)
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def has_dependencies(year_id: int) -> bool:
        """
        Devuelve True si el año tiene planes u otros datos asociados.
        Se usa para bloquear borrados peligrosos.
        """
        conn = get_db_connection()
        if not conn:
            return True  # ante la duda, bloquear
        cursor = conn.cursor()
        try:
            cursor.execute("""
                SELECT EXISTS(
                    SELECT 1 FROM classroom_plans
                     WHERE academic_year_id = %s
                     LIMIT 1
                )
            """, (year_id,))
            row = cursor.fetchone()
            return bool(row and row[0])
        except Exception:
            return True
        finally:
            cursor.close()
            conn.close()

@staticmethod
def delete(year_id: int) -> bool:
    """
    Elimina un año escolar. NO debe llamarse si tiene dependencias
    (usa has_dependencies() primero).
    """
    conn = get_db_connection()
    if not conn:
        return False
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM academic_years WHERE id = %s", (year_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as exc:
        conn.rollback()
        logger.exception("Error en AcademicYear.delete: %s", exc)
        return False
    finally:
        cursor.close()
        conn.close()