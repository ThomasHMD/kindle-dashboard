#!/usr/bin/env python3
"""dashboard.py : fabrique les écrans du Kindle-dashboard (v3, paysage) : colonne météo fixe + panneau tournant.

Disposition d'après RECHERCHE-DESIGN.md §6 : à gauche la météo (304 px) ; à droite un panneau (448 px) qui tourne
entre Agenda, Courrier et Abonnés, et « Demain » la nuit. Des écrans pleins s'intercalent : Météo (la journée et
la semaine), le plus long, Citation, et depuis le 01/01/2026 Dessin du jour, Lumière du
jour, Livre à lire, Mot du jour et Mes stations ; la veille du ramassage, un rappel des poubelles dans le bandeau.
Rassemble les données (Open-Meteo sans clé, Gmail et Google Agenda en lecture seule, table n8n `social_daily` pour
les abonnés, citations du jour de Wikiquote, Notion pour les concepts de dessin et la bibliothèque, Cleveland Museum
of Art en CC0, Wiktionnaire, ilévia en temps réel et GTFS), remplit gabarit.html, photographie un écran par panneau
avec Chromium
(Playwright) à la taille exacte de la liseuse, le passe en PNG 8 bits 16 niveaux de gris et le tourne dans le
sens natif de la dalle (portrait) : le format que la liseuse affiche tel quel avec `eips -g`.

    python3 dashboard.py                    # Kindle 4 / 5 / Touch (800 × 600 en paysage)
    python3 dashboard.py --modele pw1       # Paperwhite 1 (1024 × 758)
    python3 dashboard.py --rotation 270     # liseuse posée dans l'autre sens
    python3 dashboard.py --sortie <dossier> # défaut : ~/Library/Caches/kindle-dashboard (hors synchro)

Sorties : apercu-<panneau>.png (paysage, pour l'œil), ecran-<panneau>.png (tourné, pour la liseuse), ecran.png
(celui que la PLAYLIST désigne maintenant) et etat.json (panneau du moment, empreinte et flash de chaque écran,
ordre des écrans pour les boutons) dont serveur.py tire la ligne etat.txt que lit la liseuse.

Jetons : GOOGLE_KINDLE_REFRESH_TOKEN (gmail.readonly + calendar.readonly, créé par autoriser.py) ; à défaut, le
courrier retombe sur GOOGLE_GMAIL_REFRESH_TOKEN et l'agenda sur agenda-maquette.json du dossier de sortie s'il
existe. N8N_API_KEY pour les abonnés. Une source en panne n'empêche jamais un écran de sortir.
"""
import argparse
import datetime as dt
import hashlib
import html
import io
import json
import math
import os
import re
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

ICI = Path(__file__).resolve().parent
# Le .env le plus proche en remontant les dossiers (variables d'environnement prioritaires, voir lire_env) ; aucun
# pour demo.py (KINDLE_DEMO).
ENV = None if os.environ.get("KINDLE_DEMO") else next((d / ".env" for d in (ICI, *ICI.parents) if (d / ".env").is_file()), None)
# Réglages propres à l'installation (lieu, agendas, stations, bases Notion…) : config.json à côté de ce script,
# jamais publié ; à défaut, le modèle config.exemple.json.
CONFIG = next((json.loads((ICI / n).read_text(encoding="utf-8")) for n in ("config.json", "config.exemple.json")
               if (ICI / n).is_file()), {})
PARIS = ZoneInfo("Europe/Paris")
LIEU = CONFIG.get("lieu", {"nom": "Paris", "lat": 48.8566, "lon": 2.3522})
MODELES = {"k4": (600, 800), "k5": (600, 800), "touch": (600, 800), "pw1": (758, 1024)}  # natif, portrait
# Rotation par plage horaire (RECHERCHE-DESIGN.md §3.3, revue le 01/01/2026) : (début, fin, [(écran, secondes)]).
# Écrans conditionnels, retirés du cycle quand ils n'ont rien à dire (plage_du_moment, `sauf`) : courrier sans mail
# important, stations hors de leurs créneaux (STATIONS_CRENEAUX) et des 2 h avant une sortie, lumière hors des heures photo.
PLAYLIST = {
    "matin": ("06:30", "09:00", [("meteo", 360), ("stations", 360), ("agenda", 360), ("lumiere", 300), ("courrier", 240),
                                 ("air", 180), ("mot", 240), ("citation", 180)]),
    "journee": ("09:00", "19:00", [("meteo", 480), ("agenda", 360), ("courrier", 300), ("reseaux", 240), ("air", 240), ("stations", 360),
                                   ("dessin", 360), ("lumiere", 360), ("livre", 240), ("mot", 240), ("citation", 180)]),
    "soiree": ("19:00", "23:00", [("meteo", 300), ("stations", 360), ("agenda", 240), ("dessin", 480), ("livre", 360),
                                  ("mot", 240), ("citation", 180)]),
    "nuit": ("23:00", "06:30", [("demain", 1800)]),
}
IMMINENT = 45  # minutes avant une sortie : l'écran Stations reste affiché, la rotation s'arrête
PLEIN = ("meteo", "air", "citation", "stations", "lumiere", "dessin", "livre", "mot")  # écrans sans la colonne météo
# Flash complet en arrivant sur un écran (les écrans conditionnels changent l'enchaînement : une disposition peut en
# suivre une autre n'importe où) ; partiel pour la mise à jour d'un écran qui reste.
COMPLET_A = ("meteo", "air", "agenda", "courrier", "reseaux", "stations", "lumiere", "dessin", "livre", "mot", "citation", "demain")
NAVIGATION = ["meteo", "air", "agenda", "courrier", "reseaux", "stations", "lumiere", "dessin", "livre", "mot", "citation",
              "demain"]  # ordre des boutons de la liseuse
RETIRAGE = 13  # heure du second tirage du jour : dessin, livre, mot et citation changent pour l'après-midi
AGENDAS = CONFIG.get("agendas", {"primary": "Agenda"})  # calendarId → libellé
SORTIES = tuple(CONFIG.get("agendas_sorties", []))  # agendas où un rendez-vous veut dire sortir (écran Stations)
PAS_UNE_SORTIE = CONFIG.get("pas_une_sortie", "sport|salle")  # rendez-vous pour lesquels on ne prend pas le tram
# Créneaux fixes de l'écran Stations : [{"jour": 0 (lundi), "de": "06:00", "a": "10:00", "texte": "LUNDI : TRAVAIL"}].
STATIONS_CRENEAUX = CONFIG.get("stations_creneaux", [])
# Veille du ramassage des poubelles, par jour de la semaine (0 = lundi) : texte du rappel dans le bandeau.
POUBELLES = {int(k): v for k, v in CONFIG.get("poubelles", {}).items()}
UA_WIKI = {"User-Agent": f"kindle-dashboard/1.0 ({CONFIG.get('contact', 'https://github.com/ThomasHMD/kindle-dashboard')})"}  # politique Wikimedia
NOTION = CONFIG.get("notion", {})
CONCEPTS = NOTION.get("concepts", "")          # base des concepts de dessin (data source), jeton NOTION_TOKEN ;
                                               # sans elle, les concepts de consignes-dessin.json
BIBLIOTHEQUE = NOTION.get("bibliotheque", "")  # bibliothèque de livres (data source)
JETON_BIBLIOTHEQUE = NOTION.get("jeton_bibliotheque", "NOTION_TOKEN")
CLIENT_GOOGLE = CONFIG.get("google_client", ["GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"])  # variables du .env, client « Desktop »
AIR = "https://air-quality-api.open-meteo.com/v1/air-quality"
# Indice européen (EAQI) : plafond du niveau, nom, conseil.
NIVEAUX_AIR = ((20, "BON", "Rien à signaler, on peut tout ouvrir."), (40, "CORRECT", "Aucune précaution à prendre."),
               (60, "MOYEN", "Personnes sensibles : moins de sport dehors."), (80, "MAUVAIS", "Éviter le sport intense dehors."),
               (100, "TRÈS MAUVAIS", "Pas d'effort dehors, fenêtres fermées."),
               (math.inf, "EXTRÊME", "Rester dedans, fenêtres fermées."))
POLLUANTS = (("pm2_5", "PARTICULES PM2.5", "les plus fines : chauffage, trafic"), ("pm10", "PARTICULES PM10", "combustion, poussières"),
             ("nitrogen_dioxide", "DIOXYDE D'AZOTE", "surtout le trafic"), ("ozone", "OZONE", "soleil sur la pollution, l'été"))
POLLENS = {"alder_pollen": "aulne", "birch_pollen": "bouleau", "grass_pollen": "graminées", "mugwort_pollen": "armoise",
           "olive_pollen": "olivier", "ragweed_pollen": "ambroisie"}
CLEVELAND = "https://openaccess-api.clevelandart.org/api/artworks/"
FAMILLES = {  # famille de la consigne → requêtes Cleveland (une par jour, tirée au sort)
    "valeurs": [{"technique": "chalk"}, {"technique": "charcoal"}, {"technique": "wash"}],
    "trait": [{"technique": "pen"}, {"technique": "graphite"}],
    "construction": [{"q": "figure study"}, {"q": "study"}],
    "perspective": [{"q": "view of"}],
    "portrait": [{"q": "head"}],
    "mains": [{"q": "hand"}],
}
TECHNIQUES_OK = ("graphite", "chalk", "pen", "ink", "charcoal", "crayon", "pencil", "wash", "stylus", "metalpoint")
TECHNIQUES_NON = ("watercolor", "gouache", "oil", "pastel", "tempera", "colored")
ILEVIA_DIRECT = "https://data.lillemetropole.fr/geoserver/ogc/features/v1/collections/dsp_ilevia:prochains_passages/items"
ILEVIA_GTFS = "https://media.ilevia.fr/opendata/gtfs.zip"
# Stations du réseau ilévia (Lille). parent : stop_id de la station dans le GTFS ; ligne : route_id ; sens :
# direction_id voulue ; direct : [nom_station, sens_ligne] du temps réel ilévia (le métro n'y est pas) ; vers : où
# va ce sens, en clair (« LILLE »).
STATIONS = CONFIG.get("stations", [])
SOCIAL_DAILY = CONFIG.get("abonnes", "")  # table n8n des relevés quotidiens d'abonnés (API data-tables)
# Écrans sans réglage, ou retirés dans la config : hors des boutons et de la rotation.
INACTIFS = set(CONFIG.get("ecrans_retires", [])) | {e for e, manque in (
    ("stations", not STATIONS), ("livre", not BIBLIOTHEQUE), ("reseaux", not SOCIAL_DAILY)) if manque}
NAVIGATION = [e for e in NAVIGATION if e not in INACTIFS]
RESEAUX = {"youtube": "YOUTUBE", "instagram": "INSTAGRAM", "facebook": "FACEBOOK", "tiktok": "TIKTOK", "threads": "THREADS"}
JOURS = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]
JOURS_COURTS = ["LUN.", "MAR.", "MER.", "JEU.", "VEN.", "SAM.", "DIM."]
MOIS_COURTS = ["JANV.", "FÉVR.", "MARS", "AVRIL", "MAI", "JUIN", "JUIL.", "AOÛT", "SEPT.", "OCT.", "NOV.", "DÉC."]
MOIS = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE",
        "NOVEMBRE", "DÉCEMBRE"]
WMO = {0: "Ciel dégagé", 1: "Plutôt dégagé", 2: "Éclaircies", 3: "Couvert", 45: "Brouillard", 48: "Brouillard givrant",
       51: "Bruine légère", 53: "Bruine", 55: "Bruine dense", 56: "Bruine verglaçante", 57: "Bruine verglaçante",
       61: "Pluie faible", 63: "Pluie", 65: "Forte pluie", 66: "Pluie verglaçante", 67: "Pluie verglaçante",
       71: "Neige faible", 73: "Neige", 75: "Forte neige", 77: "Grains de neige", 80: "Averses faibles",
       81: "Averses", 82: "Fortes averses", 85: "Averses de neige", 86: "Fortes averses de neige", 95: "Orage",
       96: "Orage et grêle", 99: "Orage et grêle"}


def lire_env(nom):
    if os.environ.get(nom):
        return os.environ[nom]
    try:
        for l in ENV.read_text(encoding="utf-8").splitlines():
            if l.startswith(nom + "="):
                return l.split("=", 1)[1].strip().strip("'\"")
    except (OSError, AttributeError):  # AttributeError : pas de .env
        pass
    return ""


