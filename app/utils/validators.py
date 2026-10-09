"""Input validation helpers."""
from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Optional


def validate_mobile(mobile: str) -> bool:
    return bool(re.match(r"^[6-9]\d{9}$", mobile.strip()))


def validate_email(email: str) -> Optional[str]:
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    if re.match(pattern, email.strip()):
        return None
    return "Invalid email address"


def validate_pincode(pincode: str) -> bool:
    return bool(re.match(r"^\d{6}$", pincode.strip()))


def validate_pan(pan: str) -> bool:
    return bool(re.match(r"^[A-Z]{5}[0-9]{4}[A-Z]$", pan.strip().upper()))


def validate_aadhaar(aadhaar: str) -> bool:
    digits = re.sub(r"[\s\-]", "", aadhaar)
    return bool(re.match(r"^\d{12}$", digits))


def validate_positive_decimal(value: str) -> Optional[str]:
    try:
        d = Decimal(value.replace(",", "").strip())
        if d <= 0:
            return "Value must be greater than zero"
        return None
    except (InvalidOperation, Exception):
        return "Invalid number"


def validate_weight(value: str) -> Optional[str]:
    try:
        d = Decimal(value.replace(",", "").strip())
        if d <= 0:
            return "Weight must be greater than zero"
        if d > Decimal("9999.999"):
            return "Weight exceeds maximum allowed"
        return None
    except Exception:
        return "Invalid weight"


def validate_interest_rate(rate: str) -> Optional[str]:
    try:
        d = Decimal(rate.strip())
        if d < 0:
            return "Rate cannot be negative"
        if d > Decimal("100"):
            return "Rate cannot exceed 100%"
        return None
    except Exception:
        return "Invalid rate"


def validate_ltv(ltv: str, max_ltv: float = 90.0) -> Optional[str]:
    try:
        d = Decimal(ltv.strip())
        if d <= 0:
            return "LTV must be greater than zero"
        if d > Decimal(str(max_ltv)):
            return f"LTV cannot exceed {max_ltv}% per policy"
        return None
    except Exception:
        return "Invalid LTV percentage"


def validate_password(password: str) -> Optional[str]:
    if len(password) < 8:
        return "Password must be at least 8 characters"
    if not re.search(r"[A-Z]", password):
        return "Password must contain at least one uppercase letter"
    if not re.search(r"[a-z]", password):
        return "Password must contain at least one lowercase letter"
    if not re.search(r"\d", password):
        return "Password must contain at least one digit"
    return None


def validate_username(username: str) -> Optional[str]:
    if len(username) < 3:
        return "Username must be at least 3 characters"
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", username):
        return "Username may only contain letters, digits, _ - ."
    return None
