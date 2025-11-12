# app/main.py
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles                      # <-- NEW
from starlette.middleware.sessions import SessionMiddleware      # <-- NEW
from pathlib import Path

from .core.db import check_db
from .services.subtitles import srt_to_lines
from .services.normalize import normalize_line, token_counts_from_file
from .services.schema import init_schema
from .services.indexer import index_srt

from app.api import admin, debug_index
from app.api import search
from app.api import recommend
from app.api import auth

from app.web import router as web_router                         # <-- NEW (router HTML)

app = FastAPI(title="Series Reco")

# === Sessions (cookie signé) pour savoir qui est connecté ===
# (la clé peut être n'importe quelle chaîne secrète en développement)
app.add_middleware(SessionMiddleware, secret_key="CHANGE-ME")    # <-- NEW

# === Fichiers statiques (CSS du mini-front) ===
app.mount("/static", StaticFiles(directory="static"), name="static")  # <-- NEW

# === Routers API existants ===
app.include_router(admin.router)
app.include_router(debug_index.router)
app.include_router(search.router)
app.include_router(recommend.router)
app.include_router(auth.router)

# === Router web (pages HTML) ===
app.include_router(web_router)                                   # <-- NEW

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/db/health")
def db_health():
    return {"db": "ok" if check_db() else "down"}

@app.get("/debug/preview-srt")
def preview_srt(file: str = Query(..., description="Chemin d'un fichier .srt sous data/")):
    p = Path(file)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable: {file}")
    lines = srt_to_lines(str(p))
    return {"file": str(p), "total_lines": len(lines), "sample": lines[:10]}

@app.get("/debug/clean-srt")
def clean_srt(file: str = Query(..., description="Chemin d'un .srt (ex: data/xxx.srt)")):
    p = Path(file)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable: {file}")
    lines = srt_to_lines(str(p))
    cleaned = [normalize_line(l) for l in lines[:10]]
    return {
        "file": str(p),
        "original_sample": lines[:10],
        "cleaned_sample": cleaned,
    }

@app.get("/debug/token-stats")
def token_stats(
    file: str = Query(..., description="Chemin .srt (ex: data/xxx.srt)"),
    top: int = Query(20, ge=5, le=200, description="Combien de mots fréquents renvoyer")
):
    p = Path(file)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable: {file}")
    stats = token_counts_from_file(str(p), top_k=top)
    return {
        "file": str(p),
        **stats
    }

@app.post("/admin/init-db")
def admin_init_db():
    init_schema()
    return {"status": "ok", "message": "schema created/verified"}

@app.post("/admin/index-srt")
def admin_index_srt(
    file: str = Query(..., description="Chemin .srt ex: data/xxx.srt"),
    show: str | None = Query(None),
    season: int | None = Query(None),
    ep: int | None = Query(None),
):
    p = Path(file)
    if not p.exists():
        raise HTTPException(status_code=404, detail=f"Fichier introuvable: {file}")
    result = index_srt(str(p), show_name=show, season=season, episode=ep)
    return {"status": "ok", "indexed": result}
