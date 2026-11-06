#!/bin/sh
# Sans argument (menu KUAL « Tester l'affichage ») : affiche l'image de test embarquée, sans réseau ni arrêt de
# l'interface. Dans tous les cas, écrit diagnostic.txt : ce que la liseuse sait faire, lisible depuis le Mac par
# `python3 liseuse.py 'cat diagnostic.txt'` quand le dashboard tourne.
DIR="$(dirname "$0")"
. "$DIR/config.sh"
. "$DIR/commun.sh"
{
  echo "=== diagnostic du $(date '+%Y-%m-%d %H:%M:%S') (UTC : $(date -u '+%H:%M:%S'))"
  echo "--- busybox et ses commandes"
  busybox 2>&1 | sed -n '1p;/defined functions/,$p'
  for c in wget dd expr hexdump md5sum pkill hwclock mntroot lipc-set-prop gasgauge-info; do
    if existe "$c"; then echo "$c : oui"; else echo "$c : absent"; fi
  done
  echo "pkill -f : $(pkill -f motif-qui-nexiste-pas >/dev/null 2>&1; echo "code $?")"
  echo "batterie : $(gasgauge-info -c 2>&1)"
  echo "wifi : $(lipc-get-prop com.lab126.wifid cmState 2>&1)"
  ifconfig wlan0 2>&1 | grep -i "inet "
  echo "--- entrées"
  ls -l /dev/input/ 2>&1
  cat /proc/bus/input/devices 2>&1
  echo "--- démarrage"
  ls /etc/rc5.d/ 2>&1 | tr '\n' ' '
  echo
  ls -l /etc/init.d/kindle-dashboard 2>&1
  echo "--- eips"
  eips -h 2>&1 | head -30
} > "$DIR/diagnostic.txt" 2>&1
[ "$1" = diagnostic ] || eips -f -g "$DIR/test.png"
