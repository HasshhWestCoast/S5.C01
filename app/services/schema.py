# app/services/schema.py
from app.core.db import get_connection

DDL = """
-- Épisodes + index
CREATE TABLE IF NOT EXISTS episodes (
    id SERIAL PRIMARY KEY,
    show_name TEXT,
    season INT,
    episode INT,
    file_path TEXT UNIQUE NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_episodes_show_season_ep
  ON episodes(show_name, season, episode);

-- Unigrammes
CREATE TABLE IF NOT EXISTS unigram_counts (
    episode_id INT REFERENCES episodes(id) ON DELETE CASCADE,
    token TEXT NOT NULL,
    freq INT NOT NULL,
    PRIMARY KEY (episode_id, token)
);
CREATE INDEX IF NOT EXISTS idx_unigrams_token
  ON unigram_counts(token);

-- Bigrammes
CREATE TABLE IF NOT EXISTS bigram_counts (
    episode_id INT REFERENCES episodes(id) ON DELETE CASCADE,
    token1 TEXT NOT NULL,
    token2 TEXT NOT NULL,
    freq INT NOT NULL,
    PRIMARY KEY (episode_id, token1, token2)
);
CREATE INDEX IF NOT EXISTS idx_bigrams_t1_t2
  ON bigram_counts(token1, token2);

-- (Optionnel mais utile pour la reco/IDF si tu l'utilises)
CREATE TABLE IF NOT EXISTS token_df (
    token TEXT PRIMARY KEY,
    df INT NOT NULL,
    idf DOUBLE PRECISION NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_token_df_token ON token_df(token);

-- Utilisateurs (auth)
CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    login TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Notes utilisateur (préférence séries)
CREATE TABLE IF NOT EXISTS user_ratings (
    user_id TEXT NOT NULL,
    show_name TEXT NOT NULL,
    rating INT NOT NULL,
    PRIMARY KEY (user_id, show_name),
    CHECK (rating >= 1 AND rating <= 5)
);
CREATE INDEX IF NOT EXISTS idx_user_ratings_user ON user_ratings(user_id);
CREATE INDEX IF NOT EXISTS idx_user_ratings_show ON user_ratings(show_name);
"""

def init_schema() -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)
        conn.commit()
