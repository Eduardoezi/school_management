"""
WSGI entry point.

Servidores de producción leen `app` desde este módulo:

    # Windows (Waitress) — usar serve.py
    python serve.py

    # Linux (Gunicorn)
    gunicorn "wsgi:app" --bind 127.0.0.1:8000 --workers 3 --timeout 60

    # Linux (uWSGI)
    uwsgi --module wsgi:app --http 127.0.0.1:8000 --processes 4

Nunca uses `python wsgi.py` en producción: solo importa la app y la deja
disponible para el servidor.
"""

from app import create_app

# La app se construye una sola vez al importar este módulo.
# Todos los workers del servidor WSGI la comparten.
app = create_app()