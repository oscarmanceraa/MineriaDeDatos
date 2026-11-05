"""Conexion compartida a Supabase para las consultas de la Etapa 05."""

import os
from contextlib import contextmanager
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

BASE = Path(__file__).resolve().parents[2]
load_dotenv(BASE / ".env")


def _conectar():
    url = os.environ.get("SUPABASE_DB_URL")
    if not url:
        raise RuntimeError("Falta SUPABASE_DB_URL en el entorno.")
    return psycopg2.connect(url, connect_timeout=20)


@contextmanager
def conexion():
    conn = _conectar()
    try:
        yield conn
    finally:
        conn.close()


def fetch(conn, sql, params=None):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(sql, params or [])
        return cur.fetchall()
