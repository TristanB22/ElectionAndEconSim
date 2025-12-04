#!/usr/bin/env python3
from __future__ import annotations

from typing import Optional, Any, List, Dict
from contextlib import contextmanager
from fastapi import Header, HTTPException, status
import mysql.connector  # type: ignore
try:
	import psycopg2  # type: ignore
	import psycopg2.extras  # type: ignore
	PSYCOPG2_AVAILABLE = True
except ImportError:
	PSYCOPG2_AVAILABLE = False
	psycopg2 = None

from .config import settings


def require_api_key(x_api_key: Optional[str] = Header(None)) -> None:
    """Optional API key check. If API key is set in settings, require it.

    Raises 401 if missing/invalid.
    """
    if settings.API_KEY:
        if not x_api_key or x_api_key != settings.API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key")


def get_client_session(x_client_session: Optional[str] = Header(None)) -> str:
    return x_client_session or "default"


@contextmanager
def mysql_connection():
    conn = mysql.connector.connect(
        host=settings.MYSQL_HOST,
        port=settings.MYSQL_PORT,
        user=settings.MYSQL_USER,
        password=settings.MYSQL_PASSWORD,
        database=settings.MYSQL_DATABASE,
    )
    try:
        yield conn
    finally:
        conn.close()


@contextmanager
def postgis_connection():
    conn = psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
    )
    try:
        yield conn
    finally:
        conn.close()


