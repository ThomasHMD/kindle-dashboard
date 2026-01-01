#!/bin/sh
# Lit les touches d'un périphérique d'entrée (/dev/input/eventN, un lecteur par périphérique, lancés par
# superviseur.sh) et ajoute « <sens> <code> » au fichier $2, que boucle.sh lit dans le quart de seconde.
# Un évènement Linux fait 16 octets sur ARM 32 bits, soit 8 mots de 16 bits petit-boutistes : secondes (2),
# microsecondes (2), type, code, valeur (2). type 1 = touche ; valeur 1 = appui (2 = répétition, 0 = relâché).
# Rapidité (01/01/2026) : un dd et un hexdump par évènement (33 ms mesurées). printf n'est pas intégré au shell de
# BusyBox 1.7.2, chaque appel coûte 50 ms : l'ancienne version, qui comparait les octets un à un, mettait 1,3 s
# à reconnaître une touche. Le périphérique reste ouvert (descripteur 3) : aucun évènement perdu entre deux lectures.
# Codes du Kindle 4 (KOReader, event_map_kindle4.lua) : 104 / 191 page suivante gauche / droite, 193 / 109 page
# précédente gauche / droite, 103 108 105 106 haut bas gauche droite du 5 voies, 194 son clic, 102 Accueil, 158 Retour,
# 139 Menu. Tous présents dans la table de touches que la liseuse annonce (/proc/bus/input/devices, 01/01/2026).
DEV="$1"
NAV="$2"

while true; do
  [ -r "$DEV" ] || { sleep 30; continue; }
  while true; do
    set -- $(dd bs=16 count=1 <&3 2>/dev/null | hexdump -v -e '8/2 "%u " "\n"')
    [ $# = 8 ] || break   # lecture ratée : rouvrir le périphérique
    [ "$5" = 1 ] && [ "$7" = 1 ] && [ "$8" = 0 ] || continue
    # Pavé dans le sens de lecture : la liseuse est couchée (écran tourné de 90°, `--rotation 90`), son haut est à
    # gauche. Vu de face : → (108, « bas » pour la liseuse) et ↓ (105) = suivant ; ← (103) et ↑ (106) = précédent.
    case "$6" in
      108|105|104|191) sens=suivant ;;
      103|106|193|109) sens=precedent ;;
      102|158|194) sens=auto ;;   # Accueil, Retour, clic : rotation
      139) sens=quitter ;;        # Menu : interface Amazon
      *) sens=autre ;;            # code inconnu : remonté au Mac (liseuse.json)
    esac
    echo "$sens $6" >> "$NAV"   # ajouté : des appuis rapprochés s'additionnent (boucle.sh les compte)
  done 3< "$DEV"   # redirection sur la boucle, pas `exec` : si elle échoue, le shell continue au lieu de quitter
  sleep 5
done
