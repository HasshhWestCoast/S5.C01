# app/services/indexer.py
from __future__ import annotations
from collections import Counter
from pathlib import Path

from app.core.db import get_connection
from app.services.subtitles import srt_to_lines
from app.services.normalize import normalize_lines, tokens_flatten, bigrams

def index_srt(file_path: str, show_name: str | None = None, season: int | None = None, episode: int | None = None) -> dict:
    """
    Lit un .srt, normalise, compte les tokens (unigrams) ET bigrams, puis écrit dans la BDD.
    Tables utilisées : episodes, unigram_counts, bigram_counts (ton schéma).
    """
    path = Path(file_path)

    # 1) extraction + normalisation
    lines = srt_to_lines(str(path))
    toks_per_line = normalize_lines(lines)
    toks_all = tokens_flatten(toks_per_line)
    bigs_all = bigrams(toks_all)

    c_uni = Counter(toks_all)
    c_bi  = Counter(bigs_all)

    # 2) upsert épisode
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO episodes (show_name, season, episode, file_path)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (file_path)
                DO UPDATE SET show_name = EXCLUDED.show_name,
                              season    = EXCLUDED.season,
                              episode   = EXCLUDED.episode
                RETURNING id;
                """,
                (show_name, season, episode, str(path)),
            )
            row = cur.fetchone()
            episode_id = row["id"] if hasattr(row, "keys") else row[0]

            # 3) upsert UNIGRAMS
            for token, freq in c_uni.items():
                cur.execute(
                    """
                    INSERT INTO unigram_counts (episode_id, token, freq)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (episode_id, token)
                    DO UPDATE SET freq = EXCLUDED.freq;
                    """,
                    (episode_id, token, freq),
                )

            # 4) upsert BIGRAMS
            for (t1, t2), freq in c_bi.items():
                cur.execute(
                    """
                    INSERT INTO bigram_counts (episode_id, token1, token2, freq)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (episode_id, token1, token2)
                    DO UPDATE SET freq = EXCLUDED.freq;
                    """,
                    (episode_id, t1, t2, freq),
                )

        conn.commit()

    return {
        "episode_id": episode_id,
        "file": str(path),
        "lines": len(lines),
        "tokens_total": sum(c_uni.values()),
        "unigrams_unique": len(c_uni),
        "bigrams_unique": len(c_bi),
    }
