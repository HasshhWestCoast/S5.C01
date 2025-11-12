import time
from fastapi import APIRouter, Query
from app.core.db import get_connection
from app.services.normalize import normalize_line

router = APIRouter(prefix="/search", tags=["Search"])

CANDIDATE_POOL = 100  # on récupère plus d'épisodes pour un meilleur rerank par série
LIMIT = 5            # limite finale affichée

# ---------- Requêtes SQL de base (AND et OR) ----------

def _query_and(cur, tokens, limit):
    placeholders = ",".join(["%s"] * len(tokens))
    sql = f"""
    WITH q(tok) AS (SELECT UNNEST(ARRAY[{placeholders}]))
    SELECT
        e.id, e.show_name, e.season, e.episode, e.file_path,
        COUNT(DISTINCT u.token) AS matched_terms,
        SUM(u.freq * COALESCE(t.idf, 0.0)) AS tfidf
    FROM unigram_counts u
    JOIN q            ON q.tok = u.token
    LEFT JOIN token_df t ON t.token = u.token
    JOIN episodes e   ON e.id = u.episode_id
    GROUP BY e.id, e.show_name, e.season, e.episode, e.file_path
    HAVING COUNT(DISTINCT u.token) = (SELECT COUNT(*) FROM q)  -- AND strict
    ORDER BY tfidf DESC
    LIMIT {limit};
    """
    cur.execute(sql, tokens)
    rows = cur.fetchall()
    for r in rows:
        r["score"] = float(r["tfidf"])
        r["match_type"] = "AND"
    return rows

def _query_or(cur, tokens, limit):
    placeholders = ",".join(["%s"] * len(tokens))
    sql = f"""
    WITH q(tok) AS (SELECT UNNEST(ARRAY[{placeholders}]))
    SELECT
        e.id, e.show_name, e.season, e.episode, e.file_path,
        COUNT(DISTINCT u.token) AS matched_terms,
        SUM(u.freq * COALESCE(t.idf, 0.0)) AS tfidf
    FROM unigram_counts u
    JOIN q            ON q.tok = u.token
    LEFT JOIN token_df t ON t.token = u.token
    JOIN episodes e   ON e.id = u.episode_id
    GROUP BY e.id, e.show_name, e.season, e.episode, e.file_path
    HAVING COUNT(DISTINCT u.token) >= 1                        -- OR large
    ORDER BY matched_terms DESC, tfidf DESC
    LIMIT {limit};
    """
    cur.execute(sql, tokens)
    rows = cur.fetchall()
    for r in rows:
        r["score"] = float(r["tfidf"])
        r["match_type"] = "OR"
    return rows

# ---------- Route principale : un seul paramètre q ----------

@router.get("")
def search(q: str = Query(..., description="Mots-clés ou courte phrase")):
    """
    Mode fixe : AND prioritaire + fallback OR + boost bigrammes.
    Dédup par série (max 1 épisode par show) + Rerank par série (Top-3 séries promues).
    Variantes singulier/pluriel auto si la requête contient un seul mot.
    """
    start = time.perf_counter()

    tokens = normalize_line(q)
    if not tokens:
        elapsed = (time.perf_counter() - start) * 1000.0
        return {"query": q, "tokens": [], "time_ms": round(elapsed, 2), "results": []}

    # Variantes singulier/pluriel auto si UN seul mot (ex: vampire <-> vampires)
    use_variant_or = False
    if len(tokens) == 1:
        t = tokens[0]
        variants = {t}
        if t.endswith("s"):
            if len(t) > 1:
                variants.add(t[:-1])
        else:
            variants.add(t + "s")
        tokens = list(variants)
        use_variant_or = True

    # Bigrammes pour boost de "phrase exacte"
    bigrams = [(tokens[i], tokens[i + 1]) for i in range(len(tokens) - 1)]

    # ----- Récupération des candidats (AND prioritaire puis OR) -----
    with get_connection() as conn, conn.cursor() as cur:
        if use_variant_or:
            rows_and = []
            rows_or = _query_or(cur, tokens, CANDIDATE_POOL)
        else:
            rows_and = _query_and(cur, tokens, CANDIDATE_POOL)
            remaining = max(0, CANDIDATE_POOL - len(rows_and))
            rows_or = _query_or(cur, tokens, remaining) if remaining else []

    # Fusion sans doublons d'épisodes (AND avant OR)
    seen_ep = {r["id"] for r in rows_and}
    rows = rows_and + [r for r in rows_or if r["id"] not in seen_ep]

    # ----- Boost de phrase exacte via bigram_counts -----
    if bigrams and rows:
        ep_ids = [r["id"] for r in rows]
        placeholders_ep = ",".join(["%s"] * len(ep_ids))
        placeholders_bg = ",".join(["(%s,%s)"] * len(bigrams))
        bg_params = []
        for t1, t2 in bigrams:
            bg_params += [t1, t2]

        boost_sql = f"""
        SELECT episode_id, SUM(freq) AS bgfreq
        FROM bigram_counts
        WHERE episode_id IN ({placeholders_ep})
          AND (token1, token2) IN ({placeholders_bg})
        GROUP BY episode_id;
        """
        with get_connection() as conn, conn.cursor() as cur:
            cur.execute(boost_sql, ep_ids + bg_params)
            boosts = {r["episode_id"]: r["bgfreq"] for r in cur.fetchall()}
        for r in rows:
            r["score"] = float(r["score"]) + 2.0 * float(boosts.get(r["id"], 0))

    # ----- Tri primaire (AND d'abord, puis score décroissant) -----
    rows.sort(key=lambda x: (0 if x["match_type"] == "AND" else 1, -x["score"]))

    # ----- Rerank par série : promouvoir les Top-3 séries -----
    # 1) score par série = somme des scores + petit bonus sur matched_terms max
    series_score = {}
    best_ep_per_show = {}
    for r in rows:
        show = r["show_name"]
        series_score.setdefault(show, 0.0)
        series_score[show] += float(r["score"])
        # garder le meilleur épisode par série
        if show not in best_ep_per_show or r["score"] > best_ep_per_show[show]["score"]:
            best_ep_per_show[show] = r
        # bonus léger à la "couverture" (approx: matched_terms max)
        series_score[show] += 0.1 * int(r.get("matched_terms", 0))

    # 2) top-3 séries
    top_series = sorted(series_score.items(), key=lambda kv: kv[1], reverse=True)[:3]
    top3_shows = [name for name, _ in top_series]
    top3_episodes = [best_ep_per_show[s] for s in top3_shows if s in best_ep_per_show]

    # ----- Diversité : max 1 épisode par série + priorité aux Top-3 -----
    diverse = []
    seen_shows = set()

    # place d'abord les meilleurs épisodes des 3 meilleures séries
    for r in top3_episodes:
        if r["show_name"] not in seen_shows:
            diverse.append(r)
            seen_shows.add(r["show_name"])
            if len(diverse) >= LIMIT:
                break

    # puis complète avec le reste, en respectant "1 épisode par série"
    if len(diverse) < LIMIT:
        for r in rows:
            if r["show_name"] in seen_shows:
                continue
            diverse.append(r)
            seen_shows.add(r["show_name"])
            if len(diverse) >= LIMIT:
                break

    elapsed = (time.perf_counter() - start) * 1000.0
    return {
        "query": q,
        "tokens": tokens,
        "time_ms": round(elapsed, 2),
        "results": diverse,
    }
