from app import create_app
import os

app = create_app()

if __name__ == '__main__':
    # Rutas a los certificados SSL (opcional)
    cert_path = os.path.join('certs', 'cert.pem')
    key_path = os.path.join('certs', 'key.pem')

    # Escuchar en todas las interfaces de red para acceso desde otros equipos
    HOST = '0.0.0.0'
    PORT = 5000

    if os.path.exists(cert_path) and os.path.exists(key_path):
        print(f"🔒 Servidor HTTPS iniciado en https://{HOST}:{PORT}")
        app.run(host=HOST, port=PORT, debug=True,
                ssl_context=(cert_path, key_path))
    else:
        print(f"🌐 Servidor HTTP iniciado en http://{HOST}:{PORT}")
        print(f"   Acceso local:   http://127.0.0.1:{PORT}")
        print(f"   Acceso en red:  http://<tu-ip-local>:{PORT}")
        app.run(host=HOST, port=PORT, debug=True)