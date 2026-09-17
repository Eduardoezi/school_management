from app.utils.db import get_db_connection


class InstitutionData:
    @staticmethod
    def get():
        """Devuelve la fila única de datos institucionales. Crea una si no existe."""
        conn = get_db_connection()
        if not conn:
            return None
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM institution_data WHERE id = 1")
        row = cursor.fetchone()
        cursor.close()
        conn.close()

        if not row:
            # Crear por defecto si no existe
            InstitutionData._ensure_default()
            return InstitutionData.get()
        return row

    @staticmethod
    def _ensure_default():
        conn = get_db_connection()
        if not conn:
            return
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT IGNORE INTO institution_data (id, nombre, nombre_corto)
                VALUES (1, 'Institución Educativa', 'IE')
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    @staticmethod
    def save(data):
        """Actualiza la fila única."""
        conn = get_db_connection()
        if not conn:
            return False
        cursor = conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO institution_data
                    (id, nombre, nombre_corto, codigo_dea, codigo_dependencia,
                     codigo_administrativo, direccion, municipio, estado,
                     telefono, email, rif, logo_path)
                VALUES (1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    nombre                = VALUES(nombre),
                    nombre_corto          = VALUES(nombre_corto),
                    codigo_dea            = VALUES(codigo_dea),
                    codigo_dependencia    = VALUES(codigo_dependencia),
                    codigo_administrativo = VALUES(codigo_administrativo),
                    direccion             = VALUES(direccion),
                    municipio             = VALUES(municipio),
                    estado                = VALUES(estado),
                    telefono              = VALUES(telefono),
                    email                 = VALUES(email),
                    rif                   = VALUES(rif),
                    logo_path             = VALUES(logo_path)
            """, (
                data.get('nombre'),
                data.get('nombre_corto'),
                data.get('codigo_dea'),
                data.get('codigo_dependencia'),
                data.get('codigo_administrativo'),
                data.get('direccion'),
                data.get('municipio'),
                data.get('estado'),
                data.get('telefono'),
                data.get('email'),
                data.get('rif'),
                data.get('logo_path') or 'img/logo_institucional.png'
            ))
            conn.commit()
            return True
        except Exception as e:
            print(f"[InstitutionData.save] {e}")
            return False
        finally:
            cursor.close()
            conn.close()