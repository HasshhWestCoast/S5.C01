import re
from pathlib import Path

# Ligne de timecode: 00:00:12,345 --> 00:00:14,210
TIME_LINE = re.compile(r"\d{2}:\d{2}:\d{2},\d{3}\s*-->\s*\d{2}:\d{2}:\d{2},\d{3}")

def _read_text_guess_encoding(path: Path) -> str:
    """Lit le fichier en essayant quelques encodages courants."""
    for enc in ("utf-8", "utf-16", "cp1252", "latin-1"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    # Dernier recours: ignore les erreurs
    return path.read_text(encoding="utf-8", errors="ignore")

def srt_to_lines(file_path: str) -> list[str]:
    """
    Retourne les lignes utiles (sans les numéros de blocs, ni timecodes, ni balises <i> ...>).
    """
    path = Path(file_path)
    raw = _read_text_guess_encoding(path)
    lines: list[str] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.isdigit():               # numéros de séquence
            continue
        if TIME_LINE.search(line):       # timecodes
            continue
        # supprime les balises simples <i>...</i>, <font ...>, etc.
        line = re.sub(r"<[^>]+>", "", line)
        lines.append(line)
    return lines

def srt_to_text(file_path: str) -> str:
    """Texte concaténé sur une seule ligne (pratique pour les étapes suivantes)."""
    return " ".join(srt_to_lines(file_path))
