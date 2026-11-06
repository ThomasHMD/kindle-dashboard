#!/bin/sh
# Superviseur du Kindle-dashboard (lancé par demarrer.sh, à la main ou au démarrage de la liseuse) :
# - prépare la liseuse : interface Amazon arrêtée (elle écraserait l'écran), ni veille ni économiseur ;
# - installe le démarrage automatique s'il manque (demarrage-auto.sh) ;
# - lance un lecteur de touches par périphérique d'entrée ;
# - lance boucle.sh et la relance si elle tombe, ou si elle ne bat plus depuis FIGEE secondes (battement : horloge
#   monotone écrite à chaque tour ; une boucle bloquée sur un appel est tuée) ;
# - remet la version précédente des scripts (gardée à chaque mise à jour) et refuse la nouvelle si la boucle tombe
#   trois fois de suite sans avoir joint le Mac entre deux chutes, ou deux fois tant que la version est neuve.
# Il est lui-même lancé et relancé par noyau.sh, la seule pièce jamais mise à jour à distance.
# Codes de sortie de boucle.sh : 3 = scripts mis à jour (on relance tout, superviseur compris), 4 = quitter,
# 5 = version neuve qui n'a jamais joint le Mac (retour à la précédente, comme après trois chutes).
DIR="$(dirname "$0")"
. "$DIR/config.sh"
. "$DIR/commun.sh"
FIGEE=600   # plus long qu'une commande du Mac (300 s) suivie de son renvoi, qu'une mise à jour ou qu'une relance du wifi

preparer() {
  /etc/init.d/framework stop >/dev/null 2>&1
  lipc-set-prop com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1
  { echo powersave > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor; } 2>/dev/null
}

lancer_annexes() {
  tuer "$DIR/touches.sh"
  for d in /dev/input/event*; do
    [ -e "$d" ] && sh "$DIR/touches.sh" "$d" "$TMP/nav" >/dev/null 2>&1 &
  done
}

rendre() {  # rendre la liseuse à l'interface Amazon
  tuer "$DIR/touches.sh"
  lipc-set-prop com.lab126.powerd preventScreenSaver 0 >/dev/null 2>&1
  journal "arrêt, interface Amazon relancée"
  /etc/init.d/framework start >/dev/null 2>&1
}

revenir_en_arriere() {
  [ -d "$DIR/precedent" ] || return 1
  cat "$DIR/version" > "$DIR/version-refusee" 2>/dev/null
  # nouveaux fichiers (cp puis mv) : le shell qui lit un script en cours ne le voit pas changer sous lui
  for f in "$DIR/precedent/"*.sh; do cp "$f" "$DIR/${f##*/}.neuf" && mv "$DIR/${f##*/}.neuf" "$DIR/${f##*/}"; done
  cp "$DIR/precedent/version" "$DIR/version" 2>/dev/null
  sync
  rm -f "$DIR/version-a-confirmer"
  journal "version $(cat "$DIR/version-refusee" 2>/dev/null) refusée : retour à la précédente"
}

rm -f "$TMP/arret"
if [ "$1" = relance ]; then
  journal "superviseur relancé"
else
  journal "démarrage du dashboard"
  preparer
fi
borne 60 sh "$DIR/tester.sh" diagnostic >/dev/null 2>&1         # bornés : un appel bloqué n'empêche pas
borne 60 sh "$DIR/demarrage-auto.sh" installer >/dev/null 2>&1  # le dashboard de démarrer
lancer_annexes
chutes=0
neuves=0
while true; do
  rm -f "$TMP/vivant"
  read up _reste < /proc/uptime
  echo "${up%.*}" > "$TMP/battement"
  sh "$DIR/boucle.sh" &
  b=$!
  while kill -0 "$b" 2>/dev/null; do
    sleep 10
    read up _reste < /proc/uptime
    read vu _reste < "$TMP/battement" 2>/dev/null
    case "$vu" in ''|*[!0-9]*) vu=${up%.*} ;; esac
    if [ $((${up%.*} - vu)) -gt "$FIGEE" ]; then
      journal "boucle figée depuis $((${up%.*} - vu)) s : tuée"
      kill -9 "$b" 2>/dev/null
      break
    fi
  done
  wait "$b"
  code=$?
  [ -f "$TMP/arret" ] && exit 0
  case "$code" in
    3) exec sh "$DIR/superviseur.sh" relance ;;
    4) rendre; exit 0 ;;
    5) revenir_en_arriere && exec sh "$DIR/superviseur.sh" relance ;;
  esac
  if [ -f "$TMP/vivant" ]; then chutes=1; else chutes=$((chutes + 1)); fi
  [ -f "$DIR/version-a-confirmer" ] && neuves=$((neuves + 1))
  journal "boucle tombée (code $code, $chutes fois de suite), relance dans 10 s"
  if { [ "$chutes" -ge 3 ] || [ "$neuves" -ge 2 ]; } && revenir_en_arriere; then
    exec sh "$DIR/superviseur.sh" relance
  fi
  sleep 10
done
