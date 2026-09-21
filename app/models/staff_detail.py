from app.utils.db import get_db_connection
from app.utils.crypto import encrypt_str


class StaffDetail:
    @staticmethod
    def get_by_teacher(teacher_id):
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            "SELECT * FROM staff_details WHERE teacher_id = %s",
            (teacher_id,)
        )
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row

    @staticmethod
    def save(teacher_id, data):
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            # --- Cifrar número de cuenta si viene ---
            account_number = (data.get('bank_account_number') or '').strip()
            encrypted = None
            last6 = None
            if account_number:
                digits = ''.join(c for c in account_number if c.isdigit())
                if len(digits) >= 6:
                    encrypted = encrypt_str(digits)
                    last6 = digits[-6:]

            cursor.execute("""
                INSERT INTO staff_details
                    (teacher_id, codigo_rac, cargo, staff_type, specialist_type,
                     nominal_condition, sex,
                     shirt_size, pants_size, shoe_size,
                     academic_hours, admin_hours, shift,
                     worker_status, observations, specialty,
                     birth_city, birth_state,
                     bank_name, bank_account_type,
                     bank_account_number_encrypted, bank_account_last6)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    codigo_rac        = VALUES(codigo_rac),
                    cargo             = VALUES(cargo),
                    staff_type        = VALUES(staff_type),
                    specialist_type   = VALUES(specialist_type),
                    nominal_condition = VALUES(nominal_condition),
                    sex               = VALUES(sex),
                    shirt_size        = VALUES(shirt_size),
                    pants_size        = VALUES(pants_size),
                    shoe_size         = VALUES(shoe_size),
                    academic_hours    = VALUES(academic_hours),
                    admin_hours       = VALUES(admin_hours),
                    shift             = VALUES(shift),
                    worker_status     = VALUES(worker_status),
                    observations      = VALUES(observations),
                    specialty         = VALUES(specialty),
                    birth_city        = VALUES(birth_city),
                    birth_state       = VALUES(birth_state),
                    bank_name         = VALUES(bank_name),
                    bank_account_type = VALUES(bank_account_type),
                    bank_account_number_encrypted =
                        IF(VALUES(bank_account_number_encrypted) IS NULL,
                           bank_account_number_encrypted,
                           VALUES(bank_account_number_encrypted)),
                    bank_account_last6 =
                        IF(VALUES(bank_account_last6) IS NULL,
                           bank_account_last6,
                           VALUES(bank_account_last6))
            """, (
                teacher_id,
                data.get('codigo_rac'),
                data.get('cargo'),
                data.get('staff_type') or None,
                data.get('specialist_type') or 'ninguno',
                data.get('nominal_condition') or None,
                data.get('sex') or None,
                data.get('shirt_size'),
                data.get('pants_size'),
                data.get('shoe_size'),
                data.get('academic_hours') or None,
                data.get('admin_hours') or None,
                data.get('shift'),
                data.get('worker_status'),
                data.get('observations'),
                data.get('specialty'),
                data.get('birth_city'),
                data.get('birth_state'),
                data.get('bank_name') or None,
                data.get('bank_account_type') or None,
                encrypted,
                last6,
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[StaffDetail.save] {e}")
            return False
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def get_bank_account(teacher_id):
        """Devuelve el número de cuenta DESCIFRADO (solo para admin)."""
        from app.utils.crypto import decrypt_str
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        try:
            cursor.execute("""
                SELECT bank_account_number_encrypted
                  FROM staff_details
                 WHERE teacher_id = %s
            """, (teacher_id,))
            row = cursor.fetchone()
            if not row or not row['bank_account_number_encrypted']:
                return None
            return decrypt_str(row['bank_account_number_encrypted'])
        finally:
            cursor.close()
            conn.close()