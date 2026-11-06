#!/bin/sh
# Arrête le dashboard et rend la liseuse à l'interface Amazon (menu KUAL « Arrêter le dashboard » ; pendant que
# le dashboard tourne, c'est la touche Menu qui fait ça).
DIR="$(dirname "$0")"
. "$DIR/config.sh"
. "$DIR/commun.sh"
touch "$TMP/arret"
tuer "$DIR/noyau.sh"
tuer "$DIR/superviseur.sh"
tuer "$DIR/boucle.sh"
tuer "$DIR/touches.sh"
lipc-set-prop com.lab126.powerd preventScreenSaver 0 >/dev/null 2>&1
journal "arrêt, interface Amazon relancée"
/etc/init.d/framework start >/dev/null 2>&1
