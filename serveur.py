#!/usr/bin/env python3
"""serveur.py : côté Mac : régénère les écrans chaque minute et les sert à la liseuse en HTTP local.

Un seul processus, lancé (et relancé s'il tombe) par l'agent launchd com.exemple.kindle-dashboard :
- toutes les minutes (à la seconde 2), lance `dashboard.py --tous` : tous les écrans sont prêts, les boutons de la
  liseuse passent de l'un à l'autre sans attendre. Une génération ratée ou trop longue (Chromium compris) est
  arrêtée et notée, jamais fatale : la liseuse garde les derniers écrans ;
- sert à la liseuse ce qu'il lui faut, et rien d'autre du dossier de sortie (il contient le cache mails et agenda) :
  /etat.txt     la ligne que lit boucle.sh (v2 ; sans `v=2`, l'ancienne ligne de la première boucle) ;
  /ecran.png    l'écran demandé (?p=) ou celui du moment, et sa variante « hors ligne » (?hl=1) ;
  /liseuse/…    les scripts de la liseuse (paquet.txt : noms, md5, tailles), pour la mise à jour à distance, et
                commande.sh, la commande posée par liseuse.py ;
  /retour       la sortie de cette commande, renvoyée par la liseuse en morceaux octaux (pas de POST dans son wget) ;
  /pousse/<md5> un fichier que liseuse.py fait copier sur la liseuse ;
  /sonde        réponse fixe, qui permet à la liseuse de retrouver le Mac si son adresse change ;
- garde l'écran choisi aux boutons (?nav=suivant|precedent|auto) MANUEL secondes, puis rend la main à la rotation ;
- éjecte la liseuse si elle reste montée en clé USB plus de 2 min (branchée au Mac, elle passe d'elle-même en mode
  USB au démarrage, et le dashboard attend la fin de ce mode) ; sauf si le fichier garder-usb existe dans la sortie ;
- note chaque passage de la liseuse dans liseuse.json (heure, adresse, batterie, écart d'horloge, version des
  scripts, écran servi, dernière touche) : le battement de cœur, et de quoi vérifier la liseuse sans y toucher ;
- n'ouvre les écrans (mails, agenda), les commandes et les copies qu'à la liseuse : son user-agent porte le jeton
  KINDLE_JETON du .env (le wget de la liseuse n'a pas --header). Scripts, /sonde et une ligne d'état réduite (heure,
  version, aucun écran) restent ouverts : une liseuse sans jeton peut toujours se mettre à jour ;
- sert les scripts publiés par publier.py (dossier publie/ de la sortie, syntaxe contrôlée), jamais les sources (dossier
  synchronisé entre plusieurs Mac) : un fichier en cours d'écriture ou arrivé d'un autre Mac ne part pas sur la liseuse ;
- écrans périmés (dashboard.py en panne depuis 5 min) : sert leur variante « HORS LIGNE », qui dit l'heure du
  dernier relevé, plutôt qu'un écran figé qui aurait l'air à jour.

    python3 serveur.py [--port 8765] [--sortie ~/Library/Caches/kindle-dashboard]
"""
import argparse
import datetime as dt
import hashlib
import hmac
import http.server
import json
import os
import re
import signal
import subprocess
import sys
import threading
import time
import urllib.parse
from pathlib import Path

ICI = Path(__file__).resolve().parent
LISEUSE = ICI / "liseuse/dashboard"
PUBLIE = Path.home() / "Library/Caches/kindle-dashboard/publie"  # écrit par publier.py
JOURNAL_MAC = Path.home() / "Library/Logs/kindle-dashboard.log"  # sortie d'erreur de l'agent launchd
PERIME = 300  # secondes sans régénération au-delà desquelles un écran est servi en « HORS LIGNE »
JETON = ""    # KINDLE_JETON du .env, lu au lancement ; vide = rien n'est exigé
PAQUET = ["config.sh", "commun.sh", "boucle.sh", "touches.sh", "superviseur.sh", "demarrer.sh", "arreter.sh",
          "tester.sh", "demarrage-auto.sh"]  # scripts tenus à jour sur la liseuse
MANUEL = 600  # secondes pendant lesquelles un écran choisi aux boutons reste affiché
choix = {"ecran": None, "jusqu": 0.0, "touche": None}
annonces = {}  # empreinte → (image, variante hors ligne) annoncées dans etat.txt : servies telles quelles ensuite,
               # même si l'écran a été régénéré entre la lecture d'état et le téléchargement
