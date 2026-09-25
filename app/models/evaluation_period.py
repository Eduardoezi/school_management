"""
Períodos de evaluación dentro de un momento pedagógico (lapso).

Cada lapso (PedagogicalMoment) tiene MÍNIMO TRES períodos de evaluación:
    1. Diagnóstico / Inicio
    2. Observación Formativa / Desarrollo
    3. Observación Calificativa / Cierre

La subdirección pedagógica puede editarlos, agregar más o cambiar sus
fechas y orden. El sistema los usa para:
    - Registrar evaluaciones por estudiante (`evaluations.period_id`)
    - Autocompletar fechas al crear un plan de aula
"""

from __future__ import annotations
from typing import Optional
import mysql.connector
from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)

class EvaluationPeriod:

    # ============================================================
    # Consultas
    # ============================================================
    @staticmethod
    def get_all() -> list[dict]:
        """
        Todos los períodos con el nombre del momento pedagógico
        al que están vinculados (JOIN con pedagogical_moments).
        """
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT p.*,
                       m.name       AS moment_name,
                       m.sort_order AS moment_sort_order
                  FROM evaluation_periods p
                  LEFT JOIN pedagogical_moments m
                         ON m.id = p.pedagogical_moment_id
                 ORDER BY m.sort_order, p.sort_order, p.name
            """)
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_moment(moment_id: int) -> list[dict]:
        """Períodos de un lapso específico, ordenados."""
        conn = get_db_connection()
        if not conn:
            return []
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT * FROM evaluation_periods
                 WHERE pedagogical_moment_id = %s
                 ORDER BY sort_order, name
            """, (moment_id,))
            return cursor.fetchall()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_by_id(period_id: int) -> Optional[dict]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT p.*,
                       m.name AS moment_name
                  FROM evaluation_periods p
                  LEFT JOIN pedagogical_moments m
                         ON m.id = p.pedagogical_moment_id
                 WHERE p.id = %s
            """, (period_id,))
            return cursor.fetchone()
        finally:
            cursor.close()
            conn.close()

    # ============================================================
    # Mutaciones
    # ============================================================
    @staticmethod
    def create(data: dict) -> Optional[int]:
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO evaluation_periods
                    (name, academic_year, start_date, end_date,
                     sort_order, pedagogical_moment_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                data['name'],
                data['academic_year'],
                data.get('start_date'),
                data.get('end_date'),
                data.get('sort_order', 0),
                data.get('pedagogical_moment_id'),
            ))
            conn.commit()
            return cursor.lastrowid
        except mysql.connector.IntegrityError as exc:
            conn.rollback()
            logger.exception("Error en el metodo create de la clase EvaluationPeriod Integridad: %s",  exc)
            return None
        except Exception as exc:
            conn.rollback()
            logger.exception("Error en el metodo create de la clase EvaluationPeriod: %s", exc)
            return None
        finally:
            cursor.close()
            conn.close()