def appel(url, entetes=None, donnees=None):
    req = urllib.request.Request(url, data=donnees, headers={"User-Agent": "kindle-dashboard", **(entetes or {})})
    with urllib.request.urlopen(req, timeout=8) as r:  # court : les sources s'enchaînent, le tout borné à 110 s
        return json.load(r)


def plage_du_moment(maintenant, sauf=()):
    """(nom de la plage, panneau du moment, rang dans le cycle). La plage nuit enjambe minuit. Les écrans de `sauf`
    (rien à montrer) sortent du cycle, qui raccourcit d'autant."""
    minutes = maintenant.hour * 60 + maintenant.minute
    for nom, (debut, fin, liste) in PLAYLIST.items():
        liste = [x for x in liste if x[0] not in sauf] or liste
        d, f = (int(x[:2]) * 60 + int(x[3:]) for x in (debut, fin))
        if (d <= minutes < f) if d < f else (minutes >= d or minutes < f):
            ecoule = ((minutes - d) % 1440) * 60 + maintenant.second
            t = ecoule % sum(s for _, s in liste)
            for rang, (panneau, duree) in enumerate(liste):
                if t < duree:
                    return nom, panneau, rang
                t -= duree
    return "journee", "agenda", 0


# ── icônes pixel (grille 16 × 16, 1 = encre, 2 = tramé) ─────────────────────────────────────────────

def _grille():
    return [[0] * 16 for _ in range(16)]


def _disque(g, cx, cy, r, val):
    for y in range(16):
        for x in range(16):
            if (x + .5 - cx) ** 2 + (y + .5 - cy) ** 2 <= r * r:
                g[y][x] = val


def _soleil(g, cx, cy, r):
    _disque(g, cx, cy, r, 2)
    for y in range(16):  # contour plein
        for x in range(16):
            d = math.hypot(x + .5 - cx, y + .5 - cy)
            if r - 1 < d <= r:
                g[y][x] = 1
    for k in range(8):  # rayons
        a = k * math.pi / 4
        for t in (r + 1.6, r + 2.6):
            x, y = int(cx + t * math.cos(a)), int(cy + t * math.sin(a))
            if 0 <= x < 16 and 0 <= y < 16:
                g[y][x] = 1


