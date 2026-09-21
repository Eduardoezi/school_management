"""Cifrado simétrico para datos sensibles.

Usa Fernet (AES-128 en CBC + HMAC-SHA256) para cifrar campos
como números de cuenta bancaria.

La clave se lee de la variable de entorno BANK_ENCRYPTION_KEY.
Si no está configurada, el cifrado no está disponible y cualquier
intento de cifrar/descifrar lanza RuntimeError.
"""

from __future__ import annotations

import os

from cryptography.fernet import Fernet, InvalidToken


def _get_cipher() -> Fernet:
    key = os.getenv('BANK_ENCRYPTION_KEY')
    if not key:
        raise RuntimeError(
            'BANK_ENCRYPTION_KEY no está configurada en el .env. '
            'Genera una con: python -c "from cryptography.fernet import Fernet; '
            'print(Fernet.generate_key().decode())"'
        )
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_str(plaintext: str) -> bytes:
    """Cifra un string. Devuelve bytes listos para VARBINARY."""
    if not plaintext:
        return None
    return _get_cipher().encrypt(plaintext.encode('utf-8'))


def decrypt_str(ciphertext: bytes) -> str | None:
    """Descifra bytes. Devuelve el string original o None si falla."""
    if not ciphertext:
        return None
    try:
        return _get_cipher().decrypt(ciphertext).decode('utf-8')
    except (InvalidToken, Exception):
        return None