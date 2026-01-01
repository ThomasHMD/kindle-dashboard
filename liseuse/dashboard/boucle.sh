#!/bin/sh
# Boucle d'affichage du Kindle-dashboard, côté liseuse (Kindle 4, firmware 4.1.4, BusyBox 1.7.2), lancée et
# relancée par superviseur.sh. Le Mac fabrique les images ; ici, toutes les INTERVALLE secondes, ou dès qu'une
# touche est pressée, on lit etat.txt et on ne retélécharge l'écran que si son empreinte a changé.
# etat.txt (v2) = « empreinte écran flash taille taille_hl heure_utc epoch version commande » :
#   flash 0 = partiel, 1 = complet si l'écran vient de changer, 2 = complet quoi qu'il arrive (04:00) ;
#   taille, taille_hl = octets de l'écran et de sa variante « hors ligne » (refus d'une image tronquée) ;
#   heure_utc, epoch = l'heure du Mac (horloge remise à l'heure) ; version = celle des scripts publiés par le Mac
#   (« - » : rien de publié) ; commande = identifiant d'une commande à exécuter une fois (« - » sinon), sortie
#   renvoyée au Mac (liseuse.py).
# Codes de sortie lus par superviseur.sh : 3 = scripts mis à jour (tout relancer), 4 = quitter (Menu deux fois),
# 5 = version neuve qui n'a jamais joint le Mac en 5 min, wifi relancé compris (revenir à la précédente).
# Chaque tour écrit l'horloge monotone (/proc/uptime) dans $TMP/battement : le superviseur tue une boucle figée.
# Tout ce qui vient du réseau est vérifié avant usage : une réponse bizarre ne doit jamais arrêter la boucle.

DIR="$(dirname "$0")"
. "$DIR/config.sh"
. "$DIR/commun.sh"
NAV="$TMP/nav"
[ -s "$DIR/serveur.txt" ] && SERVEUR=$(cat "$DIR/serveur.txt")   # adresse retrouvée par chercher_serveur

entier() {  # vrai si $1 est un entier positif
  case "$1" in ''|*[!0-9]*) return 1 ;; esac
}

taille() {
  wc -c < "$1" 2>/dev/null | tr -d ' '
}

battement() {  # « je suis vivante » pour le superviseur, et $up = secondes depuis l'allumage (sans processus lancé)
  read up _reste < /proc/uptime
  up=${up%.*}
  echo "$up" > "$TMP/battement"
}

recuperer() {  # recuperer <url> <fichier> : wget borné à DELAI secondes, le jeton dans le user-agent (pas de --header)
  rm -f "$2"
  borne "$DELAI" wget -q -U "kindle-dashboard/$JETON" -O "$2" "$1" 2>/dev/null
}

attendre() {  # attendre [secondes] : INTERVALLE par défaut, par quarts de seconde, coupé dès qu'une touche est pressée
  i=0
  while [ "$i" -lt $((${1:-$INTERVALLE} * 4)) ] && [ ! -s "$NAV" ]; do
    usleep 250000 2>/dev/null || sleep 1
    i=$((i + 1))
  done
}

lire_touches() {  # appuis notés par touches.sh depuis le dernier passage : sens, code et pas (appuis cumulés)
  sens=""
  code=""
  pas=0
  [ -s "$NAV" ] && mv "$NAV" "$TMP/nav.lu" 2>/dev/null || return 0
  while read s c; do
    code="$c"
    case "$s" in
      suivant) pas=$((pas + 1)) ;;
      precedent) pas=$((pas - 1)) ;;
      quitter) sens=quitter; return 0 ;;
      *) sens="$s"; pas=0 ;;
    esac
  done < "$TMP/nav.lu"
  rm -f "$TMP/nav.lu"
  if [ "$pas" -gt 0 ]; then sens=suivant
  elif [ "$pas" -lt 0 ]; then sens=precedent; pas=$((-pas))
  fi
}

regler_horloge() {  # regler_horloge <AAAA.MM.JJ-hh:mm:ss UTC> <epoch du Mac>
  ici=$(date -u +%s 2>/dev/null)
  entier "$2" && entier "$ici" || return 0
  ecart=$((ici - $2))
  [ "$ecart" -lt 0 ] && ecart=$((-ecart))
  [ "$ecart" -le 30 ] && return 0
  if date -u -s "$1" >/dev/null 2>&1; then
    hwclock -u -w >/dev/null 2>&1
    journal "horloge remise à l'heure du Mac (elle avait ${ecart} s d'écart)"
  else
    journal "horloge : date -s refuse « $1 »"
  fi
}

