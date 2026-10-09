"""Activation key encoding/decoding for client onboarding."""
from __future__ import annotations

import base64
import json


def decode_activation_key(key: str) -> dict:
    """
    Decode an activation key into DB connection credentials.
    Returns dict with: db_host, db_port, db_user, db_password, db_name
    Raises ValueError if key is invalid.
    """
    try:
        padded = key.strip()
        padding = 4 - len(padded) % 4
        if padding != 4:
            padded += "=" * padding
        decoded = base64.b64decode(padded.encode()).decode()
        data = json.loads(decoded)
        required = {"db_host", "db_port", "db_user", "db_password", "db_name"}
        if not required.issubset(data.keys()):
            raise ValueError("missing fields")
        return data
    except Exception:
        raise ValueError("Invalid activation key. Please check and try again.")


def generate_activation_key(
    db_host: str,
    db_user: str,
    db_password: str,
    db_name: str = "gold_loan_db",
    db_port: int = 3306,
) -> str:
    """Admin utility: generate an activation key for a client."""
    payload = json.dumps({
        "db_host": db_host,
        "db_port": db_port,
        "db_user": db_user,
        "db_password": db_password,
        "db_name": db_name,
    }, separators=(",", ":"))
    return base64.b64encode(payload.encode()).decode().rstrip("=")
