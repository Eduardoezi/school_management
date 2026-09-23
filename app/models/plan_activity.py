"""
Actividades pedagógicas dentro de un área de plan.

Cada actividad puede convertirse en un evento del calendario cuando
el plan pasa a estado 'publicado' (Fase 6).
"""

from __future__ import annotations

from typing import Optional

from app.utils.db import get_db_connection


class PlanActivity:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_by_id(activity_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM plan_activities WHERE id = %s", (activity_id,)
            )
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_area(area_id: int) -> list[dict]:
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM plan_activities
                 WHERE plan_area_id = %s
                 ORDER BY sort_order, id
            """, (area_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_plan(plan_id: int) -> list[dict]:
        """Todas las actividades de un plan (join con áreas)."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT a.*, ar.formation_area
                  FROM plan_activities a
                  JOIN plan_areas ar ON a.plan_area_id = ar.id
                 WHERE ar.plan_id = %s
                 ORDER BY ar.sort_order, a.sort_order
            """, (plan_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(area_id: int, data: dict) -> Optional[int]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT COALESCE(MAX(sort_order), 0) + 1 FROM plan_activities WHERE plan_area_id = %s",
                (area_id,)
            )
            next_order = cursor.fetchone()[0]

            cursor.execute("""
                INSERT INTO plan_activities (
                    plan_area_id, title, description, strategy, indicators,
                    resources, evaluation_technique, evaluation_instrument,
                    curricular_emphasis, start_datetime, end_datetime,
                    location, sort_order
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                area_id,
                (data.get('title') or '').strip(),
                data.get('description') or None,
                data.get('strategy') or None,
                data.get('indicators') or None,
                data.get('resources') or None,
                data.get('evaluation_technique') or None,
                data.get('evaluation_instrument') or None,
                data.get('curricular_emphasis') or None,
                data.get('start_datetime') or None,
                data.get('end_datetime') or None,
                data.get('location') or None,
                next_order,
            ))
            conn.commit()
            return cursor.lastrowid
        except Exception as exc:
            conn.rollback()
            print(f"[PlanActivity.create] {exc}")
            return None
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def update(activity_id: int, data: dict) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE plan_activities SET
                    title                  = %s,
                    description            = %s,
                    strategy               = %s,
                    indicators             = %s,
                    resources              = %s,
                    evaluation_technique   = %s,
                    evaluation_instrument  = %s,
                    curricular_emphasis    = %s,
                    start_datetime         = %s,
                    end_datetime           = %s,
                    location               = %s
                 WHERE id = %s
            """, (
                (data.get('title') or '').strip(),
                data.get('description') or None,
                data.get('strategy') or None,
                data.get('indicators') or None,
                data.get('resources') or None,
                data.get('evaluation_technique') or None,
                data.get('evaluation_instrument') or None,
                data.get('curricular_emphasis') or None,
                data.get('start_datetime') or None,
                data.get('end_datetime') or None,
                data.get('location') or None,
                activity_id,
            ))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[PlanActivity.update] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def delete(activity_id: int) -> bool:
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute(
                "DELETE FROM plan_activities WHERE id = %s", (activity_id,)
            )
            conn.commit()
            return cursor.rowcount > 0
        except Exception as exc:
            conn.rollback()
            print(f"[PlanActivity.delete] {exc}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def mark_as_calendar_published(activity_id: int, event_id: int) -> bool:
        """Se llama en Fase 6 al publicar el plan."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                UPDATE plan_activities
                   SET is_calendar_published = 1,
                       calendar_event_id = %s
                 WHERE id = %s
            """, (event_id, activity_id))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            cursor.close()
            conn.close()