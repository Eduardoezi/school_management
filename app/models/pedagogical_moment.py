"""
Modelo del catálogo de momentos pedagógicos.

En la práctica del MPPE se llaman "momentos pedagógicos" (I, II, III Momento),
pero en el uso diario se llaman "lapsos" (1er Lapso, 2do Lapso, 3er Lapso).

Este catálogo es administrable por el directivo y condiciona los períodos
de evaluación: cada período debe estar vinculado a un momento pedagógico.
"""

from __future__ import annotations

from typing import Optional

import mysql.connector

from app.utils.db import get_db_connection


class PedagogicalMoment:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_all(only_active: bool = True) -> list[dict]:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            sql = "SELECT * FROM pedagogical_moments"
            if only_active:
                sql += " WHERE is_active = 1"
            sql += " ORDER BY sort_order, name"
            cursor.execute(sql)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(moment_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM pedagogical_moments WHERE id = %s", (moment_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_name(name: str) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM pedagogical_moments WHERE name = %s LIMIT 1",
                (name,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def count_periods_using(moment_id: int) -> int:
        """Cuántos períodos usan este momento (para bloquear desactivación)."""
        conn = get_db_connection()
        if not conn:
            return 0
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COUNT(*) FROM evaluation_periods WHERE pedagogical_moment_id = %s",
                (moment_id,)
            )
            row = cursor.fetchone()
            return int(row[0]) if row else 0
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(name: str, sort_order: int = 0) -> Optional[int]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO pedagogical_moments (name, sort_order)
                VALUES (%s, %s)
            """, (name.strip(), sort_order))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError:
            return None
        except Exception as exc:
            conn.rollback()
            print(f"[PedagogicalMoment.create] {exc}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(moment_id: int, name: str, sort_order: int, is_active: bool) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE pedagogical_moments
                SET name = %s,
                    sort_order = %s,
                    is_active = %s
                WHERE id = %s
            """, (name.strip(), sort_order, 1 if is_active else 0, moment_id))
            conn.commit()

            # MySQL devuelve rowcount=0 si los valores son idénticos.
            # Verificamos que la fila exista para no reportar falso error.
            if cursor.rowcount > 0:
                return True

            cursor.execute("SELECT id FROM pedagogical_moments WHERE id = %s", (moment_id,))
            return cursor.fetchone() is not None

        except Exception as exc:
            conn.rollback()
            print(f"[PedagogicalMoment.update] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()
        @staticmethod
        def soft_toggle(moment_id: int, active: bool) -> bool:
            """Activa/desactiva sin borrar (preserva históricos)."""
            conn = get_db_connection()
            if not conn:
                return False
            cursor = conn.cursor()
            try:
                cursor.execute("""
                    UPDATE pedagogical_moments
                    SET is_active = %s
                    WHERE id = %s
                """, (1 if active else 0, moment_id))
                conn.commit()
                return cursor.rowcount > 0
            except Exception as exc:
                conn.rollback()
                print(f"[PedagogicalMoment.soft_toggle] {exc}")
                return False
            finally:
                cursor.close()
                conn.close()