"""
Servidor de producción con Waitress.

Waitress NO hace SSL. En producción se coloca detrás de Apache (o Nginx)
como reverse proxy que maneja el certificado y los headers de seguridad.

Uso:
    python serve.py

Variables de entorno relevantes (.env):
    HOST, PORT, BEHIND_PROXY,
    WAITRESS_THREADS, WAITRESS_CONNECTION_LIMIT, WAITRESS_CHANNEL_TIMEOUT,
    PUBLIC_URL (opcional, solo para el log de arranque)
"""

import os
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
    return os.getenv('BEHIND_PROXY', 'true').lower() in ('1', 'true', 'yes', 'on')


# ============================================================
# Aplicar ProxyFix para que Flask confíe en headers del proxy
# ============================================================
def _apply_proxy_fix(app):
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
        _apply_proxy_fix(app)
        scheme_public = 'https'
        print(f'[serve] Modo proxy: aplicando ProxyFix y esperando HTTP en {host}:{port}')
    else:
        scheme_public = 'http'
        print(f'[serve] Modo directo (sin proxy): sirviendo en {host}:{port}')

    # URL pública informativa — sin dominio hardcodeado.
    # Prioridad: PUBLIC_URL explícita > construida desde PUBLIC_HOST/PORT.
    public_url = os.getenv('PUBLIC_URL')
    if not public_url:
        public_host = os.getenv('PUBLIC_HOST', host)
        public_url = f'{scheme_public}://{public_host}:{port}'

    print('=' * 60)
    print('  Sistema Escolar — Servidor de producción (Waitress)')
    print('=' * 60)
    print(f'  Host:             {host}')
    print(f'  Puerto:           {port}')
    print(f'  Threads:          {threads}')
    print(f'  Connection limit: {connection_limit}')
    print(f'  Channel timeout:  {channel_timeout}s')
    print(f'  Behind proxy:     {behind_proxy}')
    print(f'  URL pública:      {public_url}')
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