# app/api/debug_index.py
from fastapi import APIRouter, HTTPException
from app.core.db import get_connection
from pathlib import Path


router = APIRouter(prefix="/debug", tags=["Debug Index"])

@router.get("/unigrams")
def get_unigrams(episode_id: int, top: int = 20):
    """
    Retourne les top `n` unigrams pour un épisode donné.
    Exemple : /debug/unigrams?episode_id=1&top=20
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT token, freq
                FROM unigram_counts
                WHERE episode_id = %s
                ORDER BY freq DESC
                LIMIT %s;
            """, (episode_id, top))
            rows = cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucun unigram trouvé pour cet épisode")
    return {"episode_id": episode_id, "unigrams": [{"token": t, "freq": f} for t, f in rows]}


@router.get("/bigrams")
def get_bigrams(episode_id: int, top: int = 20):
    """
    Retourne les top `n` bigrammes pour un épisode donné.
    Exemple : /debug/bigrams?episode_id=1&top=20
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT token1, token2, freq
                FROM bigram_counts
                WHERE episode_id = %s
                ORDER BY freq DESC
                LIMIT %s;
            """, (episode_id, top))
            rows = cur.fetchall()
    if not rows:
        raise HTTPException(status_code=404, detail="Aucun bigram trouvé pour cet épisode")
    return {
        "episode_id": episode_id,
        "bigrams": [{"tokens": f"{t1} {t2}", "freq": f} for t1, t2, f in rows],
    }

@router.get("/posters-check")
def posters_check():
    """
    Vérifie les posters disponibles vs les séries présentes en base.
    Retourne la liste des séries pour lesquelles aucune image PNG
    n'a été trouvée dans static/posters.
    """
    # 1. Récupérer la liste des séries présentes dans la base
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT DISTINCT show_name FROM episodes ORDER BY show_name;")
            rows = cur.fetchall()

    # rows = liste de dicts, ex: {"show_name": "lost"}
    shows = [r["show_name"] for r in rows]

    # 2. Récupérer les fichiers présents dans static/posters
    base_dir = Path(__file__).resolve().parents[2]
    posters_dir = base_dir / "static" / "posters"

    existing = {png.stem.lower() for png in posters_dir.glob("*.png")}

    def normalize_name(name: str) -> str:
        return name.lower().replace(" ", "")

    missing = [
        show for show in shows
        if normalize_name(show) not in existing
    ]

    return {
        "total_shows": len(shows),
        "total_posters": len(existing),
        "missing_count": len(missing),
        "missing": missing,
    }
