#!/usr/bin/env python3
"""liseuse.py : la main sur la liseuse depuis le Mac, par le wifi, sans câble : commandes root et copies de fichiers.

Le serveur (serveur.py) pose la commande ; la liseuse la voit à sa lecture d'état suivante (20 s au plus), l'exécute
une fois en root dans /mnt/us/dashboard (variables SERVEUR et DIR fournies, 300 s au plus), et renvoie la sortie
(64 Ko au plus) que ce script affiche. Le dashboard doit tourner sur la liseuse.

    python3 liseuse.py 'ls -l /etc/rc5.d'                 # une commande shell (BusyBox 1.7.2)
    python3 liseuse.py --script fichier.sh                # un script entier
    python3 liseuse.py --pousser local.png /mnt/us/x.png  # copie un fichier du Mac vers la liseuse (partition
                                                          # système comprise : ouverte en écriture le temps de la copie)
    python3 liseuse.py --journal 50                       # fin du journal de la liseuse
    python3 liseuse.py --redemarrer                       # redémarre la liseuse (le dashboard repart seul en 90 s)

Le fichier copié par --pousser est effacé du Mac dès la réponse de la liseuse (c'est ainsi que le jeton y est posé).

Code de sortie : celui de la commande sur la liseuse ; 2 si elle n'a pas répondu à temps.
"""
import argparse
import hashlib
import re
import shlex
import sys
import time
from pathlib import Path

SORTIE = Path.home() / "Library/Caches/kindle-dashboard"


def executer(script, attente):
    script = f"# {time.time_ns()}\n{script}"  # chaque appel est une commande neuve, même texte ou pas
    ident = hashlib.md5(script.encode()).hexdigest()[:12]
    resultat = SORTIE / "commandes" / f"{ident}.txt"
    resultat.unlink(missing_ok=True)
    tmp = SORTIE / "commande.sh.tmp"
    tmp.write_text(script, encoding="utf-8")
    tmp.replace(SORTIE / "commande.sh")
    print(f"commande {ident} posée, la liseuse la prend à sa prochaine lecture (20 s au plus)…", file=sys.stderr)
    fin = time.time() + attente
    try:
        while time.time() < fin and not resultat.exists():
            time.sleep(1)
    finally:
        commande = SORTIE / "commande.sh"
        if commande.exists() and hashlib.md5(commande.read_bytes()).hexdigest()[:12] == ident:
            commande.unlink()
    if not resultat.exists():
        print("pas de réponse de la liseuse (dashboard arrêté, hors ligne ?) : voir liseuse.json", file=sys.stderr)
        return 2
    texte = resultat.read_text(encoding="utf-8", errors="replace")
    resultat.unlink()
    print(texte, end="")
    code = re.search(r"--- code de sortie (\d+)\s*$", texte)
    return int(code.group(1)) if code else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("commande", nargs="?")
    ap.add_argument("--script", type=Path)
    ap.add_argument("--pousser", nargs=2, metavar=("LOCAL", "DISTANT"))
    ap.add_argument("--journal", type=int, metavar="N")
    ap.add_argument("--redemarrer", action="store_true")
    ap.add_argument("--attente", type=int, default=400, help="secondes d'attente de la réponse")
    ap.add_argument("--sortie", type=Path, help=argparse.SUPPRESS)  # essais : un autre serveur
    args = ap.parse_args()
    global SORTIE
    SORTIE = args.sortie or SORTIE
    if args.script:
        script = args.script.read_text(encoding="utf-8")
    elif args.pousser:
        local, distant = Path(args.pousser[0]), args.pousser[1]
        octets = local.read_bytes()
        somme = hashlib.md5(octets).hexdigest()
        (SORTIE / "pousse").mkdir(exist_ok=True)
        (SORTIE / "pousse" / somme).write_bytes(octets)
        d = shlex.quote(distant)
        copie = (f'wget -q -U "kindle-dashboard/$(cat "$DIR/jeton" 2>/dev/null)" -O {d}.neuf "$SERVEUR/pousse/{somme}"'
                 f' && [ "$(wc -c < {d}.neuf | tr -d " ")" = {len(octets)} ]'
                 f' && mv {d}.neuf {d} && echo "copié : {distant} ({len(octets)} octets)"')
        script = copie if distant.startswith("/mnt/us/") else f"mntroot rw\n{copie}\nr=$?\nsync\nmntroot ro\nexit $r"
    elif args.journal:
        script = f'tail -{args.journal} "$DIR/journal.txt"'
    elif args.redemarrer:
        script = 'echo "redémarrage demandé par le Mac"; (sleep 5; reboot) >/dev/null 2>&1 &'
    elif args.commande:
        script = args.commande
    else:
        ap.error("une commande, --script, --pousser, --journal ou --redemarrer")
    try:
        return executer(script + "\n", args.attente)
    finally:
        if args.pousser:
            (SORTIE / "pousse" / somme).unlink(missing_ok=True)


if __name__ == "__main__":
    sys.exit(main())