mettre_a_jour() {  # mettre_a_jour <version> : scripts du Mac téléchargés, vérifiés (taille, md5), l'ancienne version gardée
  m="$TMP/maj"
  rm -rf "$m"
  mkdir -p "$m"
  recuperer "$SERVEUR/liseuse/paquet.txt" "$m/paquet.txt" && [ -s "$m/paquet.txt" ] || return 1
  while read nom somme octets; do
    case "$nom" in ''|*/*|.*) journal "mise à jour : nom refusé « $nom »"; return 1 ;; esac
    if ! recuperer "$SERVEUR/liseuse/$nom" "$m/$nom" || [ "$(taille "$m/$nom")" != "$octets" ]; then
      journal "mise à jour : $nom illisible ou tronqué"; return 1
    fi
    if existe md5sum && [ "$(md5sum < "$m/$nom" | cut -d' ' -f1)" != "$somme" ]; then
      journal "mise à jour : $nom abîmé en route"; return 1
    fi
    battement
  done < "$m/paquet.txt"
  mkdir -p "$DIR/precedent"
  rm -f "$DIR/precedent/noyau.sh"
  for f in "$DIR"/*.sh; do [ "${f##*/}" = noyau.sh ] || cp "$f" "$DIR/precedent/"; done   # le noyau ne bouge jamais
  cp "$DIR/version" "$DIR/precedent/version" 2>/dev/null
  sync
  while read nom somme octets; do
    if ! { cp "$m/$nom" "$DIR/$nom.neuf" && mv "$DIR/$nom.neuf" "$DIR/$nom"; }; then
      journal "mise à jour : copie de $nom ratée, scripts précédents remis"
      for f in "$DIR/precedent/"*.sh; do cp "$f" "$DIR/${f##*/}.neuf" && mv "$DIR/${f##*/}.neuf" "$DIR/${f##*/}"; done
      sync
      return 1
    fi
  done < "$m/paquet.txt"
  echo "$1" > "$DIR/version"
  : > "$DIR/version-a-confirmer"   # effacé après 30 contacts avec le Mac ; d'ici là, retour en arrière au moindre souci
  sync
  journal "scripts mis à jour (version $1), relance"
}

renvoyer() {  # renvoyer <id> <fichier> : sortie d'une commande vers le Mac, une ligne par requête
  # (BusyBox 1.7.2 : wget sans POST et od peu sûr, donc le texte voyage dans l'adresse, encodé par sed ;
  # 400 caractères par ligne au plus ; abandon après 3 lignes perdues de suite : le Mac a disparu).
  tr '\t\r' '  ' < "$2" | cut -c1-400 | {
    n=0
    perdues=0
    while read -r ligne; do
      t=$(echo "x$ligne" | sed -e 's/^x//' -e 's/%/%25/g' -e 's/ /%20/g' -e 's/&/%26/g' -e 's/+/%2B/g' -e 's/#/%23/g' -e 's/?/%3F/g' -e 's/"/%22/g')
      if recuperer "$SERVEUR/retour?id=$1&n=$n&t=$t" "$TMP/retour"; then
        perdues=0
      else
        perdues=$((perdues + 1))
        [ "$perdues" -ge 3 ] && { journal "commande $1 : renvoi abandonné à la ligne $n"; exit 1; }
      fi
      n=$((n + 1))
      battement
    done
  } || return 1
  recuperer "$SERVEUR/retour?id=$1&n=99999&fin=1" "$TMP/retour" || { journal "commande $1 : renvoi raté"; return 1; }
}

executer() {  # executer <id> : commande du Mac (root), une seule fois, bornée à 300 s, sortie renvoyée au Mac
  echo "$1" > "$DIR/commande-faite"   # noté avant : une commande qui redémarre la liseuse ne repart pas en boucle
  recuperer "$SERVEUR/liseuse/commande.sh?id=$1" "$TMP/commande.sh" || { journal "commande $1 : illisible"; return 1; }
  journal "commande $1 du Mac"
  ( cd "$DIR" && export SERVEUR DIR JETON && borne 300 sh "$TMP/commande.sh" ) > "$TMP/commande.out" 2>&1
  c=$?
  { head -599 "$TMP/commande.out"; echo "--- code de sortie $c"; } > "$TMP/commande.txt"   # le code arrive toujours
  rm -f "$TMP/commande.out"
  battement
  renvoyer "$1" "$TMP/commande.txt"
}

