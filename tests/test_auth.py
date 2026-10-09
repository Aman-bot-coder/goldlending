"""Unit tests for authentication service."""
import pytest
from app.utils.security import hash_password, verify_password, encrypt_field, decrypt_field, init_encryption


def test_password_hash_and_verify():
    pw = "TestPassword@123"
    h = hash_password(pw)
    assert verify_password(pw, h) is True
    assert verify_password("WrongPassword", h) is False


def test_password_hash_is_not_plaintext():
    pw = "TestPassword@123"
    h = hash_password(pw)
    assert pw not in h


def test_encrypt_decrypt():
    import tempfile, os
    with tempfile.NamedTemporaryFile(delete=False, suffix=".key") as f:
        key_path = f.name
    try:
        # Remove the empty temp file so init_encryption generates a fresh key
        import os as _os
        _os.unlink(key_path)
        init_encryption(key_path)
        plain = "1234 5678 9012 3456"
        cipher = encrypt_field(plain)
        assert cipher != plain
        recovered = decrypt_field(cipher)
        assert recovered == plain
    finally:
        os.unlink(key_path)


def test_encrypt_empty():
    init_encryption()
    assert encrypt_field("") == ""
    assert decrypt_field("") == ""
