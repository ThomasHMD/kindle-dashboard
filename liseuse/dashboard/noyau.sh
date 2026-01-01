#!/bin/sh
# Noyau du Kindle-dashboard : la seule pièce jamais mise à jour à distance (hors du paquet de serveur.py, posée une
# fois par câble ou par `liseuse.py --pousser`). Lancé par demarrer.sh et le démarrage automatique, il lance
# superviseur.sh et le relance quoi qu'il arrive. Un superviseur qui meurt trois fois de suite en moins de 2 min
# (mise à jour cassée : config.sh ou commun.sh illisibles, superviseur qui plante) : scripts de precedent/ remis,
# version refusée. Ne lit rien de ce qui se met à jour, et ne fait rien d'autre : il doit marcher des années.
DIR=/mnt/us/dashboard
TMP=/tmp/kindle-dashboard
export TZ="CET-1CEST,M3.5.0,M10.5.0/3"   # heure de Paris pour le journal (même valeur que config.sh)
mkdir -p "$TMP"

note() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') noyau : $*" >> "$DIR/journal.txt"
}

note "lancé"
rapides=0
mode="$1"
while true; do
  read debut _reste < /proc/uptime
  sh "$DIR/superviseur.sh" $mode >> "$DIR/journal.txt" 2>&1
  code=$?
  [ "$code" = 0 ] && { note "superviseur arrêté normalement"; exit 0; }   # Menu, arreter.sh
  [ -f "$TMP/arret" ] && exit 0
  mode=relance
  read fin _reste < /proc/uptime
  if [ $((${fin%.*} - ${debut%.*})) -lt 120 ]; then rapides=$((rapides + 1)); else rapides=1; fi
  note "superviseur tombé (code $code, $rapides fois de suite en moins de 2 min)"
  if [ "$rapides" -ge 3 ] && [ -d "$DIR/precedent" ]; then
    cat "$DIR/version" > "$DIR/version-refusee" 2>/dev/null
    for f in "$DIR/precedent/"*.sh; do cp "$f" "$DIR/${f##*/}.neuf" && mv "$DIR/${f##*/}.neuf" "$DIR/${f##*/}"; done
    cp "$DIR/precedent/version" "$DIR/version" 2>/dev/null
    rm -f "$DIR/version-a-confirmer"
    sync
    note "scripts précédents remis, version $(cat "$DIR/version-refusee" 2>/dev/null) refusée"
    rapides=0
  fi
  sleep 10
done
