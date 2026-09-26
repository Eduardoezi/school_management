# app/models/socioeconomic_info.py
from app.utils.db import get_db_connection
from app.utils.crypto import encrypt_sensitive, decrypt_sensitive
import logging

logger = logging.getLogger(__name__)


# Campos que se cifran antes de guardar
CAMPOS_CIFRADOS = (
    'other_family_members',
    'monthly_income',
    'housing_infrastructure',
)


class SocioeconomicInfo:
    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM student_socioeconomic WHERE student_id = %s",
                (student_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            for campo in CAMPOS_CIFRADOS:
                if campo in row:
                    row[campo] = decrypt_sensitive(row[campo])
            return row
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def save(student_id, data):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            d = dict(data)
            for campo in CAMPOS_CIFRADOS:
                # monthly_income es Decimal → convertir a str antes de cifrar
                valor = d.get(campo)
                if valor is not None and not isinstance(valor, str):
                    valor = str(valor)
                d[campo] = encrypt_sensitive(valor)

            cursor.execute("""
                INSERT INTO student_socioeconomic
                    (student_id, lives_with, other_family_members,
                     working_members, monthly_income, household_members,
                     housing_type, rooms_count, housing_condition,
                     housing_infrastructure)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    lives_with             = VALUES(lives_with),
                    other_family_members   = VALUES(other_family_members),
                    working_members        = VALUES(working_members),
                    monthly_income         = VALUES(monthly_income),
                    household_members      = VALUES(household_members),
                    housing_type           = VALUES(housing_type),
                    rooms_count            = VALUES(rooms_count),
                    housing_condition      = VALUES(housing_condition),
                    housing_infrastructure = VALUES(housing_infrastructure)
            """, (
                student_id,
                d.get('lives_with'),
                d.get('other_family_members'),
                d.get('working_members') or None,
                d.get('monthly_income'),
                d.get('household_members') or None,
                d.get('housing_type'),
                d.get('rooms_count') or None,
                d.get('housing_condition'),
                d.get('housing_infrastructure'),
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en save de SocioeconomicInfo: %s", e)
            return False
        finally:
            cursor.close()
            conn.close()