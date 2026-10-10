"""
Application configuration management.
Reads from environment variables / config file stored in user AppData.
Never bundle secrets in the executable.
"""
from __future__ import annotations

import os
import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

APP_NAME = "GoldSilverLoan"
APP_VERSION = "1.0.0"
APP_DISPLAY_NAME = "Gold & Silver Loan Management System"

# AppData directory for config/data
if os.name == "nt":  # Windows
    _BASE_DIR = Path(os.environ.get("APPDATA", Path.home())) / APP_NAME
else:  # dev on macOS/Linux
    _BASE_DIR = Path.home() / f".{APP_NAME.lower()}"

CONFIG_FILE = _BASE_DIR / "config.json"
DB_DIR = _BASE_DIR / "database"
BACKUP_DIR = _BASE_DIR / "backups"
UPLOAD_DIR = _BASE_DIR / "uploads"
LOG_DIR = _BASE_DIR / "logs"

# Create required directories
for _d in [_BASE_DIR, DB_DIR, BACKUP_DIR, UPLOAD_DIR, LOG_DIR]:
    _d.mkdir(parents=True, exist_ok=True)

_DEFAULT_CONFIG: dict = {
    # Application
    "debug_sql": False,
    "session_timeout_minutes": 30,
    "auto_backup_enabled": True,
    "auto_backup_interval_hours": 24,
    # Business
    "business_name": "Gold & Silver Loan Services",
    "business_address": "",
    "business_phone": "",
    "business_email": "",
    "business_gstin": "",
    "receipt_prefix": "RCPT",
    "loan_prefix": "LN",
    "customer_prefix": "CUST",
    # Rate API
    "rate_api_provider": "goldapi",
    "rate_api_key": "",
    "rate_refresh_interval_minutes": 30,
    # Loan defaults
    "default_interest_rate": 2.0,
    "default_ltv_percentage": 75.0,
    "default_tenure_days": 180,
    "max_ltv_percentage": 90.0,
    "overdue_penalty_rate": 3.0,
    "currency": "INR",
    "currency_symbol": "₹",
    "theme": "light",
}


class AppConfig:
    def __init__(self) -> None:
        self._data: dict = {}
        self.load()

    def load(self) -> None:
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                self._data = {**_DEFAULT_CONFIG, **stored}
            except Exception as exc:
                logger.warning("Config read error: %s — using defaults", exc)
                self._data = dict(_DEFAULT_CONFIG)
        else:
            self._data = dict(_DEFAULT_CONFIG)
            self.save()

    def save(self) -> None:
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, indent=2)
        except Exception as exc:
            logger.error("Config save error: %s", exc)

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value) -> None:
        self._data[key] = value
        self.save()

    def update(self, updates: dict) -> None:
        self._data.update(updates)
        self.save()

    # --- Convenience properties ---
    @property
    def debug_sql(self) -> bool:
        return bool(self._data.get("debug_sql", False))

    @property
    def session_timeout_minutes(self) -> int:
        return int(self._data.get("session_timeout_minutes", 30))

    @property
    def business_name(self) -> str:
        return self._data.get("business_name", APP_DISPLAY_NAME)

    @property
    def receipt_prefix(self) -> str:
        return self._data.get("receipt_prefix", "RCPT")

    @property
    def loan_prefix(self) -> str:
        return self._data.get("loan_prefix", "LN")

    @property
    def customer_prefix(self) -> str:
        return self._data.get("customer_prefix", "CUST")

    @property
    def default_interest_rate(self) -> float:
        return float(self._data.get("default_interest_rate", 2.0))

    @property
    def default_ltv_percentage(self) -> float:
        return float(self._data.get("default_ltv_percentage", 75.0))

    @property
    def max_ltv_percentage(self) -> float:
        return float(self._data.get("max_ltv_percentage", 90.0))

    @property
    def default_tenure_days(self) -> int:
        return int(self._data.get("default_tenure_days", 180))

    @property
    def overdue_penalty_rate(self) -> float:
        return float(self._data.get("overdue_penalty_rate", 3.0))

    @property
    def currency_symbol(self) -> str:
        return self._data.get("currency_symbol", "₹")

    @property
    def rate_api_provider(self) -> str:
        return self._data.get("rate_api_provider", "goldapi")

    @property
    def rate_api_key(self) -> str:
        return self._data.get("rate_api_key", "")

    @property
    def rate_refresh_interval_minutes(self) -> int:
        return int(self._data.get("rate_refresh_interval_minutes", 30))

    @property
    def theme(self) -> str:
        return self._data.get("theme", "light")

    @property
    def upload_dir(self) -> Path:
        return UPLOAD_DIR

    @property
    def backup_dir(self) -> Path:
        return BACKUP_DIR

    @property
    def log_dir(self) -> Path:
        return LOG_DIR


_config_instance: Optional[AppConfig] = None


def get_config() -> AppConfig:
    global _config_instance
    if _config_instance is None:
        _config_instance = AppConfig()
    return _config_instance
