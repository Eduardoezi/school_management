# app/utils/crypto.py
"""
Cifrado simétrico para datos sensibles.

Usa Fernet (AES-128-CBC + HMAC-SHA256) para cifrar campos.

Dos claves independientes (SEC-06 y SEC-09):
    BANK_ENCRYPTION_KEY  → números de cuenta bancaria del personal
    DATA_ENCRYPTION_KEY  → datos médicos y socioeconómicos de menores

Mantenerlas separadas permite rotar una sin tocar la otra.
"""

from __future__ import annotations

import os
from typing import Optional

from cryptography.fernet import Fernet, InvalidToken


def _get_cipher(env_var: str) -> Fernet:
    key = os.getenv(env_var)
    if not key:
        raise RuntimeError(
            f'{env_var} no está configurada en el .env. '
            'Genera una con: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


# ============================================================
# API para datos bancarios (SEC-06)
# ============================================================
def encrypt_str(plaintext: str) -> Optional[bytes]:
    """Cifra un string con la clave bancaria. Devuelve bytes."""
    if not plaintext:
        return None
    return _get_cipher('BANK_ENCRYPTION_KEY').encrypt(plaintext.encode('utf-8'))


def decrypt_str(ciphertext: bytes) -> Optional[str]:
    """Descifra bytes con la clave bancaria. Devuelve str o None."""
    if not ciphertext:
        return None
    try:
        return _get_cipher('BANK_ENCRYPTION_KEY').decrypt(ciphertext).decode('utf-8')
    except (InvalidToken, Exception):
        return None


# ============================================================
# API para datos sensibles de menores (SEC-09)
# ============================================================
def encrypt_sensitive(plaintext: Optional[str]) -> Optional[str]:
    """
    Cifra un texto con la clave DATA. Devuelve un string ASCII listo
    para guardar en columnas TEXT/VARCHAR.

    Si el input es None o vacío, devuelve None (no cifra la nada).
    """
    if plaintext is None or plaintext == '':
        return None
    ciphertext_bytes = _get_cipher('DATA_ENCRYPTION_KEY').encrypt(
        plaintext.encode('utf-8')
    )
    # Fernet ya devuelve base64 url-safe ASCII, así que podemos decodificar
    return ciphertext_bytes.decode('ascii')


def decrypt_sensitive(ciphertext: Optional[str]) -> Optional[str]:
    """
    Descifra un texto cifrado con encrypt_sensitive.

    Si el ciphertext no es válido (dato viejo en texto plano, por ejemplo),
    lo devuelve tal cual para no romper. Esto facilita migraciones
    incrementales.
    """
    if ciphertext is None or ciphertext == '':
        return None
    try:
        return _get_cipher('DATA_ENCRYPTION_KEY').decrypt(
            ciphertext.encode('ascii')
        ).decode('utf-8')
    except (InvalidToken, Exception):
        # Si el dato está en texto plano (no migrado todavía), devolverlo
        # tal cual. La migración posterior lo va a cifrar.
        return ciphertext