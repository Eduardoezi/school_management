from app.utils.db import get_db_connection
import mysql.connector

class Representative:
    @staticmethod
    def get_all():
        conn = get_db_connection()
        if not conn: return []
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM representatives ORDER BY last_name, first_name")
        reps = cursor.fetchall()
        cursor.close(); conn.close()
        return reps

    @staticmethod
    def get_by_cedula(cedula_id):
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM representatives WHERE cedula_id = %s", (cedula_id,))
        rep = cursor.fetchone()
        cursor.close(); conn.close()
        return rep

    @staticmethod
    def get_or_create(data):
        """
        Devuelve la cédula del representante.
        - Si ya existe (misma cédula), devuelve su cedula_id SIN modificar datos.
        - Si no existe, lo crea y devuelve su cedula_id.
        Retorna None si hubo error.
        """
        # 1. Buscar si ya existe
        existente = Representative.get_by_cedula(data['cedula_id'])
        if existente:
            # Ya existe: solo relacionamos, no tocamos sus datos
            return existente['cedula_id']

        # 2. No existe: crear
        conn = get_db_connection()
        if not conn: return None
        cursor = conn.cursor()
        sql = """INSERT INTO representatives 
                 (cedula_id, first_name, last_name, email, phone, address, relationship)
                 VALUES (%s, %s, %s, %s, %s, %s, %s)"""
        values = (data['cedula_id'], data['first_name'], data['last_name'],
                  data.get('email'), data.get('phone'), data.get('address'),
                  data.get('relationship'))
        try:
            cursor.execute(sql, values)
            conn.commit()
            return data['cedula_id']
        except mysql.connector.IntegrityError as e:
            print(f"Error al crear representante: {e}")
            return None
        finally:
            cursor.close(); conn.close()

    # También mantén create, update, etc.