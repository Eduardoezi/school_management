# app/models/medical_info.py
from app.utils.db import get_db_connection
from app.utils.crypto import encrypt_sensitive, decrypt_sensitive
import logging

logger = logging.getLogger(__name__)


# Campos que se cifran antes de guardar
CAMPOS_CIFRADOS = (
    'vaccine_others',
    'allergies',
    'chronic_conditions',
    'convulsions',
    'current_medication',
    'medical_attention',
    'upen_attention',
    'fever_protocol',
    'report_medical',
    'report_psychological',
    'report_neurological',
)


class MedicalInfo:
    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute(
                "SELECT * FROM student_medical WHERE student_id = %s",
                (student_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None
            # Descifrar los campos sensibles antes de devolver
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
            # Cifrar los campos sensibles antes de armar el SQL
            d = dict(data)
            for campo in CAMPOS_CIFRADOS:
                d[campo] = encrypt_sensitive(d.get(campo))

            cursor.execute("""
                INSERT INTO student_medical
                    (student_id, vaccine_bcg, vaccine_polio, vaccine_triple,
                     vaccine_measles, vaccine_rubella, vaccine_yellow_fever,
                     vaccine_toxoid, vaccine_covid_1, vaccine_covid_2,
                     vaccine_covid_3, vaccine_others, allergies,
                     chronic_conditions, convulsions, current_medication,
                     medical_attention, upen_attention, fever_protocol,
                     report_medical, report_psychological, report_neurological)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    vaccine_bcg          = VALUES(vaccine_bcg),
                    vaccine_polio        = VALUES(vaccine_polio),
                    vaccine_triple       = VALUES(vaccine_triple),
                    vaccine_measles      = VALUES(vaccine_measles),
                    vaccine_rubella      = VALUES(vaccine_rubella),
                    vaccine_yellow_fever = VALUES(vaccine_yellow_fever),
                    vaccine_toxoid       = VALUES(vaccine_toxoid),
                    vaccine_covid_1      = VALUES(vaccine_covid_1),
                    vaccine_covid_2      = VALUES(vaccine_covid_2),
                    vaccine_covid_3      = VALUES(vaccine_covid_3),
                    vaccine_others       = VALUES(vaccine_others),
                    allergies            = VALUES(allergies),
                    chronic_conditions   = VALUES(chronic_conditions),
                    convulsions          = VALUES(convulsions),
                    current_medication   = VALUES(current_medication),
                    medical_attention    = VALUES(medical_attention),
                    upen_attention       = VALUES(upen_attention),
                    fever_protocol       = VALUES(fever_protocol),
                    report_medical       = VALUES(report_medical),
                    report_psychological = VALUES(report_psychological),
                    report_neurological  = VALUES(report_neurological)
            """, (
                student_id,
                d.get('vaccine_bcg') or None,
                d.get('vaccine_polio') or None,
                d.get('vaccine_triple') or None,
                d.get('vaccine_measles') or None,
                d.get('vaccine_rubella') or None,
                d.get('vaccine_yellow_fever') or None,
                d.get('vaccine_toxoid') or None,
                d.get('vaccine_covid_1') or None,
                d.get('vaccine_covid_2') or None,
                d.get('vaccine_covid_3') or None,
                d.get('vaccine_others'),
                d.get('allergies'),
                d.get('chronic_conditions'),
                d.get('convulsions'),
                d.get('current_medication'),
                d.get('medical_attention'),
                d.get('upen_attention'),
                d.get('fever_protocol'),
                d.get('report_medical'),
                d.get('report_psychological'),
                d.get('report_neurological'),
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en save de MedicalInfo: %s", e)
            return False
        finally:
            cursor.close()
            conn.close()