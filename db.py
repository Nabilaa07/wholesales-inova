"""Koneksi ke dua DBMS (MySQL + PostgreSQL) via SQLAlchemy.

Kredensial TIDAK di-hardcode. Urutan pembacaan:
  1. environment variable (termasuk dari file .env / ENV_FILE saat lokal)
  2. st.secrets (Streamlit Community Cloud)
"""
from __future__ import annotations

import os
from functools import lru_cache

import certifi
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, Engine

try:  # .env hanya dipakai saat dev lokal
    from dotenv import load_dotenv

    load_dotenv(os.getenv("ENV_FILE") or None)  # ENV_FILE=.env.cloud untuk target cloud
except ImportError:  # pragma: no cover
    pass


def _get(key: str, default: str | None = None) -> str | None:
    val = os.getenv(key)
    if val not in (None, ""):
        return val
    try:
        import streamlit as st

        if key in st.secrets:
            return str(st.secrets[key])
    except Exception:
        pass
    return default


def _truthy(value: str | None) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


@lru_cache(maxsize=1)
def get_mysql_engine() -> Engine:
    """DBMS 1 - MySQL (data transaksi)."""
    url = URL.create(
        "mysql+pymysql",
        username=_get("MYSQL_USER", "root"),
        password=_get("MYSQL_PASSWORD") or None,
        host=_get("MYSQL_HOST", "127.0.0.1"),
        port=int(_get("MYSQL_PORT", "3306")),
        database=_get("MYSQL_DATABASE", "innova_sales"),
        query={"charset": "utf8mb4"},
    )
    connect_args: dict = {}
    if _truthy(_get("MYSQL_SSL", "false")):
        connect_args = {
            "ssl": {"ca": certifi.where()},
            "ssl_verify_cert": True,
            "ssl_verify_identity": True,
        }
    return create_engine(url, pool_pre_ping=True, pool_recycle=300, connect_args=connect_args)


@lru_cache(maxsize=1)
def get_postgres_engine() -> Engine:
    """DBMS 2 - PostgreSQL (katalog & referensi)."""
    url = URL.create(
        "postgresql+psycopg2",
        username=_get("PG_USER") or None,  # None -> libpq memakai user OS (Postgres.app)
        password=_get("PG_PASSWORD") or None,
        host=_get("PG_HOST", "localhost"),
        port=int(_get("PG_PORT", "5432")),
        database=_get("PG_DATABASE", "innova_catalog"),
    )
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"sslmode": _get("PG_SSLMODE", "prefer")},
    )


def ping(engine: Engine) -> tuple[bool, str]:
    """Cek koneksi; kembalikan (ok, versi_server / pesan_error ringkas)."""
    try:
        with engine.connect() as conn:
            version = conn.execute(text("SELECT VERSION()")).scalar()
        return True, str(version)
    except Exception as exc:  # jangan bocorkan kredensial ke UI
        return False, type(exc).__name__
