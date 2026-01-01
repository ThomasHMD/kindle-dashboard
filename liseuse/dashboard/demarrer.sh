#!/bin/sh
# Lance le dashboard (menu KUAL « Démarrer le dashboard ») : arrête d'abord toute instance déjà là, puis lance le
# noyau (noyau.sh, qui lance et relance le superviseur) en arrière-plan ; le superviseur seul s'il n'y a pas de noyau.
DIR="$(dirname "$0")"
. "$DIR/config.sh"
. "$DIR/commun.sh"
rm -f "$TMP/arret"
tuer "$DIR/noyau.sh"   # le noyau d'abord : sinon il relancerait le superviseur qu'on arrête
tuer "$DIR/superviseur.sh"
tuer "$DIR/boucle.sh"
if [ -f "$DIR/noyau.sh" ]; then
  sh "$DIR/noyau.sh" >> "$JOURNAL" 2>&1 &
else
  sh "$DIR/superviseur.sh" >> "$JOURNAL" 2>&1 &
fi
