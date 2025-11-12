# app/services/normalize.py
from __future__ import annotations
from collections import Counter
from .subtitles import srt_to_lines
import re
import unicodedata

# Petite liste FR/EN – on l’enrichira plus tard si besoin
STOPWORDS = {
    # FR
    "a", "à", "ai", "aie", "aient", "ait", "alors", "au", "aux", "avec", "car", "ce",
    "cela", "ces", "cet", "cette", "ceci", "comme", "d", "dans", "de", "des", "du",
    "elle", "elles", "en", "et", "eu", "est", "etait", "ete", "etre", "il", "ils",
    "je", "la", "le", "les", "leur", "lui", "ma", "mais", "me", "meme", "mes", "moi",
    "mon", "ne", "nos", "notre", "nous", "on", "ou", "par", "pas", "pour", "qu",
    "que", "qui", "sa", "se", "ses", "si", "son", "sur", "ta", "te", "tes", "toi",
    "ton", "tu", "un", "une", "vos", "votre", "vous", "y",
    # EN
    "a", "an", "the", "and", "or", "but", "if", "in", "on", "at", "to", "of", "for",
    "is", "it", "its", "this", "that", "these", "those", "i", "you", "he", "she",
    "we", "they", "me", "him", "her", "them", "my", "your", "his", "their", "our",
}

_PUNCT = re.compile(r"[^\w\s]", flags=re.UNICODE)  # ponctuation
_DIGITS = re.compile(r"\d+", flags=re.UNICODE)     # chiffres

def _strip_accents(s: str) -> str:
    """Supprime les accents (é -> e)."""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")

def normalize_line(line: str) -> list[str]:
    """
    Transforme une ligne en tokens 'propres' :
    - minuscules
    - sans accents
    - sans chiffres ni ponctuation
    - sans stopwords
    - tokens de longueur > 1
    """
    s = line.lower()
    s = _strip_accents(s)
    s = _DIGITS.sub(" ", s)
    s = _PUNCT.sub(" ", s)
    tokens = s.split()
    tokens = [t for t in tokens if t not in STOPWORDS and len(t) > 1]
    return tokens

def normalize_lines(lines: list[str]) -> list[list[str]]:
    """Applique normalize_line à une liste de lignes."""
    return [normalize_line(l) for l in lines]

def tokens_flatten(lines_tokens: list[list[str]]) -> list[str]:
    """Aplati [[t1,t2],[t3]] -> [t1,t2,t3]."""
    out: list[str] = []
    for toks in lines_tokens:
        out.extend(toks)
    return out

def token_counts_from_file(file_path: str, top_k: int = 20) -> dict:
    """
    Lit un .srt, nettoie toutes les lignes, compte les tokens,
    et retourne les top_k plus fréquents.
    """
    lines = srt_to_lines(file_path)
    tokens_per_line = normalize_lines(lines)
    all_tokens = tokens_flatten(tokens_per_line)
    counts = Counter(all_tokens)
    top = counts.most_common(top_k)
    return {
        "total_lines": len(lines),
        "total_tokens": len(all_tokens),
        "vocab_size": len(counts),
        "top": top,  # liste de [("mot", freq), ...]
    }

def bigrams(tokens: list[str]) -> list[tuple[str, str]]:
    return list(zip(tokens, tokens[1:]))
