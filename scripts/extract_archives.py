# scripts/extract_archives.py
from pathlib import Path
import zipfile
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]         # racine du projet
SUBS = ROOT / "data" / "sous-titres"               # là où sont tes sous-titres
SEVEN_ZIP_EXE = r"C:\Program Files\7-Zip\7z.exe"   # modifie si besoin

def extract_zip(p: Path):
    try:
        with zipfile.ZipFile(p, "r") as zf:
            zf.extractall(p.parent)
        print(f"[ZIP] OK  -> {p}")
    except Exception as e:
        print(f"[ZIP] ERR -> {p} : {e}")

def extract_7z(p: Path):
    # 1) essayer py7zr si dispo
    try:
        import py7zr  # type: ignore
        with py7zr.SevenZipFile(p, mode="r") as z:
            z.extractall(path=p.parent)
        print(f"[7Z]  OK  -> {p} (py7zr)")
        return
    except ImportError:
        pass
    except Exception as e:
        print(f"[7Z]  ERR py7zr -> {p} : {e}")

    # 2) sinon tenter l'exécutable 7-Zip
    try:
        subprocess.run([SEVEN_ZIP_EXE, "x", str(p), f"-o{p.parent}", "-y"],
                       check=True, capture_output=True)
        print(f"[7Z]  OK  -> {p} (7z.exe)")
    except Exception as e:
        print(f"[7Z]  ERR  -> {p} : {e}\n"
              f"Installe 'py7zr' (pip install py7zr) ou ajuste SEVEN_ZIP_EXE.")

def main():
    if not SUBS.exists():
        print(f"Dossier introuvable : {SUBS}")
        sys.exit(1)

    zips = list(SUBS.rglob("*.zip"))
    z7s  = list(SUBS.rglob("*.7z"))

    if not zips and not z7s:
        print("Aucune archive .zip ou .7z trouvée.")
        return

    for p in zips:
        extract_zip(p)
    for p in z7s:
        extract_7z(p)

    print("\n✅ Décompression terminée.")

if __name__ == "__main__":
    main()