verrou = threading.Lock()


def note(texte):
    print(f"{dt.datetime.now():%Y-%m-%d %H:%M:%S} {texte}", file=sys.stderr, flush=True)


def generer(sortie):
    """Un passage de dashboard.py, borné à 110 s ; au-delà, tout son groupe de processus (Chromium) est tué."""
    p = subprocess.Popen([sys.executable, str(ICI / "dashboard.py"), "--tous", "--sortie", str(sortie)],
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=True)
    try:
        _, err = p.communicate(timeout=110)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL)
        p.communicate()
        note("dashboard.py : plus de 110 s, arrêté avec son Chromium")
        return
    if p.returncode != 0 or err.strip():
        note(f"dashboard.py ({p.returncode}) : {err.strip()[-500:]}")


def entretien(sortie):
    """Une fois par minute : journal launchd plafonné à 2 Mo (copié dans .ancien puis vidé : launchd écrit en ajout),
    commandes et copies de plus d'un jour effacées."""
    if JOURNAL_MAC.exists() and JOURNAL_MAC.stat().st_size > 2_000_000:
        JOURNAL_MAC.with_suffix(".log.ancien").write_bytes(JOURNAL_MAC.read_bytes())
        os.truncate(JOURNAL_MAC, 0)
    for f in [*(sortie / "commandes").glob("*"), *(sortie / "pousse").glob("*")]:
        if time.time() - f.stat().st_mtime > 86400:
            f.unlink(missing_ok=True)


def regenerer(sortie):
    while True:
        try:
            generer(sortie)
            entretien(sortie)
        except Exception as e:  # noqa: BLE001 : rien ne doit arrêter ce fil : il reprend la minute suivante
            note(f"régénération : {type(e).__name__} {e}")
        attente = 62 - time.time() % 60  # juste après le changement de minute
        time.sleep(attente if attente <= 60 else attente - 60)


def ejecter(sortie):
    """Liseuse montée en clé USB depuis plus de 2 min (et pas de garder-usb) : l'éjecter pour que le dashboard démarre."""
    depuis = None
    while True:
        time.sleep(30)
        try:
            if Path("/Volumes/Kindle/dashboard").exists() and not (sortie / "garder-usb").exists():
                depuis = depuis or time.time()
                if time.time() - depuis >= 120:
                    r = subprocess.run(["diskutil", "eject", "/Volumes/Kindle"], capture_output=True, text=True, timeout=60)
                    note(f"liseuse montée en clé USB depuis 2 min, éjectée : {(r.stdout or r.stderr).strip()}")
                    depuis = None
            else:
                depuis = None
        except Exception as e:  # noqa: BLE001
            note(f"éjection : {type(e).__name__} {e}")


def paquet(dossier=None):
    """(texte de paquet.txt, version) des scripts publiés ; la version change dès qu'un script publié change.
    Rien de publié (ou publication incomplète) : ("", "-"), que la liseuse ignore."""
    dossier = dossier or PUBLIE
    if not all((dossier / nom).is_file() for nom in PAQUET):
        return "", "-"
    lignes = ""
    for nom in PAQUET:
        octets = (dossier / nom).read_bytes()
        lignes += f"{nom} {hashlib.md5(octets).hexdigest()} {len(octets)}\n"
    return lignes, hashlib.md5(lignes.encode()).hexdigest()[:12]


def commande_en_cours(sortie):
    """Identifiant de la commande posée par liseuse.py (md5 de commande.sh), « - » s'il n'y en a pas. Une commande de
    plus de 15 min est abandonnée (liseuse.py tué sans faire le ménage) : jamais exécutée sur le tard."""
    f = sortie / "commande.sh"
    if f.exists() and time.time() - f.stat().st_mtime > 900:
        f.unlink(missing_ok=True)
    return hashlib.md5(f.read_bytes()).hexdigest()[:12] if f.exists() else "-"


def ecran_servi(etat, nav, pas=1):
    """Écran à servir : celui choisi aux boutons tant qu'il n'a pas expiré, sinon celui de la rotation. `pas` = appuis
    rapprochés que la liseuse a cumulés avant de demander (trois fois → = trois écrans plus loin)."""
    with verrou:
        manuel = choix["ecran"] if choix["ecran"] and time.time() < choix["jusqu"] else None
        if nav in ("suivant", "precedent"):
            ordre = etat["navigation"]
            depart = manuel or etat["panneau"]
            i = ordre.index(depart) if depart in ordre else 0
            manuel = ordre[(i + (pas if nav == "suivant" else -pas)) % len(ordre)]
            choix.update(ecran=manuel, jusqu=time.time() + MANUEL)
        elif nav == "auto":
            manuel = choix["ecran"] = None
    return manuel or etat["panneau"], manuel is not None


