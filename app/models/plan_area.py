"""
Áreas de formación dentro de un plan de aula.

Un plan tiene N áreas (Matemática, Lengua, Ciencias, etc.).
Cada área tiene N actividades (ver PlanActivity).
"""

from __future__ import annotations

from typing import Optional

from app.utils.db import get_db_connection


class PlanArea:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_by_id(area_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM plan_areas WHERE id = %s", (area_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_plan(plan_id: int) -> list[dict]:
        """Todas las áreas de un plan, ordenadas."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM plan_areas
                 WHERE plan_id = %s
                 ORDER BY sort_order, id
            """, (plan_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(plan_id: int, data: dict) -> Optional[int]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            # Calcular el siguiente sort_order
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM plan_areas WHERE plan_id = %s",
                (plan_id,)
            )
            next_order = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO plan_areas (
                    plan_id, formation_area, pedagogical_approach,
                    curricular_components, essential_themes, contents,
                    expected_learning, tasks, sort_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                plan_id,
                (data.get('formation_area') or '').strip(),
                data.get('pedagogical_approach') or None,
                data.get('curricular_components') or None,
                data.get('essential_themes') or None,
                data.get('contents') or None,
                data.get('expected_learning') or None,
                data.get('tasks') or None,
                next_order,
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as exc:
            conn.rollback()
            print(f"[PlanArea.create] {exc}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(area_id: int, data: dict) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE plan_areas SET
                    formation_area         = %s,
                    pedagogical_approach   = %s,
                    curricular_components  = %s,
                    essential_themes       = %s,
                    contents               = %s,
                    expected_learning      = %s,
                    tasks                  = %s
                 WHERE id = %s
            """, (
                (data.get('formation_area') or '').strip(),
                data.get('pedagogical_approach') or None,
                data.get('curricular_components') or None,
                data.get('essential_themes') or None,
                data.get('contents') or None,
                data.get('expected_learning') or None,
                data.get('tasks') or None,
                area_id,
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[PlanArea.update] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(area_id: int) -> bool:
        """Elimina un área. Las actividades caen por ON DELETE CASCADE."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("DELETE FROM plan_areas WHERE id = %s", (area_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[PlanArea.delete] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()