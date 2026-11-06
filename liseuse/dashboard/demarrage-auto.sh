#!/bin/sh
# Démarrage automatique du dashboard à l'allumage de la liseuse : demarrage-auto.sh installer | retirer.
# Installe /etc/init.d/kindle-dashboard, lancé après l'interface Amazon (lien S99 à côté du sien) : il attend 90 s
# puis lance noyau.sh (demarrer.sh s'il n'y a pas de noyau). Si la liseuse est montée en clé USB (branchée au Mac :
# dossier invisible), il attend la fin
# du mode USB (le Mac l'éjecte seul au bout de 2 min, voir serveur.py). Il ne fait rien si
# /mnt/us/dashboard/PAS_DE_DEMARRAGE existe. Pour reprendre la main : touche Menu, ce fichier, le menu KUAL
# « Démarrage automatique : retirer », ou liseuse.py depuis le Mac. `installer` ne touche à rien si tout est en place.
DIR="$(dirname "$0")"
TMP=/tmp/kindle-dashboard
INIT=/etc/init.d/kindle-dashboard
mkdir -p "$TMP"
journal() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') démarrage auto : $*" >> "$DIR/journal.txt"
}

lien_framework=$(ls /etc/rc5.d/S*framework* 2>/dev/null | head -1)
[ -n "$lien_framework" ] || lien_framework=$(ls /etc/rc*.d/S*framework* 2>/dev/null | head -1)
RC=$(dirname "${lien_framework:-/etc/rc5.d/x}")
LIEN="$RC/S99kindle-dashboard"

cat > "$TMP/init" <<'FIN'
#!/bin/sh
# Kindle-dashboard : lance /mnt/us/dashboard/noyau.sh 90 s après l'allumage (installé par demarrage-auto.sh).
D=/mnt/us/dashboard
case "$1" in
  start)
    ( sleep 90
      while [ ! -d $D ]; do sleep 10; done   # montée en clé USB : attendre
      [ -f $D/PAS_DE_DEMARRAGE ] && exit 0
      if [ -f $D/noyau.sh ]; then exec sh $D/noyau.sh >> $D/journal.txt 2>&1; fi
      [ -f $D/demarrer.sh ] && sh $D/demarrer.sh ) >/dev/null 2>&1 &
    ;;
esac
exit 0
FIN

ecrire_racine() {  # la partition système est en lecture seule : l'ouvrir le temps d'écrire
  mntroot rw >/dev/null 2>&1 || mount -o remount,rw / >/dev/null 2>&1
  "$@"
  r=$?
  sync
  mntroot ro >/dev/null 2>&1 || mount -o remount,ro / >/dev/null 2>&1
  return $r
}

poser() {
  cp "$TMP/init" "$INIT" && chmod 755 "$INIT" && ln -sf ../init.d/kindle-dashboard "$LIEN"
}

enlever() {
  rm -f "$LIEN" "$INIT"
}

case "$1" in
  installer)
    if [ -z "$lien_framework" ]; then
      journal "lien de l'interface Amazon introuvable dans /etc/rc*.d, rien installé"
      exit 1
    fi
    [ "$(cat "$TMP/init")" = "$(cat "$INIT" 2>/dev/null)" ] && [ -L "$LIEN" ] && exit 0
    if ecrire_racine poser; then journal "installé ($LIEN)"; else journal "installation ratée"; exit 1; fi
    ;;
  retirer)
    ecrire_racine enlever
    journal "retiré"
    ;;
  *)
    echo "usage : demarrage-auto.sh installer | retirer"
    exit 2
    ;;
esac