def gestionnaire(sortie):
    perime = {"note": False}

    class Gestionnaire(http.server.BaseHTTPRequestHandler):
        timeout = 30  # une liseuse qui raccroche en pleine requête ne retient pas un fil

        def autorise(self):
            return not JETON or hmac.compare_digest(self.headers.get("User-Agent", ""), "kindle-dashboard/" + JETON)

        def parse_request(self):
            # Accents envoyés bruts par le wget de la liseuse : encodés en %XX avant l'analyse, sinon 0xA0 (dans « à »)
            # et 0x85, que str.split() prend pour des espaces, coupent la ligne de requête en trop de morceaux.
            self.raw_requestline = re.sub(rb"[\x80-\xff]", lambda m: b"%%%02X" % m.group()[0], self.raw_requestline)
            return super().parse_request()

        def envoyer(self, corps, type_mime):
            self.send_response(200)
            self.send_header("Content-Type", type_mime)
            self.send_header("Content-Length", str(len(corps)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(corps)

        def do_GET(self):
            url = urllib.parse.urlparse(self.path)
            q = dict(urllib.parse.parse_qsl(url.query, keep_blank_values=True))
            try:
                if url.path == "/sonde":
                    return self.envoyer(b"kindle-dashboard\n", "text/plain; charset=utf-8")
                if url.path == "/liseuse/paquet.txt":
                    return self.envoyer(paquet()[0].encode(), "text/plain; charset=utf-8")
                if url.path.startswith("/liseuse/") and url.path[9:] in PAQUET:
                    return self.envoyer((PUBLIE / url.path[9:]).read_bytes(), "text/plain; charset=utf-8")
                if url.path == "/etat.txt" and not self.autorise():  # sans jeton : l'heure et la version, aucun écran
                    utc = dt.datetime.now(dt.timezone.utc)
                    ligne = f"- - 0 0 0 {utc:%Y.%m.%d-%H:%M:%S} {int(utc.timestamp())} {paquet()[1]} -\n"
                    return self.envoyer(ligne.encode(), "text/plain; charset=utf-8")
                if not self.autorise():
                    return self.send_error(403)
                if url.path == "/liseuse/commande.sh" and (sortie / "commande.sh").exists():
                    return self.envoyer((sortie / "commande.sh").read_bytes(), "text/plain; charset=utf-8")
                if url.path.startswith("/pousse/") and re.fullmatch(r"[0-9a-f]{32}", url.path[8:]):
                    return self.envoyer((sortie / "pousse" / url.path[8:]).read_bytes(), "application/octet-stream")
                if url.path == "/retour" and q.get("id") == commande_en_cours(sortie) and q.get("n", "").isdigit():
                    self.retour(q)
                    return self.envoyer(b"ok\n", "text/plain; charset=utf-8")
                if url.path not in ("/etat.txt", "/ecran.png"):
                    return self.send_error(404)
                etat = json.loads((sortie / "etat.json").read_text(encoding="utf-8"))
                if url.path == "/ecran.png":
                    if q.get("e") in annonces:
                        return self.envoyer(annonces[q["e"]][1 if q.get("hl") else 0], "image/png")
                    ecran = q.get("p") or ecran_servi(etat, None)[0]
                    if ecran not in etat["navigation"]:
                        return self.send_error(404)
                    fichier = sortie / f"ecran-{ecran}{'-hl' if q.get('hl') else ''}.png"
                    return self.envoyer(fichier.read_bytes(), "image/png")
                pas = min(int(q["pas"]), 50) if q.get("pas", "").isdigit() and q["pas"] != "0" else 1
                ecran, manuel = ecran_servi(etat, q.get("nav"), pas)
                hl = sortie / f"ecran-{ecran}-hl.png"
                vieux = time.time() - (sortie / "etat.json").stat().st_mtime > PERIME and hl.exists()
                if vieux != perime["note"]:
                    note("écrans périmés : servis en « HORS LIGNE »" if vieux else "écrans de nouveau à jour")
                    perime["note"] = vieux
                image = (hl if vieux else sortie / f"ecran-{ecran}.png").read_bytes()
                empreinte = hashlib.sha1(image).hexdigest()[:12]
                flash = etat["flash"].get(ecran, 0)
                flash = 1 if manuel and flash == 0 else flash  # écran choisi aux boutons : toujours net
                if q.get("v") == "2":
                    image_hl = hl.read_bytes() if hl.exists() else b""
                    if len(annonces) > 50:
                        annonces.clear()
                    annonces[empreinte] = (image, image_hl)
                    utc = dt.datetime.now(dt.timezone.utc)
                    ligne = (f"{empreinte} {ecran} {flash} {len(image)} {len(image_hl)} "
                             f"{utc:%Y.%m.%d-%H:%M:%S} {int(utc.timestamp())} {paquet()[1]} {commande_en_cours(sortie)}\n")
                else:
                    ligne = f"{empreinte} {ecran} {flash}\n"
                self.envoyer(ligne.encode(), "text/plain; charset=utf-8")
                self.battement(q, ecran)
            except ConnectionError:  # la liseuse a raccroché : rien à lui répondre
                return
            except (OSError, ValueError, KeyError) as e:  # fichier en cours de régénération, etat.json absent…
                note(f"{self.path} : {type(e).__name__} {e}")
                self.send_error(503)

        def retour(self, q):
            """Un morceau de la sortie d'une commande, assemblé à la requête `fin=1` : une ligne de texte (`t`, encodée
            par le sed de la liseuse, accents laissés bruts) ou des octets en octal (`o`, 3 chiffres chacun)."""
            dossier = sortie / "commandes"
            dossier.mkdir(exist_ok=True)
            if "t" in q:  # relu en octets depuis la requête brute : http.server l'a décodée en latin-1
                brut = self.path.encode("latin-1").partition(b"?")[2]  # urlparse refuse les octets non ASCII
                t = next((v for k, _, v in (x.partition(b"=") for x in brut.split(b"&")) if k == b"t"), b"")
                octets = urllib.parse.unquote_to_bytes(t) + b"\n"
            else:
                chiffres = re.sub(r"[^0-7]", "", q.get("o", ""))
                octets = bytes(int(chiffres[i:i + 3], 8) & 255 for i in range(0, len(chiffres) - 2, 3))
            (dossier / f"{q['id']}.{int(q['n']):05d}").write_bytes(octets)
            if q.get("fin") == "1":
                morceaux = sorted(dossier.glob(f"{q['id']}.[0-9]*"))
                tmp = dossier / f"{q['id']}.txt.tmp"
                tmp.write_bytes(b"".join(m.read_bytes() for m in morceaux))
                tmp.replace(dossier / f"{q['id']}.txt")
                for m in morceaux:
                    m.unlink()

        def battement(self, q, ecran):
            if q.get("nav"):
                choix["touche"] = {"quand": dt.datetime.now().isoformat(timespec="seconds"), "sens": q["nav"],
                                   "code": q.get("touche", "")}
            horloge = q.get("horloge", "")
            vu = {"vu": dt.datetime.now().isoformat(timespec="seconds"), "adresse": self.client_address[0],
                  "batterie": q.get("batterie", ""), "ecran": ecran, "version": q.get("version", ""),
                  "ecart_horloge_s": int(horloge) - int(time.time()) if horloge.isdigit() else None,
                  "derniere_touche": choix["touche"]}
            tmp = sortie / "liseuse.json.tmp"
            tmp.write_text(json.dumps(vu, ensure_ascii=False) + "\n", encoding="utf-8")
            tmp.replace(sortie / "liseuse.json")

        def log_message(self, *a):
            pass

    return Gestionnaire


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--sortie", type=Path, default=Path.home() / "Library/Caches/kindle-dashboard")
    args = ap.parse_args()
    args.sortie.mkdir(parents=True, exist_ok=True)
    global JETON, PUBLIE
    from dashboard import lire_env
    PUBLIE = args.sortie / "publie"
    JETON = lire_env("KINDLE_JETON")
    threading.Thread(target=regenerer, args=(args.sortie,), daemon=True).start()
    threading.Thread(target=ejecter, args=(args.sortie,), daemon=True).start()
    note(f"serveur sur le port {args.port}, sortie {args.sortie}, scripts {paquet()[1]}, jeton {'exigé' if JETON else 'non exigé'}")
    http.server.ThreadingHTTPServer(("0.0.0.0", args.port), gestionnaire(args.sortie)).serve_forever()


if __name__ == "__main__":
    main()
