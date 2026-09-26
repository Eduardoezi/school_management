# app/security/rate_limit.py
"""
Instancia global de Flask-Limiter (SEC-01).

Storage:
    Por defecto memory:// — válido para una sola instancia de Waitress
    con múltiples hilos (el caso de este proyecto). Si en el futuro
    se escala horizontalmente (varios procesos/procesadores), cambiar
    a Redis:

        RATELIMIT_STORAGE_URI=redis://localhost:6379

Ref: https://flask-limiter.readthedocs.io/en/stable/
"""
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address


limiter = Limiter(
    key_func=get_remote_address,
    # Sin límites por defecto: solo donde se decora explícitamente.
    default_limits=[],
    storage_uri='memory://',
    strategy='fixed-window',
    # Desactivar en tests si se necesita (con variables de entorno).
    headers_enabled=True,
)