#!/usr/bin/env python3
"""verifier.py : santé du Kindle-dashboard en une commande (chaque jour, ou à la main).

Contrôle, sans toucher à rien : le serveur répond (/sonde) ; la liseuse est passée il y a moins de 10 min ; elle
porte la version des scripts publiés ; les sources n'ont pas changé depuis la dernière publication (publier.py) ;
son horloge est juste ; les écrans ont été régénérés il y a moins de 5 min ; le journal du serveur n'a pas d'erreur
depuis 24 h ; l'autorisation Google (agenda, courrier) marche vraiment (un échange de jeton). Lit aussi le journal de
la liseuse par le canal de commande (liseuse.py, 20 s au plus), ce qui vérifie ce canal du même coup.

    python3 verifier.py       # une ligne par contrôle ; code 0 = tout va bien, 1 = au moins un défaut
"""
import datetime as dt
import json
import subprocess
import sys
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
SORTIE = Path.home() / "Library/Caches/kindle-dashboard"
JOURNAL_MAC = Path.home() / "Library/Logs/kindle-dashboard.log"
sys.path.insert(0, str(ICI))
from serveur import paquet  # noqa: E402
from dashboard import jeton_google, lire_env  # noqa: E402


def lire(url):
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read().decode("utf-8", "replace")


def main():
    maintenant = dt.datetime.now()
    defauts, notes = [], []

    def ok(cond, bien, mal):
        (notes if cond else defauts).append(bien if cond else mal)

    try:
        ok(lire("http://127.0.0.1:8765/sonde").startswith("kindle-dashboard"), "serveur : répond", "serveur : réponse inattendue")
    except OSError as e:
        defauts.append(f"serveur : injoignable ({e}) : `launchctl kickstart -k gui/$(id -u)/com.exemple.kindle-dashboard`")
    etat = SORTIE / "etat.json"
    if etat.exists():
        age = (maintenant.timestamp() - etat.stat().st_mtime) / 60
        ok(age < 5, f"écrans : régénérés il y a {age:.0f} min", f"écrans : pas régénérés depuis {age:.0f} min")
    else:
        defauts.append("écrans : etat.json absent")
    liseuse = {}
    try:
        liseuse = json.loads((SORTIE / "liseuse.json").read_text(encoding="utf-8"))
        absence = (maintenant - dt.datetime.fromisoformat(liseuse["vu"])).total_seconds() / 60
        ok(absence < 10, f"liseuse : vue il y a {absence:.0f} min ({liseuse['adresse']}, batterie {liseuse['batterie']} %)",
           f"liseuse : silencieuse depuis {absence:.0f} min (dernière adresse {liseuse.get('adresse')})")
        version = paquet()[1]
        ok(liseuse.get("version") == version, f"scripts : version {version} en place",
           f"scripts : la liseuse a « {liseuse.get('version') or 'ancienne boucle'} », le Mac sert {version}")
        ecart = liseuse.get("ecart_horloge_s")
        ok(ecart is not None and abs(ecart) <= 60, "horloge : juste", f"horloge : écart {ecart} s")
    except (OSError, ValueError, KeyError) as e:
        defauts.append(f"liseuse : liseuse.json illisible ({type(e).__name__})")
    r = subprocess.run([sys.executable, str(ICI / "publier.py"), "--diff"], capture_output=True, text=True)
    ok(r.returncode == 0, "publication : sources et scripts publiés identiques",
       f"publication : {r.stdout.strip()} (`python3 publier.py`)")
    erreurs = []
    if JOURNAL_MAC.exists():
        hier = (maintenant - dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
        erreurs = [l for l in JOURNAL_MAC.read_text(encoding="utf-8", errors="replace").splitlines()
                   if l[:19] >= hier and l[:4].isdigit() and "serveur sur le port" not in l]
    ok(not erreurs, "journal du serveur : aucune erreur depuis 24 h",
       f"journal du serveur : {len(erreurs)} erreur(s) depuis 24 h, dernière : {erreurs[-1][:160] if erreurs else ''}")
    try:  # un vrai échange : un jeton présent mais expiré (client OAuth en mode Test : 7 jours) se voit ici
        ok(bool(jeton_google("GOOGLE_KINDLE_REFRESH_TOKEN")), "Google : autorisation valable",
           "Google : autorisation à donner (`python3 autoriser.py`, un clic dans le navigateur)")
    except OSError as e:
        defauts.append(f"Google : autorisation refusée ou injoignable ({e}) : `python3 autoriser.py`, un clic dans le navigateur")
    if liseuse.get("adresse"):
        # Seulement les lignes d'incident : la liseuse renvoie une ligne par requête et n'affiche rien pendant ce temps.
        incidents = 'grep "tombée\\|refusée\\|ratée\\|raté \\|invalide\\|injoignable\\|perdue" journal.txt | tail -20'
        r = subprocess.run([sys.executable, str(ICI / "liseuse.py"), "--attente", "90", incidents],
                           capture_output=True, text=True)
        if r.returncode == 0:
            graves = [l for l in r.stdout.splitlines() if l[:10] == maintenant.strftime("%Y-%m-%d")]
            ok(not graves, "journal de la liseuse : rien d'anormal aujourd'hui",
               f"journal de la liseuse : {len(graves)} incident(s) aujourd'hui, dernier : {graves[-1][:160] if graves else ''}")
        else:
            defauts.append("journal de la liseuse : pas de réponse au canal de commande (liseuse.py)")
    for n in notes:
        print(f"✓ {n}")
    for d in defauts:
        print(f"✗ {d}")
    return 1 if defauts else 0


if __name__ == "__main__":
    sys.exit(main())
