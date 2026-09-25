"""
Servidor de DESARROLLO (Werkzeug).

    ⚠️  NO USAR EN PRODUCCIÓN.

Para producción usa:

    python serve.py

Variables relevantes (.env):
    HOST, PORT, SSL_CERT, SSL_KEY
    PUBLIC_MDNS_NAME (opcional, nombre .local anunciado por zeroconf;
                       por defecto 'sistema-escolar.local')
"""

import os
import socket
from pathlib import Path

from app import create_app


app = create_app()

BASE_DIR = Path(__file__).resolve().parent

DEFAULT_MDNS_NAME = 'sistema-escolar.local'


def _get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 1))
        return s.getsockname()[0]
    except Exception:
        return '127.0.0.1'
    finally:
        s.close()


def _register_mdns(ip: str, port: int, mdns_name: str):
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
        server=f'{mdns_name}.',
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

    # Nombre mDNS: configurable, sin dominio hardcodeado.
    mdns_name = os.getenv('PUBLIC_MDNS_NAME', DEFAULT_MDNS_NAME)

    zc, info = (None, None)
    if ssl_context:
        zc, info = _register_mdns(_get_local_ip(), port, mdns_name)

    # URL pública para el log
    public_url = os.getenv('PUBLIC_URL')
    if not public_url:
        if ssl_context:
            public_url = f'https://{mdns_name}:{port}'
        else:
            public_url = f'http://{host}:{port}'

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