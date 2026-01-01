#!/usr/bin/env python3
"""autoriser.py : à lancer UNE fois : autorisation Google en lecture seule (mails + agenda) pour le dashboard.

Ouvre la page de consentement Google ; on clique « Autoriser ». Le jeton de rafraîchissement est écrit dans le
.env (le plus proche en remontant les dossiers, GOOGLE_KINDLE_REFRESH_TOKEN), jamais affiché. Client OAuth de type
« Desktop » : GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET du même .env (autres noms : clé google_client de config.json).
Bibliothèque standard seule.
"""
import base64
import hashlib
import http.server
import json
import secrets
import socketserver
import sys
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path

ICI = Path(__file__).resolve().parent
ENV = next((d / ".env" for d in (ICI, *ICI.parents) if (d / ".env").is_file()), ICI / ".env")
SCOPES = "https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/calendar.readonly"
NOM = "GOOGLE_KINDLE_REFRESH_TOKEN"
CONFIG = next((json.loads((ICI / n).read_text(encoding="utf-8")) for n in ("config.json", "config.exemple.json")
               if (ICI / n).is_file()), {})
CLIENT = CONFIG.get("google_client", ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"])


def lire_env(nom):
    if not ENV.is_file():
        return ""
    for l in ENV.read_text(encoding="utf-8").splitlines():
        if l.startswith(nom + "="):
            return l.split("=", 1)[1].strip().strip("'\"")
    return ""


def ecrire_env(nom, valeur):
    lignes = ENV.read_text(encoding="utf-8").splitlines() if ENV.is_file() else []
    lignes = [l for l in lignes if not l.startswith(nom + "=")] + [f"{nom}={valeur}"]
    tmp = ENV.with_name(".env.tmp")  # atomique : le .env sert à tout le dossier, jamais tronqué
    tmp.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    tmp.chmod(ENV.stat().st_mode & 0o777 if ENV.is_file() else 0o600)
    tmp.replace(ENV)


def main():
    client, secret = lire_env(CLIENT[0]), lire_env(CLIENT[1])
    if not client or not secret:
        raise SystemExit(f"{CLIENT[0]} / {CLIENT[1]} absents du .env")
    verif = secrets.token_urlsafe(64)
    defi = base64.urlsafe_b64encode(hashlib.sha256(verif.encode()).digest()).rstrip(b"=").decode()
    etat = secrets.token_urlsafe(16)
    recu = {}

    class Retour(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = dict(urllib.parse.parse_qsl(urllib.parse.urlparse(self.path).query))
            if "code" in q or "error" in q:
                recu.update(q)
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write("<p>C'est fait, tu peux fermer cet onglet.</p>".encode())

        def log_message(self, *a):
            pass

    with socketserver.TCPServer(("127.0.0.1", 0), Retour) as srv:
        retour = f"http://127.0.0.1:{srv.server_address[1]}"
        url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
            "client_id": client, "redirect_uri": retour, "response_type": "code", "scope": SCOPES,
            "access_type": "offline", "prompt": "consent", "state": etat,
            "code_challenge": defi, "code_challenge_method": "S256"})
        print("Page de consentement Google (lien à ouvrir si le navigateur ne s'ouvre pas) :\n" + url, flush=True)
        if "--sans-navigateur" not in sys.argv:
            webbrowser.open(url)
        while "code" not in recu and "error" not in recu:
            srv.handle_request()
    if recu.get("state") != etat or "code" not in recu:
        raise SystemExit(f"autorisation refusée ou invalide : {recu.get('error', 'état différent')}")
    donnees = urllib.parse.urlencode({"code": recu["code"], "client_id": client, "client_secret": secret,
                                      "redirect_uri": retour, "grant_type": "authorization_code",
                                      "code_verifier": verif}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", donnees, timeout=30) as r:
        jeton = json.loads(r.read())
    if not jeton.get("refresh_token"):
        raise SystemExit("Google n'a pas rendu de jeton de rafraîchissement")
    ecrire_env(NOM, jeton["refresh_token"])
    print(f"{NOM} écrit dans le .env (valeur non affichée).")


if __name__ == "__main__":
    main()
