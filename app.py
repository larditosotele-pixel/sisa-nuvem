import os
import psycopg2
from psycopg2.extras import RealDictCursor
from flask import Flask, render_template, request, redirect, url_for
from datetime import datetime
import pytz

app = Flask(__name__)

def get_db_connection():
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        # Render usa postgres:// mas psycopg2 precisa de postgresql://
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql://", 1)
        # Força SSL que o Render exige
        conn = psycopg2.connect(database_url, sslmode="require", cursor_factory=RealDictCursor)
        return conn
    else:
        import sqlite3
        conn = sqlite3.connect('banco.db')
        conn.row_factory = sqlite3.Row
        return conn
