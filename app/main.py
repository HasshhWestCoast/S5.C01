# app/main.py
from fastapi import FastAPI
from .core.db import check_db

app = FastAPI()

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db/health")
def db_health():
    return {"db": "ok" if check_db() else "down"}
