# scripts/bulk_index.py
import re
import sys
import pathlib
import requests

BASE_URL = "http://127.0.0.1:8000"
INDEX_ENDPOINT = "/admin/index-srt"      # doit correspondre à ton route @router.post("/index-srt")

# Garde uniquement ces tags. Vide => aucune restriction.
LANG_KEEP = {"VF", "FR"}                 # mets set() si tu veux tout prendre

PATTERNS = [
    re.compile(r"[Ss](\d{1,2})[ ._-]*[Ee](\d{1,2})"),  # S01E02, S1E3, S01.E02, etc.
    re.compile(r"(\d{1,2})[xX](\d{2})"),               # 2x01, 11x05, etc.
]

def detect_season_ep(filename: str):
    stem = pathlib.Path(filename).stem
    for pat in PATTERNS:
        m = pat.search(stem)
        if m:
            s, e = m.groups()
            return int(s), int(e)
    return None

def keep_by_language(filename: str) -> bool:
    if not LANG_KEEP:
        return True
    upper = filename.upper()
    return any(tag in upper for tag in LANG_KEEP)

def show_from_path(path: str) -> str:
    p = pathlib.Path(path)
    return p.parent.name.replace("_", " ").strip()

def index_file(abs_path: str, show: str, season: int, ep: int, session: requests.Session):
    params = {
        "file": abs_path.replace("\\", "/"),
        "show": show,
        "season": season,
        "ep": ep,
    }
    url = BASE_URL + INDEX_ENDPOINT
    r = session.post(url, params=params, timeout=30)
    r.raise_for_status()
    return r.json()

def run_all(root_dir: str = "data/sous-titres") -> int:
    """
    Parcourt tous les .srt sous root_dir, tente de les indexer via l'API,
    et renvoie le nombre d'épisodes (fichiers) indexés avec succès.
    """
    root = pathlib.Path(root_dir)
    if not root.exists():
        print(f"[ERR] dossier introuvable: {root.resolve()}")
        return 0

    count_ok = 0

    with requests.Session() as session:
        for srt in root.rglob("*.srt"):
            if not keep_by_language(srt.name):
                # print(f"[SKIP-LANG] {srt.name}")
                continue

            se = detect_season_ep(srt.name)
            if not se:
                # print(f"[SKIP] pas de motif SxxEyy ni Nxnn dans {srt.name}")
                continue

            season, ep = se
            show = show_from_path(srt)
            abs_path = str(srt.resolve())

            try:
                resp = index_file(abs_path, show, season, ep, session=session)
                # print(f"[OK] {show} S{season:02d}E{ep:02d} <- {srt.name} | {resp.get('status','')}")
                count_ok += 1
            except requests.RequestException as e:
                # print(f"[ERR] requête -> {abs_path} : {e}")
                pass

    return count_ok

def main():
    count = run_all("data/sous-titres")
    print(f"[DONE] {count} fichiers indexés.")

if __name__ == "__main__":
    main()