relancer_wifi() {
  journal "relance du wifi"
  lipc-set-prop com.lab126.wifid enable 0 >/dev/null 2>&1
  sleep 5
  lipc-set-prop com.lab126.wifid enable 1 >/dev/null 2>&1
  lipc-set-prop com.lab126.cmd wirelessEnable 1 >/dev/null 2>&1
  sleep 30
}

chercher_serveur() {  # le Mac a peut-être changé d'adresse : sonder le réseau local, 32 adresses à la fois
  ip=$(ifconfig wlan0 2>/dev/null | sed -n 's/.*inet addr:\([0-9.]*\).*/\1/p')
  [ -n "$ip" ] || { journal "recherche du Mac : pas d'adresse wifi"; return 1; }
  base=${ip%.*}
  rm -f "$TMP"/sonde.*
  i=1
  while [ "$i" -le 254 ]; do
    borne 4 wget -q -O "$TMP/sonde.$i" "http://$base.$i:$PORT/sonde" >/dev/null 2>&1 &
    [ $((i % 32)) -eq 0 ] && wait   # chaque sonde est bornée : l'attente aussi
    i=$((i + 1))
  done
  wait
  battement
  for f in "$TMP"/sonde.*; do
    if grep -q kindle-dashboard "$f" 2>/dev/null; then
      SERVEUR="http://$base.${f##*.}:$PORT"
      echo "$SERVEUR" > "$DIR/serveur.txt"
      journal "Mac retrouvé : $SERVEUR"
      rm -f "$TMP"/sonde.*
      return 0
    fi
  done
  rm -f "$TMP"/sonde.*
  journal "recherche du Mac sur $base.0/24 : rien"
  return 1
}

