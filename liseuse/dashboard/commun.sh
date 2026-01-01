# Fonctions communes aux scripts de la liseuse, lues après config.sh. La liseuse a BusyBox 1.7.2 (2007) : pas de
# `command -v`, pkill pas toujours là, wget sans délai ni POST ; tout ici s'en passe.
TMP=/tmp/kindle-dashboard
JOURNAL="$DIR/journal.txt"
mkdir -p "$TMP"
JETON=""   # présenté au Mac dans le user-agent ; posé une fois par liseuse.py (fichier jeton, hors mises à jour)
[ -s "$DIR/jeton" ] && read JETON < "$DIR/jeton"

journal() {
  [ -f "$JOURNAL" ] && [ "$(wc -c < "$JOURNAL")" -gt 200000 ] && mv "$JOURNAL" "$JOURNAL.ancien"
  echo "$(date '+%Y-%m-%d %H:%M:%S') $*" >> "$JOURNAL"
}

# borne <secondes> <commande…> : la commande, tuée au-delà du délai. L'applet timeout de BusyBox 1.7.2 (syntaxe
# `-t`, seule ; `timeout 5` y plante) ne laisse rien derrière lui ; à défaut, un guetteur qui expire seul.
if timeout -t 5 true >/dev/null 2>&1; then
  borne() { _s=$1; shift; timeout -t "$_s" "$@"; }
else
  borne() {
    _s=$1; shift
    "$@" &
    _b=$!
    ( sleep "$_s"; kill -0 "$_b" 2>/dev/null && kill "$_b" 2>/dev/null ) >/dev/null 2>&1 &
    wait "$_b"
  }
fi

existe() {  # existe <commande>
  type "$1" >/dev/null 2>&1
}

tuer() {  # tuer <motif> : les processus dont la ligne de commande contient le motif (pkill -f, sinon ps)
  pkill -f "$1" >/dev/null 2>&1 && return 0
  # (le ps de cette liseuse est celui de procps : sans -o args, il n'affiche que le nom du programme)
  ps -eo pid,args 2>/dev/null | grep "$1" | grep -v grep | while read pid reste; do kill "$pid" 2>/dev/null; done
  return 0
}
