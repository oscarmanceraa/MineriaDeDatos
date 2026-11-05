"""Consultas sobre el modelo estrella SQLite cargado por la aplicación."""

from contextlib import contextmanager

from app.modelo_estrella import obtener_modelo


@contextmanager
def conexion():
    yield obtener_modelo()["connection"]


def fetch(conn, sql, params=None):
    cursor = conn.execute(sql.replace("%s", "?"), params or [])
    return [dict(row) for row in cursor.fetchall()]
