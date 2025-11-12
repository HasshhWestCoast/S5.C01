# app/api/recommend.py
from fastapi import APIRouter, Body, HTTPException
from app.core.db import get_connection
import time

router = APIRouter(prefix="/user", tags=["Recommandations"])

# ==================== Réglages globaux (fixes) ====================
RECO_LIMIT = 6          # nb de séries renvoyées
RECO_TOP_TOKENS = 4      # nb de tokens conservés par série "aimée"
RECO_MIN_RATING = 3      # note min pour considérer une série "appréciée"
IDF_MIN, IDF_MAX = 1.0, 2.8  # fenêtre IDF pour éviter stop-words et noms propres


# ==================== Noter / mettre à jour une note ====================
@router.post("/rate")
def rate_series(
    user_id: str = Body(...),
    show_name: str = Body(...),
    rating: int   = Body(...),
):
    """Enregistre (ou met à jour) la note d'un utilisateur pour une série (1..5)."""
    if not (1 <= rating <= 5):
        raise HTTPException(400, "La note doit être comprise entre 1 et 5.")

    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO user_ratings (user_id, show_name, rating)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, show_name)
            DO UPDATE SET rating = EXCLUDED.rating;
            """,
            (user_id, show_name.lower(), rating),
        )
        conn.commit()

    return {"message": f"{show_name} = {rating}/5 pour {user_id}"}


# ==================== Lister les notes d'un utilisateur ====================
@router.get("/ratings/{user_id}")
def list_ratings(user_id: str):
    with get_connection() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT show_name, rating
            FROM user_ratings
            WHERE user_id = %s
            ORDER BY show_name;
            """,
            (user_id,),
        )
        return {"user_id": user_id, "ratings": cur.fetchall()}


# ==================== Recommandations automatiques ====================
@router.get("/recommend/{user_id}")
def recommend_series(user_id: str):
    """
    Recommande des séries à partir des meilleurs tokens (TF-IDF) des séries bien notées par l'utilisateur.
    Paramètres techniques fixés dans le code (voir constantes en haut).
    """
    t0 = time.perf_counter()

    # SQL "tout-en-un" : séries likées → top tokens par série → scoring des autres séries
    sql = """
    WITH liked AS (
      SELECT show_name, rating
      FROM user_ratings
      WHERE user_id = %s AND rating >= %s
    ),

    -- Meilleurs tokens par série aimée (TF-IDF = SUM(freq)*idf), filtrés (regex + IDF)
    per_fav AS (
      SELECT
        e.show_name,
        u.token,
        SUM(u.freq * t.idf) AS tfidf,
        ROW_NUMBER() OVER (
          PARTITION BY e.show_name
          ORDER BY SUM(u.freq * t.idf) DESC
        ) AS rk
      FROM episodes e
      JOIN unigram_counts u ON u.episode_id = e.id
      JOIN token_df t       ON t.token      = u.token
      WHERE e.show_name IN (SELECT show_name FROM liked)
        AND u.token ~ '^[a-z]{4,}$'
        AND t.idf BETWEEN %s AND %s
      GROUP BY e.show_name, u.token
    ),

    fav_tokens AS (
      SELECT DISTINCT token
      FROM per_fav
      WHERE rk <= %s                -- RECO_TOP_TOKENS par série
    ),

    -- Score pour chaque série candidate (somme TF-IDF sur les tokens retenus)
    cand AS (
      SELECT
        e.show_name,
        SUM(u.freq * t.idf) AS score
      FROM episodes e
      JOIN unigram_counts u ON u.episode_id = e.id
      JOIN token_df t       ON t.token      = u.token
      JOIN fav_tokens ft    ON ft.token     = u.token
      GROUP BY e.show_name
    )

    SELECT c.show_name, c.score
    FROM cand c
    WHERE c.show_name NOT IN (SELECT show_name FROM liked)
    ORDER BY c.score DESC
    LIMIT %s;
    """

    # Requêtes
    with get_connection() as conn, conn.cursor() as cur:
        # Résultats (séries recommandées)
        cur.execute(
            sql,
            (user_id, RECO_MIN_RATING, IDF_MIN, IDF_MAX, RECO_TOP_TOKENS, RECO_LIMIT),
        )
        rows = cur.fetchall()

        # Pour info, on renvoie aussi les séries likées utilisées
        cur.execute(
            """
            SELECT show_name, rating
            FROM user_ratings
            WHERE user_id = %s AND rating >= %s
            ORDER BY rating DESC, show_name;
            """,
            (user_id, RECO_MIN_RATING),
        )
        liked_series = cur.fetchall()

    elapsed = round((time.perf_counter() - t0) * 1000, 2)
    return {
        "user_id": user_id,
        "params": {
            "limit": RECO_LIMIT,
            "top_tokens_per_fav": RECO_TOP_TOKENS,
            "liked_min_rating": RECO_MIN_RATING,
            "idf_window": [IDF_MIN, IDF_MAX],
        },
        "liked_series": liked_series,
        "time_ms": elapsed,
        "results": rows,  # [{show_name, score}, ...]
    }
