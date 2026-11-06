#!/usr/bin/env python3
"""citations.py : banque de citations du dashboard, tirée de Wikiquote en français (base tierce, CC BY-SA).

Récupère toutes les pages « Modèle:Citation du jour/<j mois aaaa> » de fr.wikiquote.org (3 847 au 01/01/2026, 2 883 gardées
depuis 2007), en extrait citation et auteur (deux formats : modèle à champs depuis 2019 environ, HTML avant),
garde celles qui tiennent sur l'écran, écrit citations.json à côté. Le dashboard prend la citation du jour de
Wikiquote quand elle existe pour la date, sinon une citation de la banque choisie d'après la date.
À relancer de temps en temps (une fois par mois suffit). Bibliothèque standard seule.
"""
import html
import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
API = "https://fr.wikiquote.org/w/api.php"
from dashboard import UA_WIKI as UA  # noqa: E402 (politique Wikimedia : nom et contact, réglé dans config.json)
LONGUEUR_MAX = 230  # au-delà, la citation déborde de l'écran


def api(**p):
    p.update(format="json", formatversion=2, maxlag=5)
    for _ in range(6):
        try:
            req = urllib.request.Request(API, data=urllib.parse.urlencode(p).encode(), headers=UA)
            with urllib.request.urlopen(req, timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429:
                raise
            time.sleep(min(int(e.headers.get("Retry-After", 10)), 60))  # Wikimedia limite le débit
    raise SystemExit("Wikiquote refuse encore (429) : réessayer plus tard")


def liens(wiki):
    """[[cible|texte]], {{w|cible|texte}} → texte : plus aucune barre verticale parasite dans les champs."""
    t = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", wiki)
    return re.sub(r"\{\{w\|(?:[^|}]*\|)?([^|}]*)\}\}", r"\1", t)


def propre(wiki):
    t = re.sub(r"<ref[^>]*>.*?</ref>|<ref[^>]*/>|<!--.*?-->", "", wiki, flags=re.S)
    t = re.sub(r"\{\{[^{}]*\}\}", "", liens(t))
    t = re.sub(r"<br\s*/?>", " ", t)
    t = re.sub(r"<[^>]+>|'{2,}", "", t)
    return re.sub(r"\s+", " ", html.unescape(t)).strip(" «»\"“”")


def extraire(wiki):
    w = liens(re.sub(r"<!--.*?-->", "", wiki, flags=re.S))
    champs = dict(re.findall(r"\|\s*(citation|auteur)\s*=\s*(.*?)(?=\n\s*\||\n?\}\})", w, re.S))
    if champs.get("citation"):
        return propre(champs["citation"]), propre(champs.get("auteur", ""))
    m = re.search(r"\{\{Citation bloc\|(.*?)\|(.*?)(?:\|[^{}]*)?\}\}", w, re.S | re.I)
    if m:
        return propre(m.group(1)), propre(m.group(2))
    m = re.search(r"(?:<i>(.*?)</i>|''(.*?)'')(?:&nbsp;|\s|&mdash;|—|-)*(.*?)</div>", w, re.S | re.I)
    if m:
        return propre(m.group(1) or m.group(2) or ""), propre(m.group(3))
    return None, None


def valide(texte, auteur):
    """Précision avant rappel : au moindre doute sur l'extraction, la citation n'entre pas."""
    if not texte or not auteur or len(texte) > LONGUEUR_MAX or len(auteur) > 45:
        return False
    louche = ("{{", "}}", "[[", "]]", "|", "<", ">", "Vous pouvez")
    return not any(s in texte or s in auteur for s in louche) and texte[0] not in ":;,)" and auteur[0] not in ",:;("


def main():
    titres, suite = [], {}
    while True:
        r = api(action="query", list="allpages", apprefix="Citation du jour/", apnamespace=10, aplimit=500, **suite)
        titres += [x["title"] for x in r["query"]["allpages"] if re.search(r"/\d{1,2} \w+ \d{4}$", x["title"])]
        if "continue" not in r:
            break
        suite = {"apcontinue": r["continue"]["apcontinue"]}
    banque, rejets = [], 0
    for i in range(0, len(titres), 50):
        r = api(action="query", prop="revisions", titles="|".join(titres[i:i + 50]), rvprop="content", rvslots="main")
        for p in r["query"]["pages"]:
            if "revisions" not in p:
                continue
            texte, auteur = extraire(p["revisions"][0]["slots"]["main"]["content"])
            if not valide(texte, auteur):
                rejets += 1
                continue
            jour = p["title"].split("/", 1)[1]
            banque.append({"texte": texte, "auteur": auteur, "jour": jour,
                           "lien": "https://fr.wikiquote.org/wiki/" + urllib.parse.quote(p["title"].replace(" ", "_"))})
        time.sleep(.5)
    (ICI / "citations.json").write_text(json.dumps(banque, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"{len(banque)} citations gardées sur {len(titres)} pages Wikiquote ({rejets} trop longues ou illisibles)")


if __name__ == "__main__":
    main()
