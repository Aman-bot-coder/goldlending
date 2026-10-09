"""
Database connection manager.
Supports local MySQL and remote MySQL over SSH tunnel.
"""
from __future__ import annotations

import logging
import threading
from contextlib import contextmanager
from typing import Generator, Optional

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker, scoped_session
from sqlalchemy.pool import QueuePool

from app.config import get_config
from app.database.base import Base

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_tunnel = None
_engine = None
_SessionFactory: Optional[scoped_session] = None


def _build_engine(host: str, port: int):
    config = get_config()
    url = (
        f"mysql+pymysql://{config.db_user}:{config.db_password}"
        f"@{host}:{port}/{config.db_name}"
        "?charset=utf8mb4"
    )
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        echo=config.debug_sql,
        connect_args={"connect_timeout": 30},
    )


def init_db(ssh_password: str = "", ssh_key_path: str = "") -> None:
    global _tunnel, _engine, _SessionFactory

    with _lock:
        config = get_config()

        if config.use_ssh_tunnel:
            try:
                from sshtunnel import SSHTunnelForwarder
                import paramiko

                ssh_kwargs: dict = {
                    "ssh_username": config.ssh_username,
                    "remote_bind_address": ("127.0.0.1", 3306),
                }

                key_path = ssh_key_path or config.ssh_key_path
                password = ssh_password or config.ssh_password

                if key_path and key_path.strip():
                    ssh_kwargs["ssh_pkey"] = paramiko.RSAKey.from_private_key_file(key_path)
                elif password:
                    ssh_kwargs["ssh_password"] = password
                else:
                    raise ValueError(
                        "SSH authentication required: provide ssh_password or ssh_key_path in Settings."
                    )

                _tunnel = SSHTunnelForwarder(
                    (config.ssh_host, config.ssh_port),
                    **ssh_kwargs,
                )
                _tunnel.start()
                logger.info(
                    "SSH tunnel open → local port %s", _tunnel.local_bind_port
                )
                host = "127.0.0.1"
                port = _tunnel.local_bind_port
            except Exception as exc:
                logger.error("SSH tunnel failed: %s", exc)
                raise
        else:
            host = config.db_host
            port = config.db_port

        _engine = _build_engine(host, port)

        from app.models import _register_all  # noqa: F401

        _SessionFactory = scoped_session(sessionmaker(bind=_engine, autoflush=False))
        logger.info("Database initialised (%s:%s/%s)", host, port, config.db_name)


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
    global _tunnel, _engine, _SessionFactory
    with _lock:
        if _SessionFactory:
            _SessionFactory.remove()
            _SessionFactory = None
        if _engine:
            _engine.dispose()
            _engine = None
        if _tunnel:
            _tunnel.stop()
            _tunnel = None
            logger.info("SSH tunnel closed")


def health_check() -> bool:
    try:
        with get_session() as session:
            session.execute(text("SELECT 1"))
        return True
    except Exception as exc:
        logger.error("DB health check failed: %s", exc)
        return False
