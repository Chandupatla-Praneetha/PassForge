"""
Crypto utilities for PassForge.

Design (deliberately "zero-knowledge" style, the same approach real password
managers use):

- The master password is NEVER stored anywhere, in any form that could be
  reversed. Only a salted PBKDF2 hash of it is stored, used purely to verify
  a login attempt.
- A *separate* key, derived from the master password + a stored salt via
  PBKDF2-HMAC-SHA256, is used to encrypt/decrypt individual vault entries
  with Fernet (AES-128-CBC + HMAC, from the `cryptography` package). This
  key only ever exists in memory, for the duration of the unlocked session,
  and is discarded on lock/logout.
- Because of this, losing the master password means losing access to the
  vault permanently — there is no "reset" that preserves old entries. This
  is disclosed to the user during setup and in the README.
"""

import base64
import hashlib
import os
import secrets

from cryptography.fernet import Fernet, InvalidToken

PBKDF2_ITERATIONS = 390_000
SALT_BYTES = 16


def generate_salt() -> bytes:
    return os.urandom(SALT_BYTES)


def hash_master_password(password: str, salt: bytes) -> str:
    """Salted PBKDF2 hash used ONLY to verify login attempts."""
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return base64.b64encode(digest).decode("utf-8")


def verify_master_password(password: str, salt: bytes, stored_hash: str) -> bool:
    candidate = hash_master_password(password, salt)
    # Constant-time comparison to avoid timing side-channels.
    return secrets.compare_digest(candidate, stored_hash)


def derive_vault_key(password: str, salt: bytes) -> bytes:
    """Derive the Fernet encryption key used for vault entries. This key
    lives only in memory for the current unlocked session."""
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS, dklen=32
    )
    return base64.urlsafe_b64encode(digest)


def encrypt_value(vault_key: bytes, plaintext: str) -> str:
    f = Fernet(vault_key)
    token = f.encrypt(plaintext.encode("utf-8"))
    return token.decode("utf-8")


def decrypt_value(vault_key: bytes, ciphertext: str) -> str:
    f = Fernet(vault_key)
    try:
        return f.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("Could not decrypt this entry with the current session key.") from exc
