"""
Servidor de DESARROLLO (Werkzeug).

    ⚠️  NO USAR EN PRODUCCIÓN.

Werkzeug sirve para desarrollo porque:
    - Tiene reloader automático (útil mientras programas).
    - Tiene debugger interactivo (útil para ver errores).
    - NO es seguro ni eficiente para usuarios reales.

Para producción usa:

    python serve.py

El servidor de producción (Waitress) no tiene reloader ni debugger.
"""

import os
import socket
from pathlib import Path

from app import create_app


app = create_app()

BASE_DIR = Path(__file__).resolve().parent


def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def _register_mdns(ip: str, port: int):
    try:
        from zeroconf import ServiceInfo, Zeroconf
    except ImportError:
        return None, None
    info = ServiceInfo(
        '_https._tcp.local.',
        'Sistema Escolar._https._tcp.local.',
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={'path': '/'},
        server='gestionescolar.local.',
    )
    zc = Zeroconf()
    zc.register_service(info)
    return zc, info


if __name__ == '__main__':
    print('=' * 60)
    print('  ⚠️  SERVIDOR DE DESARROLLO — NO USAR EN PRODUCCIÓN')
    print('  Para producción ejecuta:  python serve.py')
    print('=' * 60)

    host = app.config.get('HOST', '0.0.0.0')
    port = int(app.config.get('PORT', 5000))
    debug = app.config.get('DEBUG', True)

    ssl_cert = app.config.get('SSL_CERT')
    ssl_key = app.config.get('SSL_KEY')

    ssl_context = None
    if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)

    zc, info = (None, None)
    if ssl_context:
        zc, info = _register_mdns(_get_local_ip(), port)

    scheme = 'https' if ssl_context else 'http'
    public_url = (
        f'{scheme}://gestionescolar.local:{port}'
        if ssl_context else f'{scheme}://{host}:{port}'
    )

    print(f'  Servidor de desarrollo en {public_url}  (debug={debug})')

    try:
        app.run(
            host=host, port=port, debug=debug,
            ssl_context=ssl_context, use_reloader=True,
        )
    finally:
        if zc and info:
            zc.unregister_service(info)
            zc.close()