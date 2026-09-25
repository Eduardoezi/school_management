"""
Endpoints de salud para monitoreo.

- /health        → liveness:  ¿el proceso responde?
- /health/ready  → readiness: ¿MySQL está accesible?

Se excluyen de CSRF y no requieren login.
"""

from flask import Blueprint, jsonify

from app.utils.db import get_db_connection


health_bp = Blueprint('health', __name__)


@health_bp.route('/health')
def health():
    """Liveness probe. Rápida, sin tocar la BD."""
    return jsonify(status='ok', service='school_management'), 200


@health_bp.route('/health/ready')
def health_ready():
    """Readiness probe. Verifica que MySQL responde."""
    conn = get_db_connection()
    if conn is None:
        return jsonify(status='error', db='unreachable'), 503

    cursor = None
    try:
        cursor = conn.cursor()
        cursor.execute('SELECT 1')
        cursor.fetchone()
        return jsonify(status='ok', db='ok'), 200
    except Exception as exc:
        return jsonify(status='error', db=str(exc)), 503
    finally:
        try:
            if cursor:
                cursor.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass