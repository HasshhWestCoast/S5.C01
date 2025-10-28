# app/core/config.py
from dotenv import load_dotenv
import os

load_dotenv()  # charge le .env à la racine du projet

PG_USER = os.getenv("POSTGRES_USER", "sae")
PG_PASSWORD = os.getenv("POSTGRES_PASSWORD", "sae")
PG_DB = os.getenv("POSTGRES_DB", "sae_db")
PG_HOST = os.getenv("POSTGRES_HOST", "localhost")
PG_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
