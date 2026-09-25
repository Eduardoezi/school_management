from app.utils.db import get_db_connection
import logging

# ============================================================
# Logger del módulo
# ============================================================
logger = logging.getLogger(__name__)


class StudentDetail:
    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM student_details WHERE student_id = %s", (student_id,))
        row = cursor.fetchone()
        cursor.close(); conn.close()
        return row

    @staticmethod
    def save(student_id, data):
        """Crea o actualiza los detalles del estudiante (1:1)."""
        conn = get_db_connection()
        if not conn: return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO student_details
                    (student_id, sex, birth_place, laterality,
                     shirt_size, pants_size, shoe_size, contact_phone,
                     address, municipality, parish, state)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    sex           = VALUES(sex),
                    birth_place   = VALUES(birth_place),
                    laterality    = VALUES(laterality),
                    shirt_size    = VALUES(shirt_size),
                    pants_size    = VALUES(pants_size),
                    shoe_size     = VALUES(shoe_size),
                    contact_phone = VALUES(contact_phone),
                    address       = VALUES(address),
                    municipality  = VALUES(municipality),
                    parish        = VALUES(parish),
                    state         = VALUES(state)
            """, (student_id, data.get('sex'), data.get('birth_place'),
                  data.get('laterality'), data.get('shirt_size'),
                  data.get('pants_size'), data.get('shoe_size'),
                  data.get('contact_phone'), data.get('address'),
                  data.get('municipality'), data.get('parish'), data.get('state')))
            conn.commit()
            return True
        except Exception as e:
            logger.exception("Error en el metodo save de la clase StudentDetail: %s", e)
            return False
        finally:
            cursor.close(); conn.close()