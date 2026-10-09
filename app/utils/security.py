"""
Security utilities: password hashing (Argon2), Fernet encryption,
session management, and input sanitisation.
"""
from __future__ import annotations

import base64
import hashlib
import logging
import os
import secrets
import string
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_ph = PasswordHasher(
    time_cost=2,
    memory_cost=65536,
    parallelism=2,
    hash_len=32,
    salt_len=16,
)

# Fernet key derived from a per-installation secret stored in AppData
_fernet: Optional[Fernet] = None


def _get_key_file_path() -> str:
    from app.config import _BASE_DIR
    return str(_BASE_DIR / ".enc_key")


def init_encryption(key_path: Optional[str] = None) -> None:
    global _fernet
    path = key_path or _get_key_file_path()
    if os.path.exists(path):
        with open(path, "rb") as f:
            key = f.read().strip()
    else:
        key = Fernet.generate_key()
        with open(path, "wb") as f:
            f.write(key)
        os.chmod(path, 0o600)
    _fernet = Fernet(key)


def _ensure_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        init_encryption()
    return _fernet  # type: ignore


# -------------------------------------------------------------------
# Password hashing
# -------------------------------------------------------------------

def hash_password(password: str) -> str:
    return _ph.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    try:
        return _ph.verify(hashed, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def needs_rehash(hashed: str) -> bool:
    return _ph.check_needs_rehash(hashed)


def generate_temp_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# -------------------------------------------------------------------
# Fernet encryption for sensitive fields (KYC refs, etc.)
# -------------------------------------------------------------------

def encrypt_field(plaintext: str) -> str:
    if not plaintext:
        return ""
    fernet = _ensure_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def decrypt_field(ciphertext: str) -> str:
    if not ciphertext:
        return ""
    fernet = _ensure_fernet()
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except (InvalidToken, Exception) as exc:
        logger.error("Decryption failed: %s", exc)
        return "[DECRYPTION ERROR]"


def mask_aadhaar(ref: str) -> str:
    """Return last 4 digits only for display."""
    if len(ref) >= 4:
        return "XXXX-XXXX-" + ref[-4:]
    return "****"


def mask_pan(ref: str) -> str:
    if len(ref) == 10:
        return ref[:2] + "XXXXX" + ref[-3:]
    return "**MASKED**"


# -------------------------------------------------------------------
# Session tokens
# -------------------------------------------------------------------

def generate_session_token() -> str:
    return secrets.token_hex(32)


def generate_receipt_id() -> str:
    return secrets.token_hex(8).upper()


# -------------------------------------------------------------------
# Input validation helpers
# -------------------------------------------------------------------

def sanitize_string(value: str, max_length: int = 255) -> str:
    if not isinstance(value, str):
        return ""
    return value.strip()[:max_length]
