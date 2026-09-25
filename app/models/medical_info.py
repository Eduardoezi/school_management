from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


class MedicalInfo:
    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM student_medical WHERE student_id = %s", (student_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def save(student_id, data):
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
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
                data.get('vaccine_bcg') or None, data.get('vaccine_polio') or None,
                data.get('vaccine_triple') or None, data.get('vaccine_measles') or None,
                data.get('vaccine_rubella') or None, data.get('vaccine_yellow_fever') or None,
                data.get('vaccine_toxoid') or None, data.get('vaccine_covid_1') or None,
                data.get('vaccine_covid_2') or None, data.get('vaccine_covid_3') or None,
                data.get('vaccine_others'), data.get('allergies'),
                data.get('chronic_conditions'), data.get('convulsions'),
                data.get('current_medication'), data.get('medical_attention'),
                data.get('upen_attention'), data.get('fever_protocol'),
                data.get('report_medical'), data.get('report_psychological'),
                data.get('report_neurological')
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en el metodo save de la clase MedicalInfo: %s", e)
            return False
        finally:
            cursor.close(); conn.close()