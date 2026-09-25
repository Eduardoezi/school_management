"""Historial de revisiones y recomendaciones sobre un plan de aula."""

from __future__ import annotations

from typing import Optional

from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


class PlanReview:

    @staticmethod
    def create(plan_id: int,
               reviewer_id: int,
               action: str,
               comment: Optional[str] = None) -> Optional[int]:
        """
        Registra una revisión.
        `action` debe ser uno de: comentario, aprobado, devuelto, archivado.
        """
        if action not in ('comentario', 'aprobado', 'devuelto', 'archivado'):
            return None

        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO plan_reviews (plan_id, reviewer_id, action, comment)
                VALUES (%s, %s, %s, %s)
            """, (plan_id, reviewer_id, action, (comment or '').strip() or None))
            conn.commit()
            return cursor.lastrowid
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo create de la clase Planreview: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_plan(plan_id: int) -> list[dict]:
        """Todas las revisiones de un plan, más recientes primero."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT r.*,
                       u.username    AS reviewer_username,
                       u.role        AS reviewer_role
                  FROM plan_reviews r
                  JOIN users u ON r.reviewer_id = u.id
                 WHERE r.plan_id = %s
                 ORDER BY r.created_at DESC
            """, (plan_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()