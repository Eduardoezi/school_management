# run.py
import os
import socket

from app import create_app

try:
    from zeroconf import ServiceInfo, Zeroconf
    HAS_ZEROCONF = True
except ImportError:
    HAS_ZEROCONF = False


app = create_app()


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
    if not HAS_ZEROCONF:
        print("i  zeroconf no instalado. Los clientes deberan usar el dominio directamente.")
        return None, None

    info = ServiceInfo(
        "_https._tcp.local.",
        "Sistema Escolar._https._tcp.local.",
        addresses=[socket.inet_aton(ip)],
        port=port,
        properties={'path': '/'},
        server="gestionescolar.duckdns.org.",
    )
    zc = Zeroconf()
    zc.register_service(info)
    return zc, info


if __name__ == '__main__':
    host  = app.config.get('HOST', '0.0.0.0')
    port  = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', False)

    ssl_cert = app.config.get('SSL_CERT')
    ssl_key  = app.config.get('SSL_KEY')

    ssl_context = None
    if ssl_cert and ssl_key and os.path.exists(ssl_cert) and os.path.exists(ssl_key):
        ssl_context = (ssl_cert, ssl_key)

    zc, info = (None, None)
    if ssl_context:
        local_ip = _get_local_ip()
        zc, info = _register_mdns(local_ip, port)

    scheme = 'https' if ssl_context else 'http'
    public_url = f"{scheme}://gestionescolar.duckdns.org:{port}" if ssl_context \
                 else f"{scheme}://{host}:{port}"

    print(f"Servidor iniciado en {public_url}  (debug={debug})")
    if ssl_context:
        print("HTTPS activo con certificados de Let's Encrypt.")
    else:
        print("Sin HTTPS. WebAuthn NO funcionara.")
        print(f"   Acceso local:   http://127.0.0.1:{port}")
        print(f"   Acceso en red:  http://<tu-ip-local>:{port}")

    try:
        app.run(
            host=host,
            port=port,
            debug=debug,
            ssl_context=ssl_context,
        )
    finally:
        if zc and info:
            zc.unregister_service(info)
            zc.close()