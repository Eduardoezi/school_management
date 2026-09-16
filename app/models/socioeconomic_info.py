from app.utils.db import get_db_connection


class SocioeconomicInfo:
    @staticmethod
    def get_by_student(student_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM student_socioeconomic WHERE student_id = %s", (student_id,))
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
                data.get('lives_with'), data.get('other_family_members'),
                data.get('working_members') or None,
                data.get('monthly_income') or None,
                data.get('household_members') or None,
                data.get('housing_type'), data.get('rooms_count') or None,
                data.get('housing_condition'), data.get('housing_infrastructure')
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[SocioeconomicInfo.save] {e}")
            return False
        finally:
            cursor.close(); conn.close()