derniere=""        # empreinte de l'écran affiché ("" = tout redessiner, flash complet)
dernier_ecran=""
partiels=0         # rafraîchissements partiels depuis le dernier flash complet
hl=""              # « écran empreinte taille » de la variante hors ligne encore à télécharger
echecs=0
contacts=0         # lectures d'état réussies depuis le lancement de cette boucle
tours=0
menu_a=""          # heure (uptime) du premier appui sur Menu
maj_ratee=""       # version dont la mise à jour vient d'échouer, et quand : nouvel essai 10 min plus tard
maj_ratee_a=0
refus_note=""
version_locale=$(cat "$DIR/version" 2>/dev/null)
version_refusee=$(cat "$DIR/version-refusee" 2>/dev/null)   # rendue par un retour en arrière : jamais reprise
journal "boucle lancée, serveur $SERVEUR, version ${version_locale:-inconnue}"
while true; do
  battement
  tours=$((tours + 1))
  # L'économiseur d'écran couperait le wifi : interdit à nouveau chaque heure (powerd a pu redémarrer).
  [ $((tours % 180)) -eq 1 ] && lipc-set-prop com.lab126.powerd preventScreenSaver 1 >/dev/null 2>&1
  lire_touches
  if [ "$sens" = quitter ]; then   # Menu : deux appuis en 6 s (un appui de travers ne coupe pas le dashboard)
    if [ -n "$menu_a" ] && [ $((up - menu_a)) -le 6 ]; then
      journal "touche Menu deux fois : arrêt du dashboard"
      exit 4
    fi
    menu_a=$up
    eips 1 1 "MENU encore une fois : quitter" >/dev/null 2>&1
    derniere="menu"   # écran redessiné (partiel) au tour suivant
    attendre 6
    continue
  fi
  batterie=$(gasgauge-info -c 2>/dev/null | tr -d '% ')
  horloge=$(date -u +%s 2>/dev/null)
  url="$SERVEUR/etat.txt?v=2&batterie=$batterie&horloge=$horloge&version=$version_locale"
  [ -n "$sens" ] && url="$url&nav=$sens&pas=$pas&touche=$code"
  if recuperer "$url" "$TMP/etat.txt" && [ -s "$TMP/etat.txt" ]; then
    [ "$echecs" -ge "$HORS_LIGNE_APRES" ] && journal "de retour en ligne"
    echecs=0
    contacts=$((contacts + 1))
    touch "$TMP/vivant"
    if [ "$contacts" -eq 30 ] && [ -f "$DIR/version-a-confirmer" ]; then
      rm -f "$DIR/version-a-confirmer"
      journal "version $version_locale confirmée (30 contacts avec le Mac sans souci)"
    fi
    read empreinte ecran flash poids poids_hl heure epoch version commande reste < "$TMP/etat.txt"
    regler_horloge "$heure" "$epoch"
    if [ -n "$version" ] && [ "$version" != - ] && [ "$version" != "$version_locale" ] \
       && [ "$version" != "$version_refusee" ] \
       && { [ "$version" != "$maj_ratee" ] || [ $((up - maj_ratee_a)) -ge 600 ]; }; then
      mettre_a_jour "$version" && exit 3
      maj_ratee="$version"
      maj_ratee_a=$up
    fi
    case "$commande" in
      ''|-|*[!0-9a-f]*) ;;
      *) [ "$commande" != "$(cat "$DIR/commande-faite" 2>/dev/null)" ] && executer "$commande" ;;
    esac
    [ "$ecran" = - ] && [ -z "$refus_note" ] && refus_note=1 && journal "le Mac refuse le jeton (fichier jeton absent ou faux) : écrans fermés"
    case "$ecran" in ''|*[!a-z]*) ecran="" ;; esac
    if [ -n "$ecran" ] && entier "$poids" && [ "$empreinte" != "$derniere" ]; then
      if recuperer "$SERVEUR/ecran.png?p=$ecran&e=$empreinte" "$TMP/ecran.png" && [ "$(taille "$TMP/ecran.png")" = "$poids" ]; then
        # Flash complet (net, 1 s de noir) : au premier affichage, à 04:00, aux changements de la rotation, et après
        # 6 partiels. Écran choisi aux boutons : partiel, plus vif ; la rémanence est effacée au flash suivant.
        if [ -z "$derniere" ] || [ "$flash" = 2 ] || [ "$partiels" -ge 6 ] \
           || { [ "$flash" = 1 ] && [ "$ecran" != "$dernier_ecran" ] && [ -z "$sens" ]; }; then
          eips -f -g "$TMP/ecran.png" >/dev/null 2>&1
          partiels=0
        else
          eips -g "$TMP/ecran.png" >/dev/null 2>&1
          partiels=$((partiels + 1))
        fi
        [ "$ecran" != "$dernier_ecran" ] && journal "écran $ecran${sens:+ (touche $code)}, batterie $batterie %"
        derniere="$empreinte"
        dernier_ecran="$ecran"
        hl="$ecran $empreinte $poids_hl"
      else
        journal "écran $ecran : téléchargement raté ou tronqué"
      fi
    fi
  else
    echecs=$((echecs + 1))
    if [ "$echecs" -eq "$HORS_LIGNE_APRES" ]; then
      journal "Mac injoignable ($SERVEUR) depuis $((echecs * INTERVALLE)) s"
      if [ -s "$TMP/hors-ligne.png" ]; then
        eips -g "$TMP/hors-ligne.png" >/dev/null 2>&1
      else
        eips 1 38 "HORS LIGNE depuis $(date '+%H:%M')" >/dev/null 2>&1
      fi
      derniere=""   # au retour, tout redessiner
    fi
    if [ "$echecs" -ge "$RELANCE_WIFI_APRES" ] && [ $(((echecs - RELANCE_WIFI_APRES) % (3 * RELANCE_WIFI_APRES))) -eq 0 ]; then
      relancer_wifi
      chercher_serveur
    fi
    if [ "$echecs" -gt "$RELANCE_WIFI_APRES" ] && [ "$contacts" -eq 0 ] && [ -f "$DIR/version-a-confirmer" ]; then
      journal "version $version_locale : jamais joint le Mac, retour à la précédente"
      exit 5
    fi
  fi
  # La variante « hors ligne » de l'écran affiché, prête si le Mac se tait ; après les touches en attente.
  if [ -n "$hl" ] && [ ! -s "$NAV" ]; then
    set -- $hl
    if recuperer "$SERVEUR/ecran.png?p=$1&e=$2&hl=1" "$TMP/hl.png" && [ "$(taille "$TMP/hl.png")" = "$3" ]; then
      mv "$TMP/hl.png" "$TMP/hors-ligne.png"
    else
      rm -f "$TMP/hl.png" "$TMP/hors-ligne.png"
    fi
    hl=""
  fi
  attendre
done
