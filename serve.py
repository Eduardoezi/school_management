"""
Servidor de producción con Waitress.

Reemplaza a `run.py` (Werkzeug) en producción. Waitress es:

    - Multiplataforma (Windows, Linux, macOS).
    - Puro Python, sin dependencias del sistema.
    - Robusto: soporta múltiples hilos, keep-alive.
    - Recomendado por la propia documentación de Flask y Django
      para producción.

IMPORTANTE: Waitress NO hace SSL. En producción se coloca detrás de
Apache (o Nginx) como reverse proxy que maneja el certificado y los
headers de seguridad. Ver `docs/DEPLOY.md`.

Uso:

    python serve.py

Para desarrollo local, usa `python run.py` (Werkzeug, con reloader).

Variables de entorno relevantes (.env):
    HOST, PORT,
    WAITRESS_THREADS, WAITRESS_CONNECTION_LIMIT, WAITRESS_CHANNEL_TIMEOUT
"""

import os
import socket
import sys
from pathlib import Path

from waitress import serve

from app import create_app


app = create_app()

BASE_DIR = Path(__file__).resolve().parent


# ============================================================
# Detectar si estamos detrás de un reverse proxy
# ============================================================
def _behind_proxy() -> bool:
    """
    True si hay un proxy adelante (Apache/Nginx).
    Cuando hay proxy, Waitress NO maneja SSL y solo escucha en localhost.
    """
    return os.getenv('BEHIND_PROXY', 'true').lower() in ('1', 'true', 'yes', 'on')


# ============================================================
# Aplicar ProxyFix para que Flask confíe en headers del proxy
# ============================================================
def _apply_proxy_fix(app):
    """
    Cuando Apache reenvía peticiones a Waitress, agrega headers
    X-Forwarded-For, X-Forwarded-Proto, etc. Werkzeug los ignora por
    defecto. ProxyFix le dice a Flask que confíe en esos headers.

    Sin esto, Flask cree que todas las peticiones vienen por HTTP
    (y rompe url_for con _external=True, redirects, cookies secure, etc.).
    """
    from werkzeug.middleware.proxy_fix import ProxyFix
    app.wsgi_app = ProxyFix(
        app.wsgi_app,
        x_for=1,
        x_proto=1,
        x_host=1,
        x_port=1,
        x_prefix=0,
    )
    return app


# ============================================================
# Main
# ============================================================
def main():
    host = app.config.get('HOST', '127.0.0.1')
    port = int(app.config.get('PORT', 8000))

    threads = int(os.getenv('WAITRESS_THREADS', '8'))
    connection_limit = int(os.getenv('WAITRESS_CONNECTION_LIMIT', '200'))
    channel_timeout = int(os.getenv('WAITRESS_CHANNEL_TIMEOUT', '120'))

    behind_proxy = _behind_proxy()

    if behind_proxy:
        # Cuando hay proxy, aplicar ProxyFix
        _apply_proxy_fix(app)
        scheme_public = 'https'
        print('[serve] Modo proxy: aplicando ProxyFix y esperando HTTP en ',
              f'{host}:{port}')
    else:
        scheme_public = 'http'
        print('[serve] Modo directo (sin proxy): sirviendo en ',
              f'{host}:{port}')

    print('=' * 60)
    print('  Sistema Escolar — Servidor de producción (Waitress)')
    print('=' * 60)
    print(f'  Host:             {host}')
    print(f'  Puerto:           {port}')
    print(f'  Threads:          {threads}')
    print(f'  Connection limit: {connection_limit}')
    print(f'  Channel timeout:  {channel_timeout}s')
    print(f'  Behind proxy:     {behind_proxy}')
    print(f'  URL pública:      {scheme_public}://gestionescolar.duckdns.org:5000')
    print('=' * 60)
    print('  Ctrl+C para detener')
    print('=' * 60)

    try:
        serve(
            app,
            host=host,
            port=port,
            threads=threads,
            connection_limit=connection_limit,
            channel_timeout=channel_timeout,
            url_scheme=scheme_public,
            ident='Sistema Escolar',
            # NO pasamos ssl_context: Apache hace SSL adelante.
        )
    except KeyboardInterrupt:
        print('\n[serve] Deteniendo servidor...')


if __name__ == '__main__':
    os.chdir(BASE_DIR)
    sys.exit(main() or 0)