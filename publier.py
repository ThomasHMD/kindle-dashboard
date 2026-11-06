#!/usr/bin/env python3
"""publier.py : publie les scripts de la liseuse : seul chemin entre les sources (liseuse/dashboard/, dossier synchronisé)
et ce que serveur.py sert à la liseuse (~/Library/Caches/kindle-dashboard/publie/).

Chaque script doit passer `dash -n` (le shell du Mac le plus proche de l'ash de BusyBox) et ne pas contenir de fin de
ligne Windows ; un seul refus, et rien n'est publié. La copie est atomique, fichier par fichier ; la liseuse vérifie
taille et md5 de chacun et prend la nouvelle version à sa lecture d'état suivante (20 s au plus).

    python3 publier.py          # contrôle puis publie ; code 0 = publié (ou déjà à jour), 1 = refusé
    python3 publier.py --diff   # dit seulement si les sources diffèrent de ce qui est publié (code 1 si oui)
"""
import subprocess
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
from serveur import LISEUSE, PAQUET, PUBLIE, paquet  # noqa: E402


def main():
    differents = [n for n in PAQUET if not (PUBLIE / n).is_file() or (PUBLIE / n).read_bytes() != (LISEUSE / n).read_bytes()]
    if "--diff" in sys.argv:
        print("à jour" if not differents else "à publier : " + ", ".join(differents))
        return 1 if differents else 0
    refus = []
    for nom in PAQUET:
        f = LISEUSE / nom
        if not f.is_file():
            refus.append(f"{nom} : absent")
            continue
        if b"\r" in f.read_bytes():
            refus.append(f"{nom} : fins de ligne Windows")
        r = subprocess.run(["dash", "-n", str(f)], capture_output=True, text=True)
        if r.returncode:
            refus.append(f"{nom} : {r.stderr.strip()}")
    if refus:
        print("rien publié :\n  " + "\n  ".join(refus))
        return 1
    if not differents:
        print(f"déjà publié (version {paquet()[1]})")
        return 0
    PUBLIE.mkdir(parents=True, exist_ok=True)
    for nom in differents:
        tmp = PUBLIE / f".{nom}.tmp"
        tmp.write_bytes((LISEUSE / nom).read_bytes())
        tmp.replace(PUBLIE / nom)
    print(f"publié : {', '.join(differents)} → version {paquet()[1]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
