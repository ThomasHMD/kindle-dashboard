#!/usr/bin/env python3
"""insolites.py : banque de l'écran Article insolite, tirée de la page « Wikipédia:Articles insolites » (CC BY-SA).

Relève chaque article de la page avec sa rubrique et sa ligne de présentation, écrit insolites.json à côté. Le résumé
et l'image de l'article sont lus à l'affichage par dashboard.py. À relancer de temps en temps (une fois par mois
suffit). Bibliothèque standard seule.
"""
import json
import re
import urllib.parse
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
from dashboard import UA_WIKI as UA  # noqa: E402 (politique Wikimedia : nom et contact, réglé dans config.json)
PAGE = "Wikipédia:Articles insolites"
LONGUEUR_MAX = 220  # au-delà, la ligne de présentation prend la place du résumé


def propre(s):
    s = re.sub(r"<ref[^>]*?/>|<ref.*?</ref>|<!--.*?-->", "", s, flags=re.S)
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", r"\1", s)
    s = re.sub(r"'{2,}|<[^>]+>", "", s)
    return re.sub(r"\s+", " ", s).strip()


def main():
    q = urllib.parse.urlencode({"action": "parse", "page": PAGE, "prop": "wikitext", "format": "json"})
    req = urllib.request.Request(f"https://fr.wikipedia.org/w/api.php?{q}", headers=UA)
    with urllib.request.urlopen(req, timeout=60) as r:
        texte = json.load(r)["parse"]["wikitext"]["*"]
    articles, vus, rubrique = [], set(), ""
    for l, suite in zip(texte.splitlines(), texte.splitlines()[1:] + [""]):
        t = re.match(r"==\s*([^=]+?)\s*==\s*$", l)
        if t:
            rubrique = t.group(1)
        lien = re.match(r"\|?\s*'''\s*\[\[([^\]|#]+)", l)
        if not lien or not suite.startswith("|") or suite.startswith(("|-", "|}")):
            continue
        titre, accroche = lien.group(1).strip(), propre(suite[1:])
        if titre not in vus and accroche and len(accroche) <= LONGUEUR_MAX:
            vus.add(titre)
            articles.append({"titre": titre, "accroche": accroche, "rubrique": rubrique})
    if len(articles) < 100:
        raise SystemExit(f"{len(articles)} articles seulement : la mise en forme de la page a dû changer")
    (ICI / "insolites.json").write_text(json.dumps(articles, ensure_ascii=False, indent=0) + "\n", encoding="utf-8")
    print(f"{len(articles)} articles")


if __name__ == "__main__":
    main()
