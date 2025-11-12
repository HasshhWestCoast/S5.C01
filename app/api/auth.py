# app/api/auth.py
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from passlib.hash import bcrypt
from app.core.db import get_connection

router = APIRouter(prefix="/auth", tags=["Auth"])

class Credentials(BaseModel):
    login: str
    password: str

@router.post("/signup")
def signup(body: Credentials):
    login = body.login.strip()
    password = body.password

    if not login or not password:
        raise HTTPException(status_code=400, detail="login and password are required")

    password_hash = bcrypt.hash(password)

    with get_connection() as conn, conn.cursor() as cur:
        # Vérifie si le login existe déjà
        cur.execute("SELECT 1 FROM users WHERE login=%s;", (login,))
        if cur.fetchone():
            raise HTTPException(status_code=409, detail="login already exists")

        # Insère l'utilisateur
        cur.execute(
            """
            INSERT INTO users (login, password_hash)
            VALUES (%s, %s);
            """,
            (login, password_hash),
        )
        conn.commit()

    return {"status": "ok", "login": login}

@router.post("/login")
def login(body: Credentials):
    login = body.login.strip()
    password = body.password

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT password_hash FROM users WHERE login=%s;", (login,))
        row = cur.fetchone()

    if not row:
        # login inconnu
        raise HTTPException(status_code=401, detail="invalid credentials")

    # row peut être un dict (RealDictCursor) ou un tuple (curseur par défaut)
    if isinstance(row, dict):
        password_hash = row.get("password_hash")
    else:
        password_hash = row[0] if row and len(row) > 0 else None

    if not password_hash or not bcrypt.verify(password, password_hash):
        raise HTTPException(status_code=401, detail="invalid credentials")

    return {"status": "ok", "login": login}

# -- MINI "qui suis-je ?" (temporaire, sans token) --
@router.get("/me")
def me(login: str):
    # Vérifie que le login existe en base
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM users WHERE login = %s;", (login,))
        if not cur.fetchone():
            raise HTTPException(status_code=404, detail="unknown user")
    return {"login": login}
