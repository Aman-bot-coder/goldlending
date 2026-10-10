"""
Local SQLite database manager.
The database file lives in the user's AppData folder and is created
automatically on first launch — no server or internet required.
"""
from __future__ import annotations

import logging
import shutil
import sqlite3
import threading
import warnings
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Generator, Optional

from sqlalchemy import create_engine, event, exc as sa_exc, text
from sqlalchemy.orm import Session, sessionmaker, scoped_session

from app.database.base import Base

logger = logging.getLogger(__name__)

# SQLite stores NUMERIC as text/real; SQLAlchemy converts back to Decimal for us.
warnings.filterwarnings("ignore", category=sa_exc.SAWarning, message=".*Decimal objects natively.*")

_lock = threading.Lock()
_engine = None
_SessionFactory: Optional[scoped_session] = None

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "Admin@1234"
AUTO_BACKUP_KEEP = 10


def get_db_path() -> Path:
    from app.config import DB_DIR
    return DB_DIR / "gold_loan.db"


def _set_sqlite_pragmas(dbapi_conn, _record):
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.execute("PRAGMA journal_mode=WAL")
    cur.execute("PRAGMA synchronous=NORMAL")
    cur.execute("PRAGMA busy_timeout=10000")
    cur.close()


def init_db(db_path: Optional[Path] = None) -> None:
    """Open (or create) the local database, create tables and seed defaults."""
    global _engine, _SessionFactory

    with _lock:
        path = Path(db_path) if db_path else get_db_path()
        path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(
            f"sqlite:///{path.as_posix()}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        event.listen(engine, "connect", _set_sqlite_pragmas)

        from app.models import _register_all  # noqa: F401
        Base.metadata.create_all(engine)

        _engine = engine
        _SessionFactory = scoped_session(sessionmaker(bind=engine, autoflush=False))
        logger.info("Local database ready: %s", path)

    _seed_defaults()


def _seed_defaults() -> None:
    from app.models.user import User
    from app.models.app_settings import AppSetting
    from app.utils.security import hash_password

    with get_session() as session:
        if session.query(User).count() == 0:
            session.add(User(
                username=DEFAULT_ADMIN_USERNAME,
                email="admin@goldloan.local",
                full_name="System Administrator",
                password_hash=hash_password(DEFAULT_ADMIN_PASSWORD),
                role="admin",
                is_active=True,
                must_change_password=True,
            ))
            logger.info("Default admin account created")

        if session.query(AppSetting).count() == 0:
            session.add(AppSetting(
                setting_key="schema_version",
                setting_value="1",
                description="Local SQLite schema version",
            ))


def get_engine():
    if _engine is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _engine


def get_session_factory() -> scoped_session:
    if _SessionFactory is None:
        raise RuntimeError("Database not initialised. Call init_db() first.")
    return _SessionFactory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    factory = get_session_factory()
    session: Session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        factory.remove()


def close_db() -> None:
    global _engine, _SessionFactory
    with _lock:
        if _SessionFactory:
            _SessionFactory.remove()
            _SessionFactory = None
        if _engine:
            _engine.dispose()
            _engine = None


def health_check() -> bool:
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        return False


# ------------------------------------------------------------------ backups

def backup_to(dest: Path) -> Path:
    """Write a consistent copy of the live database to `dest`."""
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        dest.unlink()
    src = sqlite3.connect(str(get_db_path()))
    try:
        out = sqlite3.connect(str(dest))
        try:
            src.backup(out)
        finally:
            out.close()
    finally:
        src.close()
    return dest


def validate_backup_file(path: Path) -> Optional[str]:
    """Returns an error message, or None if the file is a usable backup."""
    try:
        conn = sqlite3.connect(f"file:{Path(path).as_posix()}?mode=ro", uri=True)
        try:
            names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return "Selected file is not a valid backup database."
    required = {"users", "customers", "loans", "repayments", "collateral_items"}
    missing = required - names
    if missing:
        return f"Backup is missing tables: {', '.join(sorted(missing))}"
    return None


def restore_from(src: Path) -> None:
    """Replace the live database with the contents of `src`, then reopen it."""
    err = validate_backup_file(src)
    if err:
        raise ValueError(err)

    live = get_db_path()
    safety = live.with_name(f"before_restore_{datetime.now():%Y%m%d_%H%M%S}.db")
    backup_to(safety)

    close_db()
    for suffix in ("-wal", "-shm"):
        side = live.with_name(live.name + suffix)
        if side.exists():
            side.unlink()

    src_conn = sqlite3.connect(str(src))
    try:
        dst_conn = sqlite3.connect(str(live))
        try:
            src_conn.backup(dst_conn)
        finally:
            dst_conn.close()
    finally:
        src_conn.close()

    init_db()


def auto_backup_if_due(max_age_hours: int = 24) -> Optional[Path]:
    """Daily automatic backup into the AppData backups folder, keeping the newest few."""
    from app.config import BACKUP_DIR
    if not get_db_path().exists():
        return None
    existing = sorted(BACKUP_DIR.glob("auto_*.db"), key=lambda p: p.stat().st_mtime)
    if existing:
        age_h = (datetime.now().timestamp() - existing[-1].stat().st_mtime) / 3600
        if age_h < max_age_hours:
            return None
    dest = backup_to(BACKUP_DIR / f"auto_{datetime.now():%Y%m%d_%H%M%S}.db")
    existing.append(dest)
    for old in existing[:-AUTO_BACKUP_KEEP]:
        try:
            old.unlink()
        except OSError:
            pass
    logger.info("Automatic backup written: %s", dest)
    return dest
