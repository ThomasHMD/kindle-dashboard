#!/usr/bin/env python3
"""demo.py : fabrique tous les écrans sans aucun compte, pour voir le rendu avant de brancher Google, Notion ou n8n.

Réglages de config.json, ou à défaut de config.exemple.json ; agenda fictif (agenda-maquette.json écrit dans le
dossier de sortie) ; aucune clé lue. Les sources ouvertes (Open-Meteo, ilévia, Cleveland Museum, Wiktionnaire) sont
interrogées pour de vrai.

    python3 demo.py                      # dans ./demo/ : apercu-<écran>.png (paysage) et ecran-<écran>.png (liseuse)
    python3 demo.py --sortie /tmp/essai --heure 2026-01-01T08:15
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ICI = Path(__file__).resolve().parent


def agenda_fictif(jour):
    """Quelques rendez-vous au format de l'API Google Agenda, aujourd'hui et demain."""
    def ev(n, h, m, duree, titre, lieu=""):
        d = dt.datetime.combine(jour + dt.timedelta(days=n), dt.time(h, m), ZoneInfo("Europe/Paris"))
        return {"summary": titre, "location": lieu, "start": {"dateTime": d.isoformat()},
                "end": {"dateTime": (d + dt.timedelta(minutes=duree)).isoformat()}}
    return [ev(0, 9, 0, 60, "Réunion d'équipe"), ev(0, 12, 30, 90, "Déjeuner avec Léa", "Café du Coin, 2 rue de la Paix"),
            ev(0, 18, 0, 60, "Piscine"), ev(0, 20, 30, 120, "Cinéma", "Le Majestic"),
            ev(1, 8, 30, 30, "Dentiste"), ev(1, 14, 0, 60, "Appel banque"),
            {"summary": "Anniversaire de Paul", "start": {"date": f"{jour + dt.timedelta(days=1):%Y-%m-%d}"},
             "end": {"date": f"{jour + dt.timedelta(days=2):%Y-%m-%d}"}}]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sortie", type=Path, default=ICI / "demo")
    ap.add_argument("--heure", help="heure simulée AAAA-MM-JJTHH:MM")
    ap.add_argument("--modele", default="k4")
    args = ap.parse_args()
    args.sortie.mkdir(parents=True, exist_ok=True)
    jour = dt.date.fromisoformat(args.heure[:10]) if args.heure else dt.date.today()
    (args.sortie / "agenda-maquette.json").write_text(json.dumps(agenda_fictif(jour), ensure_ascii=False), encoding="utf-8")
    # Aucune clé : ni celles de l'environnement, ni un .env trouvé en remontant les dossiers (DEMO_SANS_ENV).
    env = {k: v for k, v in os.environ.items() if k in ("PATH", "HOME", "LANG", "LC_ALL", "TMPDIR", "PLAYWRIGHT_BROWSERS_PATH")}
    env["KINDLE_DEMO"] = "1"
    cmd = [sys.executable, str(ICI / "dashboard.py"), "--tous", "--modele", args.modele, "--sortie", str(args.sortie)]
    if args.heure:
        cmd += ["--heure", args.heure]
    r = subprocess.run(cmd, env=env)
    for f in sorted(args.sortie.glob("apercu-*.png")):
        print(f)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
