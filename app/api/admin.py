# app/api/admin.py

from fastapi import APIRouter
from app.services.schema import init_schema
from app.services.indexer import index_srt
from scripts import bulk_index

router = APIRouter(prefix="/admin")

# Route pour initialiser la base (création des tables)
@router.post("/init-db")
def admin_init_db():
    init_schema()
    return {"status": "ok", "message": "schema created/verified"}

# Route pour indexer un épisode (insertion des données unigrams/bigrams)
@router.post("/index-srt")
def admin_index_srt(file: str, show: str, season: int, ep: int):
    result = index_srt(file, show, season, ep)
    return {"status": "ok", "indexed": result}


# Route pour réindexer toute la base (tous les sous-titres déjà présents)
@router.post("/reindex")
def admin_reindex():
    """
    Réindexe tous les sous-titres déjà importés dans la base.
    Utile après une mise à jour ou correction des noms de séries.
    """
    count = bulk_index.run_all()
    return {"status": "ok", "episodes_indexed": count}
