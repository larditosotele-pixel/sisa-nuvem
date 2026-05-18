import os
import psycopg2
from psycopg2.extras import RealDictCursor

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Corrige a URL do Postgres pra versão nova do psycopg2
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        conn = psycopg2.connect(database_url, cursor_factory=RealDictCursor)
        return conn
    else:
        # Fallback pro SQLite local se não tiver DATABASE_URL
        import sqlite3
        conn = sqlite3.connect('banco.db')
        conn.row_factory = sqlite3.Row
        return conn
