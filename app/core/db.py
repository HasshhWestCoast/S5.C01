# app/core/db.py
import psycopg2
from psycopg2.extras import RealDictCursor
from .config import PG_USER, PG_PASSWORD, PG_DB, PG_HOST, PG_PORT

def get_connection():
    return psycopg2.connect(
        dbname=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD,
        host=PG_HOST,
        port=PG_PORT,
        cursor_factory=RealDictCursor,
    )

def check_db() -> bool:
    try:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1;")
                cur.fetchone()
        return True
    except Exception:
        return False