def _nuage(g, dx=0, dy=0):
    def dedans(x, y):
        x, y = x + .5 - dx, y + .5 - dy
        return ((x - 5) ** 2 + (y - 9.5) ** 2 <= 9 or (x - 9) ** 2 + (y - 7.5) ** 2 <= 14 or
                (x - 12.5) ** 2 + (y - 10) ** 2 <= 6.5 or (2.5 <= x <= 14.5 and 9.5 <= y <= 12.5))
    for y in range(16):
        for x in range(16):
            if dedans(x, y):
                bord = any(not dedans(x + a, y + b) for a, b in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                g[y][x] = 1 if bord else 0


def _lune(g, cx, cy, r, age):
    """Lune avec sa phase réelle : partie éclairée blanche, partie dans l'ombre tramée."""
    k = math.cos(2 * math.pi * age / 29.530588853)
    for y in range(16):
        for x in range(16):
            u, v = (x + .5 - cx) / r, (y + .5 - cy) / r
            if u * u + v * v > 1:
                continue
            w = math.sqrt(max(0, 1 - v * v))
            eclaire = u >= k * w if age < 14.765 else u <= -k * w
            bord = (u * u + v * v) > (1 - 1.6 / r)
            g[y][x] = 1 if bord else (0 if eclaire else 2)


def icone(nom, taille, age_lune=7.0):
    g = _grille()
    if nom == "soleil":
        _soleil(g, 8, 8, 4)
    elif nom == "lune":
        _lune(g, 8, 8, 6, age_lune)
    elif nom == "eclaircies":
        _soleil(g, 5.5, 5.5, 3)
        _nuage(g, 1, 1.5)
    elif nom == "eclaircies-nuit":
        _lune(g, 5.5, 5.5, 4, age_lune)
        _nuage(g, 1, 1.5)
    elif nom == "nuage":
        _nuage(g, 0, 0)
    elif nom == "enveloppe":
        for x in range(1, 15):
            g[3][x] = g[12][x] = 1
        for y in range(3, 13):
            g[y][1] = g[y][14] = 1
        for i in range(7):  # le rabat
            g[3 + i][1 + i] = g[3 + i][14 - i] = 1
    elif nom == "poubelle":
        for x in range(2, 14):
            g[3][x] = 1
        for x in range(6, 10):
            g[1][x] = 1
        g[2][6] = g[2][9] = 1
        for y in range(4, 15):
            g[y][3] = g[y][12] = 1
        for x in range(3, 13):
            g[14][x] = 1
        for y in range(6, 13):
            g[y][6] = g[y][9] = 1
    elif nom == "brouillard":
        for y, (a, b) in zip((4, 7, 10, 13), ((2, 13), (4, 15), (1, 11), (5, 14))):
            for x in range(a, b):
                g[y][x] = 1 if (x - a) % 5 != 4 else 0
    elif nom in ("pluie", "neige", "orage"):
        _nuage(g, 0, -3)
        if nom == "pluie":
            for x0 in (4, 8, 12):
                for i in range(3):
                    if 0 <= x0 - i < 16:
                        g[11 + i + (x0 % 2)][x0 - i] = 1
        elif nom == "neige":
            for x, y in ((4, 12), (8, 11), (12, 12), (6, 14), (10, 14)):
                g[y][x] = 1
        else:
            for x, y in ((9, 10), (8, 11), (7, 12), (8, 12), (9, 12), (8, 13), (7, 14), (6, 15)):
                g[y][x] = 1
    rects = []
    for y in range(16):
        for x in range(16):
            if g[y][x] == 1 or (g[y][x] == 2 and (x + y) % 2 == 0):
                rects.append(f'<rect x="{x}" y="{y}" width="1" height="1"/>')
    return (f'<svg class="px" width="{taille}" height="{taille}" viewBox="0 0 16 16" '
            f'xmlns="http://www.w3.org/2000/svg">{"".join(rects)}</svg>')


def nom_icone(code, jour):
    if code == 0:
        return "soleil" if jour else "lune"
    if code in (1, 2):
        return "eclaircies" if jour else "eclaircies-nuit"
    if code == 3:
        return "nuage"
    if code in (45, 48):
        return "brouillard"
    if code >= 95:
        return "orage"
    if 71 <= code <= 77 or code in (85, 86):
        return "neige"
    return "pluie"


# ── sources ──────────────────────────────────────────────────────────────────────────────────────

def meteo(maintenant):
    q = urllib.parse.urlencode({
        "latitude": LIEU["lat"], "longitude": LIEU["lon"], "timezone": "Europe/Paris", "forecast_days": 7,
        "wind_speed_unit": "kmh",
        "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m,wind_direction_10m,is_day",
        "hourly": "temperature_2m,precipitation_probability,weather_code,is_day",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,sunrise,sunset,precipitation_probability_max"})
    d = appel("https://api.open-meteo.com/v1/forecast?" + q)
    c, h, j = d["current"], d["hourly"], d["daily"]
    rose = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"][round(c["wind_direction_10m"] / 45) % 8]
    debut = maintenant.replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)

    def creneaux(pas, nombre):  # `nombre` créneaux, toutes les `pas` heures à partir de l'heure qui vient
        out = []
        for i, t in enumerate(h["time"]):
            ecart = (dt.datetime.fromisoformat(t).replace(tzinfo=PARIS) - debut).total_seconds() // 3600
            if ecart >= 0 and ecart % pas == 0 and len(out) < nombre:
                out.append({"h": f"{int(t[11:13])}H", "t": round(h["temperature_2m"][i]),
                            "p": h["precipitation_probability"][i] or 0,
                            "icone": nom_icone(h["weather_code"][i], h["is_day"][i])})
        return out
    return {"temp": round(c["temperature_2m"]), "ressenti": round(c["apparent_temperature"]),
            "libelle": WMO.get(c["weather_code"], "?"), "icone": nom_icone(c["weather_code"], c["is_day"]),
            "min": round(j["temperature_2m_min"][0]), "max": round(j["temperature_2m_max"][0]),
            "vent": round(c["wind_speed_10m"]), "rose": rose, "pluie": j["precipitation_probability_max"][0] or 0,
            "lever": j["sunrise"][0][-5:], "coucher": j["sunset"][0][-5:], "creneaux": creneaux(3, 4),
            "heures": creneaux(2, 6),
            "demain": {"icone": nom_icone(j["weather_code"][1], 1), "min": round(j["temperature_2m_min"][1]),
                       "max": round(j["temperature_2m_max"][1])},
            "jours": [{"date": j["time"][n], "icone": nom_icone(j["weather_code"][n], 1),
                       "min": round(j["temperature_2m_min"][n]), "max": round(j["temperature_2m_max"][n]),
                       "pluie": j["precipitation_probability_max"][n] or 0} for n in range(len(j["time"]))]}


def jeton_google(nom_jeton):
    refresh = lire_env(nom_jeton)
    if not refresh:
        return None
    d = urllib.parse.urlencode({"client_id": lire_env(CLIENT_GOOGLE[0]), "client_secret": lire_env(CLIENT_GOOGLE[1]),
                                "refresh_token": refresh, "grant_type": "refresh_token"}).encode()
    return appel("https://oauth2.googleapis.com/token", donnees=d)["access_token"]


def latin(t):
    """Garde ce que les polices pixel savent dessiner : latin et ponctuation typographique (pas de « 回复 »)."""
    t = "".join(ch for ch in t if ord(ch) < 0x250 or ch in "–—‘’“”„…•€«» ")
    return re.sub(r"\s+", " ", t).strip(" :")


def courrier(maintenant):
    jeton = jeton_google("GOOGLE_KINDLE_REFRESH_TOKEN") or jeton_google("GOOGLE_GMAIL_REFRESH_TOKEN")
    if not jeton:
        return {"erreur": "Gmail : autorisation à donner"}
    h = {"Authorization": "Bearer " + jeton}
    base = "https://gmail.googleapis.com/gmail/v1/users/me/"
    boite = appel(base + "labels/INBOX", h)
    # Seulement les non-lus que Gmail marque « Important » : rien de nouveau = rien à montrer.
    q = urllib.parse.urlencode({"q": "in:inbox is:unread is:important", "maxResults": 100})
    liste = appel(base + f"messages?{q}", h).get("messages", [])
    derniers = []
    for m in liste[:5]:
        msg = appel(base + f"messages/{m['id']}?format=metadata&metadataHeaders=From&metadataHeaders=Subject", h)
        en = {x["name"]: x["value"] for x in msg["payload"]["headers"]}
        de = en.get("From", "?")
        de = re.sub(r'\s*<.*>$', "", de).strip('" ') or de.split("@")[0]
        recu = dt.datetime.fromtimestamp(int(msg["internalDate"]) / 1000, PARIS)
        ecart = (maintenant.date() - recu.date()).days
        quand = recu.strftime("%H:%M") if ecart == 0 else "hier" if ecart == 1 else recu.strftime("%d/%m")
        derniers.append({"de": latin(de) or "?", "sujet": latin(en.get("Subject", "")) or "(sans objet)", "quand": quand,
                         "non_lu": "UNREAD" in msg.get("labelIds", [])})
    return {"importants": len(liste), "non_lus": boite.get("messagesUnread", 0), "derniers": derniers}


def agenda(maintenant, sortie):
    jeton = jeton_google("GOOGLE_KINDLE_REFRESH_TOKEN")
    debut = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    fin = debut + dt.timedelta(days=2)
    evenements = []
    if jeton:
        h = {"Authorization": "Bearer " + jeton}
        for cal in AGENDAS:
            q = urllib.parse.urlencode({"timeMin": debut.isoformat(), "timeMax": fin.isoformat(), "singleEvents": "true",
                                        "orderBy": "startTime", "maxResults": 20, "timeZone": "Europe/Paris"})
            for e in appel(f"https://www.googleapis.com/calendar/v3/calendars/{urllib.parse.quote(cal)}/events?{q}", h).get("items", []):
                evenements.append({**e, "_agenda": AGENDAS[cal]})
    elif (sortie / "agenda-maquette.json").exists():
        evenements = json.loads((sortie / "agenda-maquette.json").read_text(encoding="utf-8"))
    else:
        return {"erreur": "Agenda : autorisation à donner"}
    jours = [[], []]  # liste, pas dict : le cache JSON changerait les clés 0 et 1 en texte
    for e in evenements:
        if e.get("status") == "cancelled":
            continue
        s, f = e["start"], e["end"]
        if "dateTime" in s:
            d0, d1 = dt.datetime.fromisoformat(s["dateTime"]).astimezone(PARIS), dt.datetime.fromisoformat(f["dateTime"]).astimezone(PARIS)
            heure = d0.strftime("%H:%M")
        else:
            d0 = dt.datetime.fromisoformat(s["date"]).replace(tzinfo=PARIS)
            d1 = dt.datetime.fromisoformat(f["date"]).replace(tzinfo=PARIS)
            heure = "JOUR"
        for n in (0, 1):
            jour = debut + dt.timedelta(days=n)
            if d0 < jour + dt.timedelta(days=1) and d1 > jour:
                jours[n].append({"heure": heure if d0 >= jour else "suite", "cle": d0.isoformat(),
                                 "titre": latin(e.get("summary", "")) or "(sans titre)",
                                 "lieu": latin((e.get("location") or "").split(",")[0]), "passe": d1 <= maintenant,
                                 "agenda": e.get("_agenda", "")})
    for n in (0, 1):
        vus, propres = set(), []
        for x in sorted(jours[n], key=lambda x: (x["heure"] not in ("JOUR", "suite"), x["cle"])):
            if (x["titre"], x["cle"]) not in vus:  # même événement visible dans deux agendas
                vus.add((x["titre"], x["cle"]))
                propres.append(x)
        jours[n] = propres
    return {"jours": jours}


def reseaux(maintenant):
    """Abonnés par réseau, relevés chaque jour par un workflow n8n dans une table (SOCIAL_DAILY)."""
    cle = lire_env("N8N_API_KEY")
    if not cle:
        return {"erreur": "N8N_API_KEY absente du .env"}
    q = urllib.parse.urlencode({"limit": 250, "sortBy": "date:desc"})
    lignes = appel(f"{SOCIAL_DAILY}?{q}", {"X-N8N-API-KEY": cle}).get("data", [])
    series = {}
    for l in lignes:
        if l.get("network") in RESEAUX and (l.get("followers") or 0) > 0:
            series.setdefault(l["network"], {})[l["date"]] = l["followers"]
    out = []
    for reseau in RESEAUX:  # ordre fixe : l'œil apprend la place de chaque ligne
        if reseau not in series:
            continue
        jours = series[reseau]
        dates = sorted(jours)[-31:]
        valeurs = [jours[d] for d in dates]
        cible = (dt.date.fromisoformat(dates[-1]) - dt.timedelta(days=7)).isoformat()
        avant = [jours[d] for d in dates if d <= cible]
        out.append({"nom": RESEAUX[reseau], "nb": valeurs[-1], "approx": reseau == "youtube",  # API YouTube arrondie
                    "d7": valeurs[-1] - avant[-1] if avant else None,
                    "gains": [b - a for a, b in zip(valeurs, valeurs[1:])]})
    return {"reseaux": out, "semaine": sum(x["d7"] or 0 for x in out)}


def air(maintenant):
    """Qualité de l'air heure par heure sur 3 jours (Open-Meteo, sans clé) : indice européen, sous-indice et teneur
    de chaque polluant, pollens (Europe, en saison)."""
    champs = ["european_aqi"] + [x for p, _, _ in POLLUANTS for x in (p, f"european_aqi_{p}")] + list(POLLENS)
    q = urllib.parse.urlencode({"latitude": LIEU["lat"], "longitude": LIEU["lon"], "hourly": ",".join(champs),
                                "timezone": "Europe/Paris", "forecast_days": 3})
    return appel(f"{AIR}?{q}")["hourly"]


def citation(maintenant):
    """Le matin, la citation du jour de Wikiquote si elle existe pour cette date ; sinon, et l'après-midi, une de la
    banque choisie d'après le tirage du moment."""
    banque = json.loads((ICI / "citations.json").read_text(encoding="utf-8"))
    jour = f"{maintenant.day} {MOIS[maintenant.month - 1].lower()} {maintenant.year}"
    du_jour = [q for q in banque if q["jour"] == jour]
    if du_jour and maintenant.hour < RETIRAGE:
        return du_jour[0]
    return banque[graine(maintenant) % len(banque)]


def lune(maintenant):
    return ((maintenant.astimezone(dt.timezone.utc) - dt.datetime(2000, 1, 6, 18, 14, tzinfo=dt.timezone.utc))
            .total_seconds() / 86400) % 29.530588853


def sur(source, *args):
    """Une source en panne donne un bloc d'erreur, jamais un écran manquant."""
    try:
        return source(*args)
    except Exception as e:  # noqa: BLE001
        print(f"⚠️ {source.__name__} : {type(e).__name__} {str(e)[:120]}", file=sys.stderr)
        return {"erreur": f"{source.__name__} indisponible"}


# ── écrans ───────────────────────────────────────────────────────────────────────────────────────

def esc(t):
    return html.escape(str(t))


def nombre(n):
    return f"{n:,}".replace(",", " ")


def signe(n):
    return "=" if n is None else (f"+{nombre(n)}" if n > 0 else (f"−{nombre(-n)}" if n < 0 else "±0"))


def meteo_actuelle(m, age):
    temp = str(m["temp"])
    libelle = m["libelle"].upper()
    return (f'<div class="heros">{icone(m["icone"], 80, age)}'
            f'<div class="temp{" long" if len(temp) > 2 else ""}">{temp}<i class="deg"></i></div></div>'
            f'<div class="etat {"s24" if len(libelle) <= 12 else "s16"} gras">{esc(libelle)}</div>'
            f'<div class="minmax"><span class="v50">{m["min"]}° / {m["max"]}°</span><span>ressenti {m["ressenti"]}°</span></div>'
            f'<div class="vent">vent {m["vent"]} km/h {m["rose"]} · pluie {m["pluie"]} %</div>')


def colonne_meteo(maintenant, m, age):
    if "erreur" in m:
        return f'<aside class="meteo"><p>{esc(m["erreur"])}</p></aside>'
    creneaux = "".join(
        f'<div class="cr"><span class="s24 gras">{x["h"]}</span>{icone(x["icone"], 32, age)}<span class="t">{x["t"]}°</span>'
        f'<span class="barre"><i class="tramee" style="width:{x["p"]}%"></i></span><span class="p">{x["p"]}%</span></div>'
        for x in m["creneaux"])
    dm = m["demain"]
    return (f'<aside class="meteo">{meteo_actuelle(m, age)}<div class="creneaux">{creneaux}</div>'
            f'<div class="demain"><span class="tag">DEMAIN</span>{icone(dm["icone"], 32, age)}'
            f'<span class="v50">{dm["min"]}°/{dm["max"]}°</span></div>'
            f'<div class="ephem s16"><span>{icone("soleil", 16)}{m["lever"]} › {m["coucher"]}</span>'
            f'<span>{icone("lune", 16, age)}J{maintenant.timetuple().tm_yday}</span></div></aside>')


def entete(titre, extra=""):
    return f'<div class="entete"><span class="tag">{titre}</span><span class="droite">{extra}</span></div>'


def rdv(x, grand):
    lieu = f'<span class="lieu coupe">{esc(x["lieu"])}</span>' if x["lieu"] and grand else ""
    return (f'<div class="rdv {"grand" if grand else "petit"}"><span>{esc(x["heure"])}</span>'
            f'<span class="coupe">{esc(x["titre"])}</span>{lieu}</div>')


def panneau_agenda(maintenant, a):
    out = [entete("AGENDA")]
    if "erreur" in a:
        return "".join(out) + f'<p>{esc(a["erreur"])}</p>'
    a_venir = [x for x in a["jours"][0] if not x["passe"]][:4]
    out.append('<div class="s16 gras rubrique">AUJOURD\'HUI</div>')
    if a_venir:
        out += [rdv(x, True) for x in a_venir]
    else:
        out.append("<p>Plus rien aujourd'hui</p>" if a["jours"][0] else "<p>Rien de prévu</p>")
    out.append('<div class="pointille"></div><div class="s16 gras rubrique">DEMAIN</div>')
    out += [rdv(x, False) for x in a["jours"][1][:5]] or ["<p>Rien de prévu</p>"]
    return "".join(out)


def panneau_demain(maintenant, a):
    out = [entete("DEMAIN")]
    if "erreur" in a:
        return "".join(out) + f'<p>{esc(a["erreur"])}</p>'
    lendemain = maintenant + dt.timedelta(days=1)
    out.append(f'<div class="s16 gras rubrique">{JOURS[lendemain.weekday()]} {lendemain.day} {MOIS[lendemain.month - 1]}</div>')
    out += [rdv(x, True) for x in a["jours"][1][:6]] or ["<p>Rien de prévu</p>"]
    return "".join(out)


def panneau_courrier(maintenant, c):
    out = [entete("COURRIER")]
    if "erreur" in c:
        return "".join(out) + f'<p>{esc(c["erreur"])}</p>'
    n = c["importants"]
    legende = "RIEN DE NEUF" if n == 0 else ("IMPORTANT" if n == 1 else "IMPORTANTS")
    sous_titre = f"sur {c['non_lus']} non lus" if n else "aucun important non lu"
    out.append(f'<div class="compte"><b>{"99+" if n >= 100 else n}</b><div><span class="s24 gras">{legende}</span>'
               f'<span>{sous_titre}</span></div></div><div class="double"></div>')
    for x in c["derniers"]:
        out.append(f'<div class="mail"><div class="ligne1"><i class="puce{" nl" if x["non_lu"] else ""}"></i>'
                   f'<span class="de s16 gras coupe">{esc(x["de"].upper())}</span><span>{esc(x["quand"])}</span></div>'
                   f'<div class="sujet coupe">{esc(x["sujet"])}</div></div>')
    return "".join(out)


def barres_gains(gains):
    haut, bas = max([g for g in gains if g > 0] or [0]), max([-g for g in gains if g < 0] or [0])
    total = (haut + bas) or 1
    part_haut = 100 * haut / total if haut else 100
    cols = []
    for g in gains:
        h = f'<i class="tramee" style="height:{100 * g / haut:.0f}%"></i>' if g > 0 else ""
        b = f'<i class="tramee" style="height:{100 * -g / bas:.0f}%"></i>' if g < 0 else ""
        cols.append(f'<div class="col"><div class="h" style="flex-basis:{part_haut:.0f}%">{h}</div>'
                    f'<div class="b" style="flex-basis:{100 - part_haut:.0f}%">{b}</div></div>')
    return f'<div class="gains">{"".join(cols)}</div>'


def panneau_reseaux(maintenant, r):
    if "erreur" in r:
        return entete("ABONNÉS") + f'<p>{esc(r["erreur"])}</p>'
    out = [entete("ABONNÉS", f'<span>{signe(r["semaine"])} cette semaine</span>')]
    for x in r["reseaux"]:
        nb = f'≈{x["nb"] / 1000:.1f} k'.replace(".", ",") if x["approx"] else nombre(x["nb"])
        out.append(f'<div class="reseau"><div class="haut"><span class="tag">{x["nom"]}</span>'
                   f'<span class="s16">{signe(x["d7"])} / 7 J</span></div>'
                   f'<div class="bas"><span class="nb">{nb}</span>{barres_gains(x["gains"])}</div></div>')
    return "".join(out)


def ecran_meteo(maintenant, m, age):
    """Écran plein : la météo du moment, la journée de 2 h en 2 h, puis les 7 jours."""
    if "erreur" in m:
        return entete("MÉTÉO") + f'<p>{esc(m["erreur"])}</p>'
    heures = "".join(
        f'<div class="h"><span class="s16 gras">{x["h"]}</span>{icone(x["icone"], 32, age)}<span class="v50">{x["t"]}°</span>'
        f'<span class="barre"><i class="tramee" style="width:{x["p"]}%"></i></span><span>{x["p"]} %</span></div>'
        for x in m["heures"])
    ephem = (f'<span class="astres s16">{icone("soleil", 16)}{m["lever"]} › {m["coucher"]}'
             f'{icone("lune", 16, age)}J{maintenant.timetuple().tm_yday}</span>')
    jours = []
    for n, x in enumerate(m["jours"]):
        d = dt.date.fromisoformat(x["date"])
        jours.append(f'<div class="j"><span class="{"tag" if n == 0 else "s16 gras"}">{JOURS[d.weekday()][:3]} {d.day}</span>'
                     f'{icone(x["icone"], 48, age)}<span class="v50">{x["max"]}°</span><span class="min">{x["min"]}°</span>'
                     f'<span class="barre"><i class="tramee" style="width:{x["pluie"]}%"></i></span><span>{x["pluie"]} %</span></div>')
    return (f'<div class="focus"><div class="actuel">{meteo_actuelle(m, age)}</div><div class="sep"></div>'
            f'<div class="journee">{entete("AUJOURD’HUI", ephem)}<div class="heures">{heures}</div></div></div>'
            f'<div class="double"></div><div class="entete"><span class="tag">SEMAINE</span></div>'
            f'<div class="semaine">{"".join(jours)}</div>')


def ecran_citation(maintenant, q):
    """Écran plein, montré brièvement : la citation n'a plus à se serrer dans le panneau de droite."""
    if "erreur" in q:
        return entete("CITATION") + f'<p>{esc(q["erreur"])}</p>'
    n = len(q["texte"])
    taille = 64 if n <= 80 else 52 if n <= 150 else 44
    return (f'<section class="citation"><div class="ouvrant">«</div>'
            f'<blockquote style="font-size:{taille}px">{esc(q["texte"])}&nbsp;»</blockquote>'
            f'<div class="filet"></div><cite class="s24 gras">{esc(q["auteur"].upper())}</cite>'
            f'<div class="source">Wikiquote, citation du jour du {esc(q["jour"])}</div></section>')


def ecran(maintenant, panneau, contenu, meteo_html=None, importants=0):
    """Bandeau commun (date, mails importants non lus, place de l'écran dans l'ordre des boutons, heure du relevé),
    puis soit la colonne météo et le panneau de droite, soit un écran plein (meteo_html absent)."""
    badge = (f'<span class="badge">{icone("enveloppe", 16)}<span class="s24 gras">{"99+" if importants >= 100 else importants}'
             f'</span></span>' if importants else "")
    points = "".join(f'<i class="{"ici" if p == panneau else ""}"></i>' for p in NAVIGATION)
    quoi = POUBELLES.get(maintenant.weekday())  # la veille du ramassage, toute la journée
    rappel = f'<span class="badge rappel">{icone("poubelle", 16)}<span class="s16 gras">{quoi}</span></span>' if quoi else ""
    # Place comptée (12 écrans aux boutons) : avec un badge, « RELEVÉ » tombe et la date s'abrège si besoin.
    jours, mois = (JOURS_COURTS, MOIS_COURTS) if rappel and badge else (JOURS, MOIS_COURTS) if rappel else (JOURS, MOIS)
    if badge and not rappel and len(f"{JOURS[maintenant.weekday()]} {maintenant.day} {MOIS[maintenant.month - 1]}") > 18:
        mois = MOIS_COURTS
    corps = (f'<main class="plein">{contenu}</main>' if meteo_html is None else
             f'{meteo_html}<div class="separation"></div><main class="panneau">{contenu}</main>')
    return (f'<div class="ecran"><header class="bandeau"><span class="s24 gras date">{jours[maintenant.weekday()]} '
            f'{maintenant.day} {mois[maintenant.month - 1]}</span><span class="droite">{rappel}{badge}<span class="pages">{points}'
            f'</span><span class="s16">{"" if rappel or badge else "RELEVÉ "}{maintenant:%H:%M}</span></span></header>'
            f'<div class="trame"></div>{corps}</div>')


# ── écrans du jour : dessin, lumière, livre, mot, stations (01/01/2026) ──────────

def telecharger(url, entetes=None, donnees=None, timeout=10):
    req = urllib.request.Request(url, data=donnees, headers={**UA_WIKI, **(entetes or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def notion(chemin, corps, jeton="NOTION_TOKEN"):
    h = {"Authorization": "Bearer " + lire_env(jeton), "Notion-Version": "2025-09-03", "Content-Type": "application/json"}
    return json.loads(telecharger(f"https://api.notion.com/v1/{chemin}", h, json.dumps(corps).encode()), strict=False)


def propriete(p, k):
    """Valeur lisible d'une propriété Notion (texte, choix, formule, nombre, case, date, étiquettes)."""
    v = p.get(k) or {}
    t = v.get("type")
    if t in ("title", "rich_text"):
        return "".join(x["plain_text"] for x in v[t])
    if t == "select":
        return (v["select"] or {}).get("name", "")
    if t == "formula":
        return v["formula"].get(v["formula"]["type"]) or ""
    if t in ("number", "checkbox", "url"):
        return v[t]
    if t == "date":
        return (v["date"] or {}).get("start", "")
    if t == "multi_select":
        return ", ".join(x["name"] for x in v["multi_select"])
    return ""


def tirage(maintenant):
    """Clé du tirage du moment : un le matin, un autre à partir de RETIRAGE, pour ne pas revoir les mêmes l'après-midi."""
    return f"{maintenant:%Y-%m-%d}{'-2' if maintenant.hour >= RETIRAGE else ''}"


def graine(maintenant, sel=""):
    """Même résultat pendant tout le tirage du moment, un autre au suivant."""
    return int(hashlib.sha256(f"{tirage(maintenant)}{sel}".encode()).hexdigest(), 16)


def garder_du_jour(dossier, motif, garde):
    """Efface les fichiers du jour précédent (même motif) une fois celui du jour écrit."""
    for f in dossier.glob(motif):
        if f.name != garde:
            f.unlink(missing_ok=True)


def tramer(img, largeur, hauteur, marge=0.0):
    """Image en 16 gris tramés (Floyd-Steinberg), contraste étiré : l'arrondi simple fait des bandes."""
    from PIL import Image, ImageOps
    img = ImageOps.exif_transpose(img)   # photos de couverture prises au téléphone : sens réel
    if marge:
        dx, dy = int(img.width * marge), int(img.height * marge)
        img = img.crop((dx, dy, img.width - dx, img.height - dy))
    gris = ImageOps.autocontrast(img.convert("L"), cutoff=1)
    gris.thumbnail((largeur, hauteur), Image.LANCZOS)
    palette = Image.new("P", (1, 1))
    palette.putpalette([v for n in range(16) for v in (n * 17,) * 3] + [0] * 3 * 240)
    return gris.convert("RGB").quantize(palette=palette, dither=Image.Dither.FLOYDSTEINBERG).convert("L")


def image_tramee(source, nom, boite, sortie, marge=0.0):
    """<img> d'une image tramée une seule fois (img-<nom>-<image source>.png, à côté des pages rendues)."""
    from PIL import Image
    fichier = sortie / f"img-{nom}-{Path(source).stem}.png"
    if not fichier.exists():
        img = tramer(Image.open(source), *boite, marge=marge)
        img.save(fichier)
        garder_du_jour(sortie, f"img-{nom}-*.png", fichier.name)
    else:
        img = Image.open(fichier)
    return f'<img class="t16" src="{fichier.name}" width="{img.width}" height="{img.height}">'


def affichable(img, technique, titre):
    """Un dessin qui passe sur l'e-ink : technique graphique, sans couleur qui porte l'œuvre, encre lisible
    (seuils calés sur 20 dessins le 01/01/2026)."""
    import numpy as np
    from PIL import ImageOps
    t = technique.lower()
    if not any(m in t for m in TECHNIQUES_OK) or any(m in t for m in TECHNIQUES_NON):
        return False, "technique"
    if "verso" in titre.lower():
        return False, "recto-verso"
    ratio = img.width / img.height
    if not 0.55 <= ratio <= 1.6:
        return False, f"forme {ratio:.2f}"
    rgb = np.asarray(img.convert("RGB"), dtype=float)
    rg, yb = rgb[..., 0] - rgb[..., 1], 0.5 * (rgb[..., 0] + rgb[..., 1]) - rgb[..., 2]
    couleur = math.hypot(rg.std(), yb.std()) + 0.3 * math.hypot(rg.mean(), yb.mean())
    brut = np.asarray(img.convert("L"), dtype=float)
    etendue = np.percentile(brut, 98) - np.percentile(brut, 2)
    a = np.asarray(ImageOps.autocontrast(img.convert("L"), cutoff=1), dtype=float)
    encre, ecart = (a < 110).mean(), a.std()
    if couleur > 30:
        return False, f"couleur {couleur:.0f}"
    if etendue < 90:
        return False, f"trop pâle {etendue:.0f}"
    if not 0.04 <= encre <= 0.45 or ecart < 40:
        return False, f"encre {encre:.2f} écart {ecart:.0f}"
    return True, f"couleur {couleur:.0f}, encre {encre:.2f}"


def concepts(maintenant):
    if not CONCEPTS:
        return sorted(({"concept": c["concept"], "definition": c.get("definition", "")} for c in
                       json.loads((ICI / "consignes-dessin.json").read_text(encoding="utf-8"))["concepts"]),
                      key=lambda c: c["concept"])
    r = notion(f"data_sources/{CONCEPTS}/query", {"page_size": 100})
    return sorted(({"concept": propriete(e["properties"], "Concept"), "definition": propriete(e["properties"], "Définition")}
                   for e in r["results"]), key=lambda c: c["concept"])


def consigne(maintenant, concept):
    """Une consigne du jour pour ce concept, tirée de consignes-dessin.json (écrite d'après les livres de dessin)."""
    try:
        for c in json.loads((ICI / "consignes-dessin.json").read_text(encoding="utf-8"))["concepts"]:
            if c["concept"] == concept and c["consignes"]:
                liste = c["consignes"]
                return {**liste[graine(maintenant, "consigne") % len(liste)], "famille": c.get("famille_oeuvre", "trait")}
    except (OSError, ValueError, KeyError):
        pass
    return {"texte": "Recopie le dessin du jour en 20 minutes : d'abord les grandes masses, puis les valeurs.",
            "duree_min": 20, "materiel": "crayon HB et 2B", "source": None, "famille": "trait"}


def oeuvre(maintenant, famille, sortie):
    """Un dessin CC0 du Cleveland Museum qui passe sur l'e-ink, gardé pendant le tirage du moment. La recherche
    s'arrête au bout de 25 s (le passage de dashboard.py est borné) et reprend où elle en était au passage suivant."""
    from PIL import Image
    jour = tirage(maintenant)
    cache = sortie / "cache"
    fiche = cache / f"oeuvre-{jour}.json"
    if fiche.exists():
        return json.loads(fiche.read_text(encoding="utf-8"))
    suivi = cache / "oeuvre-essais.json"
    try:
        essais = json.loads(suivi.read_text(encoding="utf-8"))
        assert essais["jour"] == jour and essais["famille"] == famille
    except (OSError, ValueError, KeyError, AssertionError):
        requetes = FAMILLES.get(famille, FAMILLES["trait"])
        base = {"type": "Drawing", "has_image": 1, "cc0": 1, **requetes[graine(maintenant, "requete") % len(requetes)]}
        total = json.loads(telecharger(f"{CLEVELAND}?{urllib.parse.urlencode({**base, 'limit': 1})}"))["info"]["total"]
        essais = {"jour": jour, "famille": famille, "base": base, "total": max(total, 1),
                  "debut": graine(maintenant, "oeuvre") % max(total, 1), "vus": 0}
    limite = time.monotonic() + 25
    while time.monotonic() < limite and essais["vus"] < essais["total"]:
        q = urllib.parse.urlencode({**essais["base"], "limit": 3, "skip": (essais["debut"] + essais["vus"]) % essais["total"],
                                    "fields": "id,title,creators,creation_date,technique,images,url"})
        for o in json.loads(telecharger(f"{CLEVELAND}?{q}"))["data"]:
            essais["vus"] += 1
            web = ((o.get("images") or {}).get("web") or {}).get("url")
            if not web:
                continue
            img = Image.open(io.BytesIO(telecharger(web, timeout=10)))
            ok, _ = affichable(img, o.get("technique") or "", o.get("title") or "")
            if not ok:
                continue
            photo = cache / f"oeuvre-{jour}.jpg"
            img.convert("RGB").save(photo, quality=92)
            auteur = re.sub(r"\s*\(.*$", "", (o.get("creators") or [{}])[0].get("description") or "Anonyme")
            res = {"titre": o["title"], "auteur": auteur, "date": o.get("creation_date") or "", "image": str(photo),
                   "ratio": img.width / img.height}
            ecrire(fiche, json.dumps(res, ensure_ascii=False))
            garder_du_jour(cache, "oeuvre-2*.json", fiche.name)  # fiches et images des tirages passés
            garder_du_jour(cache, "oeuvre-2*.jpg", photo.name)
            return res
    ecrire(suivi, json.dumps(essais, ensure_ascii=False))
    return {"erreur": f"Dessin du jour : recherche en cours ({essais['vus']} essayés)"}


def position_soleil(t):
    """(hauteur, azimut) du soleil en degrés : hauteur au-dessus de l'horizon, azimut compté du nord vers l'est
    (formules simplifiées de la NOAA, sans réfraction)."""
    n = t.timestamp() / 86400 + 2440587.5 - 2451545.0
    g = math.radians((357.528 + 0.9856003 * n) % 360)
    lam = math.radians((280.460 + 0.9856474 * n) % 360 + 1.915 * math.sin(g) + 0.020 * math.sin(2 * g))
    eps = math.radians(23.439 - 0.0000004 * n)
    dec = math.asin(math.sin(eps) * math.sin(lam))
    ra = math.atan2(math.cos(eps) * math.sin(lam), math.cos(lam))
    ha = math.radians((280.46061837 + 360.98564736629 * n) % 360 + LIEU["lon"]) - ra
    la = math.radians(LIEU["lat"])
    h = math.asin(math.sin(la) * math.sin(dec) + math.cos(la) * math.cos(dec) * math.cos(ha))
    az = math.atan2(math.sin(ha), math.cos(ha) * math.sin(la) - math.tan(dec) * math.cos(la))
    return math.degrees(h), (math.degrees(az) + 180) % 360


def soleil(t):
    """Hauteur du soleil en degrés au-dessus de l'horizon."""
    return position_soleil(t)[0]


def cap(az):
    """Direction en clair d'un azimut (16 points, en français)."""
    return ["N", "NNE", "NE", "ENE", "E", "ESE", "SE", "SSE", "S", "SSO", "SO", "OSO", "O", "ONO", "NO", "NNO"][round(az / 22.5) % 16]


def course_du_soleil(maintenant):
    """Hauteur minute par minute et heures de passage : heure bleue −6° à −4°, heure dorée −4° à +6°, lever et
    coucher à −0,833° (réfraction et rayon du disque)."""
    jour = maintenant.replace(hour=0, minute=0, second=0, microsecond=0)
    minutes = [jour + dt.timedelta(minutes=i) for i in range(1441)]
    h = [soleil(t) for t in minutes]

    def passages(seuil):
        montee = descente = None
        for i in range(1, len(h)):
            if h[i - 1] < seuil <= h[i] and montee is None:
                montee = minutes[i]
            if h[i - 1] >= seuil > h[i]:
                descente = minutes[i]
        return montee, descente
    (b0, b3), (o0, o3), (l0, l1), (o1, o2) = passages(-6), passages(-4), passages(-0.833), passages(6)
    return {"aube_bleue": b0, "aube_or": o0, "lever": l0, "fin_or_matin": o1, "debut_or_soir": o2, "coucher": l1,
            "fin_or_soir": o3, "fin_bleue": b3, "courbe": h}


def nuages(maintenant):
    """Couverture nuageuse par étage, pluie et temps, heure par heure (Open-Meteo, sans clé)."""
    q = urllib.parse.urlencode({"latitude": LIEU["lat"], "longitude": LIEU["lon"], "timezone": "Europe/Paris",
                                "hourly": "cloud_cover_low,cloud_cover_mid,cloud_cover_high,precipitation_probability,"
                                          "weather_code,is_day", "forecast_days": 3})
    r = appel(f"https://api.open-meteo.com/v1/forecast?{q}")["hourly"]
    return {t: [r["cloud_cover_low"][i], r["cloud_cover_mid"][i], r["cloud_cover_high"][i],
                r["precipitation_probability"][i] or 0, r["weather_code"][i], r["is_day"][i]] for i, t in enumerate(r["time"])}


def ciel_pendant(debut, fin, ciel):
    """Moyenne (nuages bas, moyens, hauts, risque de pluie) des heures qui touchent [debut, fin] ; None sans prévision."""
    if not (debut and fin) or not isinstance(ciel, dict) or "erreur" in ciel:
        return None
    vals, h = [], debut.replace(minute=0, second=0, microsecond=0)
    while h <= fin:
        if h.strftime("%Y-%m-%dT%H:00") in ciel:
            vals.append(ciel[h.strftime("%Y-%m-%dT%H:00")])
        h += dt.timedelta(hours=1)
    return tuple(round(sum(v[i] for v in vals) / len(vals)) for i in range(4)) if vals else None


def verdict_ciel(m):
    """Ce que le ciel promet pour la photo, d'après ciel_pendant() : les nuages bas bouchent, les nuages hauts ou
    moyens prennent la couleur du soleil rasant si l'horizon est dégagé."""
    if m is None:
        return "?", "Pas de prévision."
    bas, moy, haut, pluie = m
    if pluie >= 50:
        return "PLUIE", "Pluie probable : lumière grise."
    if bas >= 70:
        return "BOUCHÉ", "Nuages bas épais : le soleil ne passera pas."
    if bas < 30 and 30 <= max(moy, haut) <= 80 and pluie < 30:
        return "PROMETTEUR", "Horizon dégagé, nuages en altitude : ils peuvent s'embraser."
    if max(bas, moy, haut) < 20:
        return "NET", "Ciel dégagé : lumière franche, ombres longues, ciel sans couleur."
    if bas >= 30:
        return "MOYEN", "Nuages bas par endroits : quelques trouées possibles."
    return "MOYEN", "Voile en altitude : lumière douce, peu de couleur."


def fenetres(s):
    """Les deux moments photo d'une journée : leurs heures bleue et dorée, dans l'ordre où elles arrivent."""
    return {"matin": {"debut": s["aube_bleue"], "fin": s["fin_or_matin"], "soleil": s["lever"], "mot": "LEVER",
                      "doree": (s["aube_or"], s["fin_or_matin"]),
                      "plages": [("BLEUE", s["aube_bleue"], s["aube_or"]), ("DORÉE", s["aube_or"], s["fin_or_matin"])]},
            "soir": {"debut": s["debut_or_soir"], "fin": s["fin_bleue"], "soleil": s["coucher"], "mot": "COUCHER",
                     "doree": (s["debut_or_soir"], s["fin_or_soir"]),
                     "plages": [("DORÉE", s["debut_or_soir"], s["fin_or_soir"]), ("BLEUE", s["fin_or_soir"], s["fin_bleue"])]}}


def boussole(maintenant, s, f):
    """La course du soleil vue du dessus (nord en haut, est à droite) : horizon, anneau du crépuscule jusqu'à -6°,
    heure dorée en trait épais, heure bleue en tirets, soleil du moment, flèche vers le lever ou le coucher de `f`."""
    c, R = 125, 98
    jour = s["aube_bleue"].replace(hour=0, minute=0, second=0, microsecond=0)

    def point(e, az, r=None):
        r = R * (90 - e) / 90 if r is None else r
        return c + r * math.sin(math.radians(az)), c - r * math.cos(math.radians(az))
    svg = [f'<svg width="{2 * c}" height="{2 * c}" viewBox="0 0 {2 * c} {2 * c}" xmlns="http://www.w3.org/2000/svg">',
           f'<circle cx="{c}" cy="{c}" r="{R * 96 / 90:.1f}" fill="none" stroke="#000" stroke-width="1" stroke-dasharray="3 5"/>',
           f'<circle cx="{c}" cy="{c}" r="{R}" fill="none" stroke="#000" stroke-width="3"/>']
    for e in (30, 60):
        svg.append(f'<circle cx="{c}" cy="{c}" r="{R * (90 - e) / 90:.1f}" fill="none" stroke="#000" stroke-width="1" stroke-dasharray="1 5"/>')
    for az, nom in ((0, "N"), (90, "E"), (180, "S"), (270, "O")):
        x, y = point(0, az, R + 18)
        svg.append(f'<text x="{x:.0f}" y="{y + 6:.0f}" text-anchor="middle" class="cap">{nom}</text>')
    for az in range(0, 360, 45):
        (x0, y0), (x1, y1) = point(0, az, R - 6), point(0, az, R + 6)
        svg.append(f'<line x1="{x0:.1f}" y1="{y0:.1f}" x2="{x1:.1f}" y2="{y1:.1f}" stroke="#000" stroke-width="2"/>')
    traits, cur = [], None
    for m in range(0, 1441, 3):
        e, az = position_soleil(jour + dt.timedelta(minutes=m))
        classe = None if e < -6 else "bleue" if e < -4 else "or" if e < 6 else "jour"
        if classe != cur:
            if cur and len(traits[-1][1]) == 1:
                traits.pop()
            if classe:
                traits.append((classe, [point(e, az)] if not cur else [traits[-1][1][-1], point(e, az)] if cur else []))
            cur = classe
        elif classe:
            traits[-1][1].append(point(e, az))
    style = {"jour": 'stroke-width="2"', "or": 'stroke-width="10"', "bleue": 'stroke-width="5" stroke-dasharray="4 4"'}
    for classe, pts in traits:
        svg.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}" fill="none" stroke="#000" {style[classe]}/>')
    _, az = position_soleil(f["soleil"])
    x, y = point(0, az, R - 14)
    svg.append(f'<line x1="{c}" y1="{c}" x2="{x:.1f}" y2="{y:.1f}" stroke="#000" stroke-width="3"/>')
    pointe = [point(0, az, R - 2), point(0, az - 8, R - 20), point(0, az + 8, R - 20)]
    svg.append(f'<polygon points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pointe)}" fill="#000"/>')
    e, az_m = position_soleil(maintenant)
    if e >= -6 and maintenant.date() == jour.date():
        x, y = point(e, az_m)
        svg.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="11" fill="#000" stroke="#fff" stroke-width="4"/>')
    svg.append(f'<circle cx="{c}" cy="{c}" r="3" fill="#000"/></svg>')
    return "".join(svg), az


def heure_photo(maintenant, s):
    """Vrai dans les fenêtres où l'écran Lumière entre dans la rotation : de 1 h avant l'heure bleue du matin à la fin
    de l'heure dorée, et de 2 h avant l'heure dorée du soir à la fin de l'heure bleue."""
    return any(a and b and a <= maintenant <= b for a, b in (
        (s["aube_bleue"] and s["aube_bleue"] - dt.timedelta(hours=1), s["fin_or_matin"]),
        (s["debut_or_soir"] and s["debut_or_soir"] - dt.timedelta(hours=2), s["fin_bleue"])))


def livre_du_jour(maintenant, sortie):
    """Un livre possédé et pas lu, parmi ceux que propose la formule « Suggéré ? » de Ma bibliothèque (elle change
    chaque heure : le choix du tirage du moment est gardé dans une fiche)."""
    cache = sortie / "cache"
    fiche = cache / f"livre-{tirage(maintenant)}.json"
    if fiche.exists():
        return json.loads(fiche.read_text(encoding="utf-8"))
    filtre = {"and": [{"property": "Suggéré ?", "formula": {"string": {"equals": "A lire 🤓"}}},
                      {"property": "Possession", "checkbox": {"equals": True}}]}
    r = notion(f"data_sources/{BIBLIOTHEQUE}/query", {"page_size": 50, "filter": filtre}, JETON_BIBLIOTHEQUE)["results"]
    if not r:
        filtre = {"and": [{"property": "Lu", "select": {"equals": "Non"}}, {"property": "Possession", "checkbox": {"equals": True}}]}
        r = notion(f"data_sources/{BIBLIOTHEQUE}/query", {"page_size": 100, "filter": filtre}, JETON_BIBLIOTHEQUE)["results"]
    p = r[graine(maintenant, "livre") % len(r)]["properties"]
    resume = propriete(p, "Résumé (trad. fr)") or propriete(p, "Résumé") or propriete(p, "Résumé auto")
    if re.search(r"aucun détail|pas de détail|aucune information|peu d'informations", resume, re.I):
        resume = ""  # résumé généré qui ne dit rien
    res = {"titre": propriete(p, "Titre"), "auteurs": propriete(p, "Auteurs"), "editeur": propriete(p, "Éditeur"),
           "date": str(propriete(p, "Date de publication"))[:4], "pages": propriete(p, "Pages"),
           "resume": re.sub(r"^\(Généré via IA\)\s*", "", resume), "tags": propriete(p, "Tags"), "type": propriete(p, "Type")}
    couverture = propriete(p, "Chemin de la couverture (calc.)")
    if couverture:
        photo = cache / f"livre-{tirage(maintenant)}.img"
        photo.write_bytes(telecharger(couverture, timeout=20))
        res["image"] = str(photo)
        garder_du_jour(cache, "livre-2*.img", photo.name)
    ecrire(fiche, json.dumps(res, ensure_ascii=False))
    garder_du_jour(cache, "livre-2*.json", fiche.name)
    return res


def mot_du_jour(maintenant, sortie):
    """Le matin, le mot du jour du Wiktionnaire. Il arrive qu'il n'ait pas de page (« néphritique », 01/01/2026) : on
    prend alors celui du même jour les années d'avant, jamais vu à l'écran, plutôt que celui de la veille, qui n'est
    qu'un dernier recours. L'après-midi, directement un mot des années d'avant."""
    cache = sortie / "cache"
    fiche = cache / f"mot-{tirage(maintenant)}.json"
    if fiche.exists():
        return json.loads(fiche.read_text(encoding="utf-8"))
    api = "https://fr.wiktionary.org/w/api.php?"

    def wikitexte(page):
        r = json.loads(telecharger(api + urllib.parse.urlencode({"action": "parse", "page": page, "prop": "wikitext",
                                                                 "format": "json", "redirects": 1})))
        return (r.get("parse") or {}).get("wikitext", {}).get("*")
    for recul in ((0, 365, 730, 1095, 1460, 1825, 1, 2, 3) if maintenant.hour < RETIRAGE else
                  (730, 1095, 1460, 1825, 2190, 365, 1, 2, 3)):
        jour = maintenant - dt.timedelta(days=recul)
        mot = re.sub(r"<noinclude>.*", "", wikitexte(f"Modèle:Mot_du_jour/{jour:%Y/%m/%d}") or "", flags=re.S).strip()
        t = wikitexte(mot) if mot else None
        if t and "{{langue|fr}}" in t:
            break
    else:
        return {"erreur": "Mot du jour introuvable"}
    fr = t[t.find("{{langue|fr}}"):]
    fin = fr.find("\n== {{langue|", 10)
    fr = fr[:fin] if fin > 0 else fr
    nature = re.search(r"=== \{\{S\|([^|}]+)\|fr", fr)
    pron = re.search(r"\{\{pron\|([^|}]+)\|fr", fr)

    def propre(s):
        s = re.sub(r"\{\{(?:lexique|term|registre|figuré|familier|vieilli|désuet|rare|péjoratif|ironique|soutenu|"
                   r"populaire|argot|littéraire|technique|spécialement|par extension|métaphore)\|([^|}]+)[^}]*\}\}",
                   lambda m: f"({m.group(1)[0].upper()}{m.group(1)[1:]})", s)
        s = re.sub(r"\{\{(?:siècle|w)\|?([^}]*)\}\}", r"\1", s)
        s = re.sub(r"\{\{[^}]*\}\}", "", s)
        s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", s)
        s = re.sub(r"\[https?://\S+ ([^\]]+)\]", r"\1", s)
        s = re.sub(r"'''?|<[^>]+>", "", s)
        return re.sub(r"\s+", " ", s).strip()
    definitions = [propre(x[1:]) for x in fr.splitlines() if x.startswith("# ")]
    exemple = re.search(r"#\*\s*\{\{exemple\s*\|\s*(?:lang=fr\s*\|)?\s*([^|}]+)", fr)
    etym = re.search(r"=== \{\{S\|étymologie\}\} ===\s*\n:\s*(.+)", fr)
    res = {"mot": mot, "jour": f"{jour:%Y-%m-%d}", "nature": nature.group(1) if nature else "",
           "pron": pron.group(1) if pron else "", "definitions": [x for x in definitions if x][:2],
           "exemple": propre(exemple.group(1)) if exemple else "", "etymologie": propre(etym.group(1)) if etym else ""}
    ecrire(fiche, json.dumps(res, ensure_ascii=False))
    garder_du_jour(cache, "mot-*.json", fiche.name)
    return res


def horaires_prevus(jour, sortie):
    """Horaires prévus du jour de service `jour` à mes stations (GTFS ilévia, 9 Mo, re-téléchargé une fois par jour) :
    {indice de station: {"aller": [s], "retour": [s], "vers": {terminus: courses}}}, en secondes depuis minuit
    (au-delà de 24 h : la nuit suivante)."""
    import csv
    import zipfile
    cache = sortie / "cache"
    fiche = cache / f"gtfs-{jour:%Y%m%d}.json"
    if fiche.exists():
        return {int(k): v for k, v in json.loads(fiche.read_text(encoding="utf-8")).items()}
    archive = cache / "gtfs.zip"
    if not archive.exists() or time.time() - archive.stat().st_mtime > 20 * 3600:
        ecrire(archive, telecharger(ILEVIA_GTFS, timeout=60))
    with zipfile.ZipFile(archive) as z:
        def table(nom):
            return csv.DictReader(io.TextIOWrapper(z.open(nom), encoding="utf-8-sig"))
        quais = {}
        for r in table("stops.txt"):
            for i, st in enumerate(STATIONS):
                if r["parent_station"] == st["parent"]:
                    quais.setdefault(r["stop_id"], []).append(i)
        services = {r["service_id"] for r in table("calendar_dates.txt")
                    if r["date"] == f"{jour:%Y%m%d}" and r["exception_type"] == "1"}
        lignes = {st["ligne"] for st in STATIONS}
        courses = {r["trip_id"]: r for r in table("trips.txt") if r["service_id"] in services and r["route_id"] in lignes}
        res = {i: {"aller": [], "retour": [], "vers": {}} for i in range(len(STATIONS))}
        for r in table("stop_times.txt"):
            if r["stop_id"] not in quais or r["trip_id"] not in courses:
                continue
            c = courses[r["trip_id"]]
            for i in quais[r["stop_id"]]:
                st = STATIONS[i]
                if c["route_id"] != st["ligne"]:
                    continue
                h, m, s = map(int, r["departure_time"].split(":"))
                aller = c["direction_id"] == st["sens"]
                res[i]["aller" if aller else "retour"].append(h * 3600 + m * 60 + s)
                if aller:
                    res[i]["vers"][c["trip_headsign"]] = res[i]["vers"].get(c["trip_headsign"], 0) + 1
    for v in res.values():
        v["aller"].sort()
        v["retour"].sort()
    ecrire(fiche, json.dumps(res))
    for f in cache.glob("gtfs-2*.json"):  # garder la veille et le lendemain (stations() lit deux jours de service)
        if f.stem[5:] < f"{jour - dt.timedelta(days=1):%Y%m%d}":
            f.unlink(missing_ok=True)
    return res


def stations(maintenant, sortie):
    """Pour chaque station : 3 prochains départs dans le sens voulu (temps réel ilévia pour le tram, horaires prévus
    pour le métro, absent du temps réel, et pour le tram si le temps réel ne répond pas), direction, premier et dernier
    départ du jour, premier et dernier retour (arrivée en sens inverse)."""
    service = (maintenant - dt.timedelta(hours=4)).replace(hour=0, minute=0, second=0, microsecond=0)  # la nuit : veille
    jours = {k: horaires_prevus(service + dt.timedelta(days=k), sortie) for k in (0, 1)}
    en_heure = lambda k, s: service + dt.timedelta(days=k, seconds=s)  # noqa: E731
    direct = None
    noms = sorted({st["direct"][0] for st in STATIONS if st.get("direct")})
    if noms:
        try:
            filtre = "nom_station IN (" + ",".join(f"'{n}'" for n in noms) + ")"
            q = urllib.parse.urlencode({"f": "application/json", "limit": 200, "filter-lang": "cql-text", "filter": filtre})
            direct = {}
            for f in appel(f"{ILEVIA_DIRECT}?{q}")["features"]:
                p = f["properties"]
                # Les heures portent un « Z » mais sont à l'heure de Paris.
                h = dt.datetime.fromisoformat(p["heure_estimee_depart"].rstrip("Z")).replace(tzinfo=PARIS)
                direct.setdefault((p["nom_station"], p["sens_ligne"]), []).append(h)
        except (OSError, ValueError, KeyError) as e:
            print(f"⚠️ temps réel ilévia : {type(e).__name__} {str(e)[:120]}", file=sys.stderr)
            direct = None
    out = []
    for i, st in enumerate(STATIONS):
        prevus = sorted(en_heure(k, s) for k in (0, 1) for s in jours[k][i]["aller"])
        if st.get("direct") and direct is not None:
            departs, source = sorted(direct.get(tuple(st["direct"]), [])), "direct"
            depuis = maintenant - dt.timedelta(minutes=1)
        else:
            departs, source, depuis = prevus, "prévu", maintenant + dt.timedelta(seconds=30)
        a, r = jours[0][i]["aller"], jours[0][i]["retour"]
        vers = jours[0][i].get("vers") or {}
        # Direction : celle du temps réel pour le tram, sinon le terminus le plus fréquent des horaires prévus.
        direction = st["direct"][1] if st.get("direct") else max(vers, key=vers.get, default="")
        out.append({**st, "source": source, "direction": direction.upper(), "departs": [x for x in departs if x >= depuis][:3],
                    "premier": en_heure(0, a[0]) if a else None, "dernier": en_heure(0, a[-1]) if a else None,
                    "premier_retour": en_heure(0, r[0]) if r else None, "dernier_retour": en_heure(0, r[-1]) if r else None})
    return out


def raison_stations(maintenant, a):
    """(raison, imminent) : pourquoi l'écran Stations entre dans la rotation, dans un de ses créneaux fixes
    (STATIONS_CRENEAUX) ou dans les 2 h avant un rendez-vous des agendas SORTIES, sauf ceux de PAS_UNE_SORTIE (le
    sport, en voiture) ; imminent dans les IMMINENT dernières minutes avant le rendez-vous. (None, False) sinon."""
    for c in STATIONS_CRENEAUX:
        if maintenant.weekday() == c["jour"] and c["de"] <= f"{maintenant:%H:%M}" < c["a"]:
            return c["texte"], False
    for x in (a.get("jours") or [[]])[0] if isinstance(a, dict) else []:
        if (x["heure"] in ("JOUR", "suite") or x.get("agenda") not in SORTIES
                or re.search(PAS_UNE_SORTIE, f'{x["titre"]} {x.get("lieu", "")}', re.I)):
            continue
        avant = dt.datetime.fromisoformat(x["cle"]) - maintenant
        if dt.timedelta(0) <= avant <= dt.timedelta(hours=2):
            return f"{x['heure']} {x['titre'].upper()}", avant <= dt.timedelta(minutes=IMMINENT)
    return None, False


def ecran_dessin(maintenant, c, k, o, sortie):
    if "erreur" in c:
        return entete("DESSIN DU JOUR") + f'<p>{esc(c["erreur"])}</p>'
    if "erreur" not in o and not Path(o["image"]).exists():
        o = {"erreur": "Dessin du jour : image en cours de relève"}
    paysage = "erreur" not in o and o["ratio"] > 1.15
    if "erreur" in o:
        image, credit = f'<p>{esc(o["erreur"])}</p>', ""
    else:
        image = image_tramee(o["image"], "dessin", (768, 250) if paysage else (352, 440), sortie, marge=0.02)
        credit = f'{esc(o["auteur"])}, <i>{esc(o["titre"][:60])}</i>, {esc(o["date"])} · Cleveland Museum of Art, CC0'
    duree = f'{k.get("duree_min", "")} MIN · {esc(k.get("materiel", "")).upper()}'
    source = k.get("source") or {}
    ref = (f'<div class="ref">d\'après {esc(source.get("livre", "").split(" — ")[0])}'
           f'{", p. " + str(source["page"]) if source.get("page") else ""}</div>' if source else "")
    idee = (f'<div class="idee">{entete("DESSIN DU JOUR")}<div class="concept">{esc(c["concept"])}</div>'
            f'<div class="def">{esc(c["definition"])}</div></div>')
    travail = (f'<div class="travail"><div class="entete"><span class="tag">CONSIGNE</span></div>'
               f'<div class="consigne">{esc(k["texte"])}</div><div class="duree s16">{duree}</div>{ref}</div>')
    if paysage:
        return (f'<section class="dessin paysage"><div class="oeuvre">{image}<div class="credit">{credit}</div></div>'
                f'<div class="bas">{idee}<div class="sep"></div>{travail}</div></section>')
    return (f'<section class="dessin"><div class="oeuvre">{image}<div class="credit">{credit}</div></div>'
            f'<div class="sep"></div><div class="txt">{idee}<div class="double"></div>{travail}</div></section>')


def ecran_lumiere(maintenant, s, ciel):
    if not (s["aube_bleue"] and s["fin_bleue"]):
        return entete("LUMIÈRE DU JOUR") + "<p>Pas d'heure bleue aujourd'hui.</p>"
    hm = lambda t: t.strftime("%H:%M") if t else "–"  # noqa: E731
    f = fenetres(s)
    if maintenant < f["matin"]["fin"]:
        jour, quand, principal, autre, autre_quand, autre_passe = s, "CE MATIN", f["matin"], f["soir"], "CE SOIR", False
    elif maintenant < f["soir"]["fin"]:
        jour, quand, principal, autre, autre_quand, autre_passe = s, "CE SOIR", f["soir"], f["matin"], "CE MATIN", True
    else:  # la journée est finie : le prochain moment est demain matin
        jour = course_du_soleil(maintenant + dt.timedelta(days=1))
        quand, principal, autre, autre_quand, autre_passe = "DEMAIN MATIN", fenetres(jour)["matin"], f["soir"], "CE SOIR", True
    if maintenant < principal["debut"]:
        reste = int((principal["debut"] - maintenant).total_seconds() // 60)
        compte = f"DANS {reste // 60} H {reste % 60:02d}" if reste >= 60 else f"DANS {reste} MIN"
    else:
        compte = "MAINTENANT"
    m = ciel_pendant(*principal["doree"], ciel)
    verdict, phrase = verdict_ciel(m)
    plages = "".join(f'<div class="ligne"><span class="s16 gras">{nom}</span><span class="v50">{hm(a)} › {hm(b)}</span></div>'
                     for nom, a, b in principal["plages"])
    dessin, az = boussole(maintenant, jour, principal)
    heros = (f'<div class="heros"><div class="entete"><span class="tag">{quand}</span><span class="s24 gras">{compte}</span></div>'
             f'<div class="grand">{verdict}</div>{plages}<div class="phrase">{esc(phrase)}</div></div>')
    rose = (f'<div class="rose">{dessin}<div class="s16 gras">{principal["mot"]} {cap(az)} {az:.0f}°</div></div>')
    if m:
        # étages d'Open-Meteo : bas jusqu'à 3 km, moyens de 3 à 8 km, hauts au-dessus
        sens = (("NUAGES BAS", "sous 3 km : cachent le soleil"), ("NUAGES MOYENS", "3 à 8 km : se colorent"),
                ("NUAGES HAUTS", "plus haut : s'embrasent"), ("RISQUE DE PLUIE", ""))
        jauges = "".join(f'<span class="s16 gras">{nom}</span><div class="barre-pleine"><i style="width:{v}%"></i></div>'
                         f'<span class="pc">{v} %</span><span class="role">{role}</span>' for (nom, role), v in zip(sens, m))
    else:
        jauges = '<span>pas de prévision des nuages</span>'
    nuages = (f'<div class="nuages"><div class="s16 gras">PART DU CIEL COUVERT PENDANT L\'HEURE DORÉE</div>'
              f'<div class="jauges">{jauges}</div></div>')
    v_autre, _ = verdict_ciel(ciel_pendant(*autre["doree"], ciel))
    d_or = autre["doree"]
    ligne_autre = (f'<div class="autre"><span class="s16 gras">{autre_quand}{" (PASSÉ)" if autre_passe else ""}</span>'
                   f'<span>{v_autre} · dorée {hm(d_or[0])} › {hm(d_or[1])}</span></div>')
    droite = f'<span class="s16">LEVER {hm(s["lever"])} · COUCHER {hm(s["coucher"])}</span>'
    return (f'<section class="lumiere">{entete("LUMIÈRE DU JOUR", droite)}<div class="haut">{heros}{rose}</div>'
            f'{nuages}{ligne_autre}</section>')


def moment_aerer(maintenant, a, i):
    """(rang de l'heure, libellé) où l'indice sera le plus bas, entre 8 h et 22 h : aujourd'hui, sinon demain."""
    def jour(d):
        return [j for j in range(i, len(a["time"])) if a["time"][j][:10] == f"{d:%Y-%m-%d}" and 8 <= int(a["time"][j][11:13]) < 22
                and a["european_aqi"][j] is not None]
    heures, quand = jour(maintenant), ""
    if not heures:
        heures, quand = jour(maintenant + dt.timedelta(days=1)), "DEMAIN "
    j = min(heures, key=lambda x: a["european_aqi"][x])
    return j, "MAINTENANT" if j == i else f"{quand}{int(a['time'][j][11:13])} H"


def ecran_air(maintenant, a):
    if "erreur" in a:
        return entete("QUALITÉ DE L'AIR") + f'<p>{esc(a["erreur"])}</p>'
    heure = f"{maintenant:%Y-%m-%dT%H}:00"
    i = a["time"].index(heure) if heure in a["time"] else None
    if i is None or a["european_aqi"][i] is None:
        return entete("QUALITÉ DE L'AIR") + "<p>Pas de mesure pour cette heure.</p>"
    indice = a["european_aqi"][i]
    rang, (_, niveau, conseil) = next((n, x) for n, x in enumerate(NIVEAUX_AIR) if indice <= x[0])
    echelle = "".join(f'<i class="{"atteint" if n <= rang else ""}"></i>' for n in range(len(NIVEAUX_AIR)))
    sous = {p: a[f"european_aqi_{p}"][i] or 0 for p, _, _ in POLLUANTS}
    cause = next(nom for p, nom, _ in POLLUANTS if sous[p] == max(sous.values()))
    heros = (f'<div class="heros"><div class="entete"><span class="tag">QUALITÉ DE L\'AIR</span><span class="s24 gras">INDICE {indice}</span></div>'
             f'<div class="grand">{niveau}</div><div class="echelle">{echelle}</div>'
             f'<div class="phrase">{esc(conseil)}</div><div class="phrase s16 gras">CAUSE : {esc(cause)}</div></div>')
    barres = "".join(f'<div class="col"><i style="height:{min(v or 0, 100)}px"></i><span>{a["time"][j][11:13] if n % 6 == 0 else ""}</span></div>'
                     for n, (j, v) in enumerate((j, a["european_aqi"][j]) for j in range(i, min(i + 24, len(a["time"])))))
    courbe = f'<div class="suite"><div class="s16 gras">INDICE SUR 24 H</div><div class="courbe">{barres}</div></div>'
    jauges = "".join(f'<span class="s16 gras">{nom}</span><div class="barre-pleine"><i style="width:{min(sous[p], 100)}%"></i></div>'
                     f'<span class="pc">{a[p][i] or 0:.0f}</span><span class="role">{role}</span>' for p, nom, role in POLLUANTS)
    polluants = (f'<div class="nuages"><div class="s16 gras">CE QU\'IL Y A DANS L\'AIR (MICROGRAMMES PAR M3)</div>'
                 f'<div class="jauges">{jauges}</div></div>')
    j, moment = moment_aerer(maintenant, a, i)
    fin = next((k for k in range(i, len(a["time"])) if a["time"][k][:10] != heure[:10]), len(a["time"]))
    pollens = sorted(((max(x or 0 for x in a[p][i:fin]), nom) for p, nom in POLLENS.items()), reverse=True)
    pollens = ", ".join(f"{nom} {v:.0f}" for v, nom in pollens[:2] if v >= 1) or "aucun"
    bas = (f'<div class="autre"><span class="s16 gras">AÉRER</span><span>{moment} · indice {a["european_aqi"][j]}</span>'
           f'<span class="s16 gras">POLLENS</span><span>{esc(pollens)}</span></div>')
    return f'<section class="lumiere air"><div class="haut">{heros}{courbe}</div>{polluants}{bas}</section>'


def ecran_livre(maintenant, b, sortie):
    if "erreur" in b:
        return entete("À LIRE") + f'<p>{esc(b["erreur"])}</p>'
    image = image_tramee(b["image"], "livre", (300, 470), sortie) if b.get("image") and Path(b["image"]).exists() else ""
    infos = " · ".join(str(x) for x in (b["editeur"], b["date"], f'{b["pages"]} pages' if b["pages"] else "") if x)
    titre = b["titre"]
    taille = 75 if len(titre) <= 18 else 50 if len(titre) <= 60 else 40
    resume = (f'<div class="resume">{esc(b["resume"])}</div>' if b["resume"] else
              f'<div class="theme">{esc(b.get("type") or "")}</div><div class="s16 gras">{esc((b.get("tags") or "").upper())}</div>')
    return (f'<section class="livre"><div class="couv">{image}</div><div class="sep"></div><div class="txt">'
            f'{entete("À LIRE", "<span class=s16>DANS TA BIBLIOTHÈQUE</span>")}'
            f'<div class="titre" style="font-size:{taille}px">{esc(titre)}</div>'
            f'<div class="s24 gras auteur">{esc(b["auteurs"].upper())}</div>'
            f'<div class="infos">{esc(infos)}</div><div class="double"></div>{resume}'
            f'<div class="pied s16">TIRÉ PARMI TES LIVRES PAS ENCORE LUS</div></div></section>')


def ecran_mot(maintenant, m):
    if "erreur" in m:
        return entete("MOT DU JOUR") + f'<p>{esc(m["erreur"])}</p>'
    n = len(m["mot"])
    taille = 150 if n <= 9 else 100 if n <= 14 else 75
    defs = "".join(f'<li>{esc(x)}</li>' for x in m["definitions"])
    exemple = f'<div class="exemple">« {esc(m["exemple"])} »</div>' if m["exemple"] and len(m["exemple"]) <= 280 else ""
    etym = m.get("etymologie", "")
    etym = (f'<div class="etym"><span class="s16 gras">ÉTYMOLOGIE</span> {esc(etym[:180])}{"…" if len(etym) > 180 else ""}</div>'
            if etym else "")
    jour = dt.date.fromisoformat(m["jour"])
    pron = f'<span class="api">/{esc(m["pron"])}/</span>' if m["pron"] else ""
    return (f'<section class="mot">{entete("MOT DU JOUR", "<span class=s16>WIKTIONNAIRE</span>")}'
            f'<div class="le-mot" style="font-size:{taille}px">{esc(m["mot"])}</div>'
            f'<div class="pron">{pron}<span class="s16 gras">{esc(m["nature"].upper())}</span></div>'
            f'<ol>{defs}</ol>{exemple}{etym}'
            f'<div class="source s16">MOT DU JOUR DU {jour.day} {MOIS[jour.month - 1]}{f" {jour.year}" if jour.year != maintenant.year else ""} · WIKTIONNAIRE, CC BY-SA</div></section>')


def ecran_stations(maintenant, liste, raison):
    if isinstance(liste, dict):
        return entete("MES STATIONS") + f'<p>{esc(liste.get("erreur", "indisponible"))}</p>'
    hm = lambda t: f"{t:%H:%M}" if t else "–"  # noqa: E731
    colonnes = []
    for st in liste:
        lignes = []
        for i, x in enumerate(st["departs"]):
            dans = max(0, round((x - maintenant).total_seconds() / 60))
            quand = "<small>À QUAI</small>" if dans == 0 else f"{dans} MIN" if dans < 60 else f"{x:%H:%M}"
            lignes.append(f'<div class="depart{" premier" if i == 0 else ""}"><span class="dans">{quand}</span>'
                          f'<span class="heure">{x:%H:%M}</span></div>')
        dernier_passe = st["dernier"] and maintenant > st["dernier"]
        colonnes.append(
            f'<div class="station"><div class="entete"><span class="tag">{esc(st["mode"])}</span>'
            f'<span class="s16">{"EN DIRECT" if st["source"] == "direct" else "PRÉVU"}</span></div>'
            f'<div class="nom">{esc(st["nom"].upper())}</div>'
            f'<div class="vers"><span class="fleche">›</span>{esc(st["direction"])}</div>'
            f'<div class="departs">{"".join(lignes) or "<div class=vide>plus de passage</div>"}</div>'
            f'<div class="jour"><div class="s16 gras">{"VERS " + esc(st["vers"].upper()) if st.get("vers") else "ALLER"}</div>'
            f'<div class="duo"><span><i>1ER</i>{hm(st["premier"])}</span>'
            f'<span{" class=passe" if dernier_passe else ""}><i>DERNIER</i>{hm(st["dernier"])}</span></div>'
            f'<div class="s16 gras">RETOUR ICI</div>'
            f'<div class="duo"><span><i>1ER</i>{hm(st["premier_retour"])}</span><span><i>DERNIER</i>{hm(st["dernier_retour"])}</span></div>'
            f'</div></div>')
    vers = next((st["vers"].upper() for st in liste if st.get("vers")), "")
    droite = f'<span class="s16">{esc(raison)[:34] if raison else "DIRECTION " + esc(vers) if vers else ""}</span>'
    return (f'<section class="stations">{entete("MES STATIONS", droite)}<div class="colonnes">{"".join(colonnes)}</div>'
            f'<div class="pied s16">TRAM : TEMPS RÉEL ILÉVIA · MÉTRO : HORAIRES PRÉVUS</div></section>')


# ── rendu ────────────────────────────────────────────────────────────────────────────────────────

def rendre(pages, largeur, hauteur, rotation, sortie, hors_ligne_html):
    """pages : {nom: html}. Écrit apercu-<nom>.png (paysage), ecran-<nom>.png (tourné, natif liseuse) et
    ecran-<nom>-hl.png : le même écran, bandeau remplacé par « HORS LIGNE », que la liseuse garde sous la main pour
    l'afficher d'elle-même si le Mac ne répond plus (elle ne sait pas dessiner du texte dans le bon sens)."""
    from playwright.sync_api import sync_playwright
    from PIL import Image

    def photo(page, nom, page_html):
        fichier = sortie / f"{nom}.html"
        fichier.write_text(page_html, encoding="utf-8")
        page.goto(fichier.as_uri())
        page.evaluate("document.fonts.ready.then(() => true)")
        brut = sortie / f"brut-{nom}.png"
        page.screenshot(path=str(brut))
        img = Image.open(brut).convert("L").point(lambda v: round(v / 17) * 17)  # 16 gris de l'e-ink
        brut.unlink()
        return img

    with sync_playwright() as p:
        nav = p.chromium.launch()
        page = nav.new_page(viewport={"width": largeur, "height": hauteur}, device_scale_factor=1)
        images = {nom: photo(page, nom, page_html) for nom, page_html in pages.items()}
        bandeau = photo(page, "hors-ligne", hors_ligne_html).crop((0, 0, largeur, round(56 * largeur / 800)))
        nav.close()
    def sauver(img, nom):  # atomique : serveur.py ne lit jamais une image à moitié écrite
        tmp = sortie / f"{nom}.tmp"
        img.save(tmp, format="PNG", optimize=True)
        tmp.replace(sortie / nom)

    for nom, img in images.items():
        sauver(img, f"apercu-{nom}.png")
        sauver(img.rotate(-rotation, expand=True), f"ecran-{nom}.png")
        img.paste(bandeau, (0, 0))
        sauver(img.rotate(-rotation, expand=True), f"ecran-{nom}-hl.png")


def en_cache(sortie, nom, ttl, source, *args):
    """Relève une source au plus toutes les `ttl` secondes ; en panne, garde la dernière bonne valeur (24 h max) et ne
    la réinterroge qu'après 2 min (sinon chaque minute paierait ses délais). Cache absent ou abîmé = pas de cache."""
    fichier = sortie / "cache" / f"{nom}.json"
    t = dt.datetime.now().timestamp()
    try:
        vieux = json.loads(fichier.read_text(encoding="utf-8"))
        float(vieux["t"]), vieux["v"]
    except (OSError, ValueError, KeyError, TypeError):
        vieux = None
    bon = vieux["v"] if vieux and vieux["v"] is not None and t - vieux["t"] < 86400 else None
    if vieux and t - vieux["t"] < ttl:
        return vieux["v"]
    if vieux and t - vieux.get("echec", 0) < 120:
        return bon if bon is not None else {"erreur": f"{source.__name__} indisponible"}
    valeur = sur(source, *args)
    fichier.parent.mkdir(exist_ok=True)
    if "erreur" not in valeur:
        ecrire(fichier, json.dumps({"t": t, "v": valeur}, ensure_ascii=False))
        return valeur
    ecrire(fichier, json.dumps({"t": vieux["t"] if vieux else 0, "v": vieux["v"] if vieux else None, "echec": t},
                               ensure_ascii=False))
    return bon if bon is not None else valeur


def ecrire(fichier, contenu):
    """Écriture atomique : la liseuse ne lit jamais un fichier à moitié écrit."""
    tmp = fichier.with_name(fichier.name + ".tmp")
    tmp.write_bytes(contenu if isinstance(contenu, bytes) else contenu.encode("utf-8"))
    tmp.replace(fichier)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--modele", choices=MODELES, default="k4")
    ap.add_argument("--rotation", type=int, choices=(0, 90, 180, 270), default=90,
                    help="degrés dans le sens horaire pour passer du paysage au portrait natif")
    ap.add_argument("--sortie", type=Path, default=Path.home() / "Library/Caches/kindle-dashboard")
    ap.add_argument("--heure", help="heure simulée AAAA-MM-JJTHH:MM (essais)")
    ap.add_argument("--tous", action="store_true", help="rendre tous les écrans (serveur.py, boutons), pas seulement celui du moment")
    ap.add_argument("--sans-cache", action="store_true", help="relever toutes les sources maintenant")
    args = ap.parse_args()
    args.sortie.mkdir(parents=True, exist_ok=True)
    maintenant = dt.datetime.fromisoformat(args.heure).replace(tzinfo=PARIS) if args.heure else dt.datetime.now(PARIS)
    natif_l, natif_h = MODELES[args.modele]
    largeur, hauteur = (natif_h, natif_l) if args.rotation in (90, 270) else (natif_l, natif_h)
    zoom = largeur / 800
    age = lune(maintenant)
    # Relèves espacées (une source par minute serait du gaspillage) : météo 15 min, courrier 2 min, agenda 5 min,
    # abonnés 3 h (la table n8n ne bouge qu'une fois par jour).
    ttl = (lambda s: 0) if args.sans_cache else (lambda s: s)
    sources = {
        "agenda": lambda: en_cache(args.sortie, "agenda", ttl(300), agenda, maintenant, args.sortie),
        "courrier": lambda: en_cache(args.sortie, "courrier-importants", ttl(120), courrier, maintenant),
        "reseaux": lambda: en_cache(args.sortie, "reseaux", ttl(10800), reseaux, maintenant),
        "air": lambda: en_cache(args.sortie, "air", ttl(3600), air, maintenant),
        "citation": lambda: sur(citation, maintenant),
        "concepts": lambda: en_cache(args.sortie, "concepts", ttl(7 * 86400), concepts, maintenant),
        "livre": lambda: en_cache(args.sortie, "livre", ttl(600), livre_du_jour, maintenant, args.sortie),
        "mot": lambda: en_cache(args.sortie, "mot", ttl(600), mot_du_jour, maintenant, args.sortie),
        "nuages": lambda: en_cache(args.sortie, "nuages", ttl(3600), nuages, maintenant),
    }

    def dessin():
        liste = sources["concepts"]()
        if not isinstance(liste, list) or not liste:
            return ecran_dessin(maintenant, {"erreur": "Concepts : Notion indisponible"}, {}, {}, args.sortie)
        c = liste[graine(maintenant, "concept") % len(liste)]
        k = consigne(maintenant, c["concept"])
        o = en_cache(args.sortie, "oeuvre", ttl(300), oeuvre, maintenant, k["famille"], args.sortie)
        return ecran_dessin(maintenant, c, k, o, args.sortie)
    m = en_cache(args.sortie, "meteo-7j", ttl(900), meteo, maintenant)
    c = sources["courrier"]()
    if "erreur" not in c and "importants" not in c:  # cache d'un ancien format
        c = {"erreur": "Courrier : relève en cours"}
    soleil_du_jour = course_du_soleil(maintenant)
    raison, imminent = raison_stations(maintenant, sources["agenda"]())
    sauf = (("courrier",) if c.get("importants") == 0 else ()) + (() if raison else ("stations",)) + \
        (() if heure_photo(maintenant, soleil_du_jour) else ("lumiere",))
    plage, actuel, rang = plage_du_moment(maintenant, sauf=sauf + tuple(INACTIFS))
    if imminent and plage != "nuit":
        actuel = "stations"
    fabriques = {
        "meteo": lambda: ecran_meteo(maintenant, m, age),
        "air": lambda: ecran_air(maintenant, sources["air"]()),
        "agenda": lambda: panneau_agenda(maintenant, sources["agenda"]()),
        "courrier": lambda: panneau_courrier(maintenant, c),
        "reseaux": lambda: panneau_reseaux(maintenant, sources["reseaux"]()),
        "citation": lambda: ecran_citation(maintenant, sources["citation"]()),
        "demain": lambda: panneau_demain(maintenant, sources["agenda"]()),
        "stations": lambda: ecran_stations(maintenant, sur(stations, maintenant, args.sortie), raison),
        "lumiere": lambda: ecran_lumiere(maintenant, soleil_du_jour, sources["nuages"]()),
        "dessin": dessin,
        "livre": lambda: ecran_livre(maintenant, sources["livre"](), args.sortie),
        "mot": lambda: ecran_mot(maintenant, sources["mot"]()),
    }
    meteo_html = colonne_meteo(maintenant, m, age)
    polices = (ICI / "polices/polices.css").read_text(encoding="utf-8").replace("url('polices/", f"url('{(ICI / 'polices').as_uri()}/")
    gabarit = (ICI / "gabarit.html").read_text(encoding="utf-8")
    lissage = "antialiased" if zoom != 1 else "none"  # zoomées, les polices pixel quittent leur grille : mieux vaut lisser
    noms = NAVIGATION if args.tous else [actuel]
    page = (gabarit.replace("{{POLICES}}", polices).replace("{{ZOOM}}", f"{zoom:.4f}").replace("{{LISSAGE}}", lissage)
            .replace("{{HAUTEUR}}", str(round(hauteur / zoom))))
    def contenu(nom):  # un écran qui plante (donnée inattendue) devient un message, les autres sortent quand même
        try:
            return fabriques[nom]()
        except Exception as e:  # noqa: BLE001
            print(f"⚠️ écran {nom} : {type(e).__name__} {str(e)[:120]}", file=sys.stderr)
            return entete(nom.upper()) + "<p>Écran indisponible, nouvel essai à la minute suivante.</p>"

    pages = {nom: page.replace("{{CONTENU}}", ecran(maintenant, nom, contenu(nom), None if nom in PLEIN else meteo_html,
                                                     c.get("importants", 0)))
             for nom in noms}
    hors_ligne = page.replace("{{CONTENU}}", f'<div class="ecran"><div class="hors-ligne"><span class="s24 gras">HORS LIGNE'
                                             f'</span><span>dernières nouvelles du Mac à {maintenant:%H:%M}</span></div></div>')
    rendre(pages, largeur, hauteur, args.rotation, args.sortie, hors_ligne)
    image = (args.sortie / f"ecran-{actuel}.png").read_bytes()
    ecrire(args.sortie / "ecran.png", image)
    empreintes = {nom: hashlib.sha1((args.sortie / f"ecran-{nom}.png").read_bytes()).hexdigest()[:12] for nom in noms}
    # Flash : 0 = partiel ; 1 = complet si l'écran vient de changer (arrivée sur COMPLET_A) ; 2 = complet quoi qu'il
    # arrive (nettoyage de 04:00). serveur.py force 1 quand l'écran a été choisi aux boutons.
    nettoyage = maintenant.strftime("%H:%M") == "04:00"
    flash = {nom: 2 if nettoyage else 1 if nom in COMPLET_A else 0 for nom in noms}
    etat = {"panneau": actuel, "plage": plage, "empreintes": empreintes, "flash": flash, "navigation": NAVIGATION,
            "releve": maintenant.strftime("%H:%M")}
    ecrire(args.sortie / "etat.json", json.dumps(etat, ensure_ascii=False) + "\n")
    empreinte = empreintes[actuel]
    print(f"{args.sortie} · {plage} · panneau du moment : {actuel} · {empreinte}")


if __name__ == "__main__":
    main()
