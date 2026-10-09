"""
Display formatters for Indian locale: currency, dates, weights, phone numbers.
All arithmetic uses Decimal to avoid float rounding errors.
"""
from __future__ import annotations

from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Optional, Union


def fmt_currency(amount: Optional[Union[Decimal, float, int, str]], symbol: str = "₹") -> str:
    if amount is None:
        return f"{symbol}0.00"
    try:
        d = Decimal(str(amount)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return f"{symbol}0.00"
    # Indian number system: X,XX,XXX.XX
    parts = str(abs(d)).split(".")
    integer_part = parts[0]
    decimal_part = parts[1] if len(parts) > 1 else "00"
    n = len(integer_part)
    if n <= 3:
        formatted = integer_part
    else:
        # Last 3 digits, then groups of 2
        last3 = integer_part[-3:]
        rest = integer_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        formatted = ",".join(groups) + "," + last3
    sign = "-" if d < 0 else ""
    return f"{sign}{symbol}{formatted}.{decimal_part}"


def fmt_weight(grams: Optional[Union[Decimal, float]], unit: str = "g") -> str:
    if grams is None:
        return "0.000 g"
    try:
        d = Decimal(str(grams)).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    except Exception:
        return "0.000 g"
    return f"{d} {unit}"


def fmt_date(d: Optional[Union[date, datetime, str]], fmt: str = "%d-%m-%Y") -> str:
    if d is None:
        return "-"
    if isinstance(d, str):
        return d
    if isinstance(d, datetime):
        return d.strftime(fmt)
    return d.strftime(fmt)


def fmt_datetime(dt: Optional[Union[datetime, str]]) -> str:
    if dt is None:
        return "-"
    if isinstance(dt, str):
        return dt
    return dt.strftime("%d-%m-%Y %H:%M")


def fmt_percentage(value: Optional[Union[Decimal, float]]) -> str:
    if value is None:
        return "0.00%"
    try:
        d = Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except Exception:
        return "0.00%"
    return f"{d}%"


def fmt_phone(phone: Optional[str]) -> str:
    if not phone:
        return "-"
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) == 10:
        return f"+91 {digits[:5]} {digits[5:]}"
    return phone


def parse_decimal(value: str) -> Optional[Decimal]:
    try:
        return Decimal(value.replace(",", "").strip())
    except Exception:
        return None


def days_overdue(maturity: date) -> int:
    today = date.today()
    if today > maturity:
        return (today - maturity).days
    return 0


INDIAN_STATES = [
    "Andhra Pradesh", "Arunachal Pradesh", "Assam", "Bihar", "Chhattisgarh",
    "Goa", "Gujarat", "Haryana", "Himachal Pradesh", "Jharkhand",
    "Karnataka", "Kerala", "Madhya Pradesh", "Maharashtra", "Manipur",
    "Meghalaya", "Mizoram", "Nagaland", "Odisha", "Punjab",
    "Rajasthan", "Sikkim", "Tamil Nadu", "Telangana", "Tripura",
    "Uttar Pradesh", "Uttarakhand", "West Bengal",
    "Andaman and Nicobar Islands", "Chandigarh", "Dadra & Nagar Haveli and Daman & Diu",
    "Delhi", "Jammu & Kashmir", "Ladakh", "Lakshadweep", "Puducherry",
]
