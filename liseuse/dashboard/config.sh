# Réglages de la liseuse, lus par superviseur.sh, boucle.sh et demarrage-auto.sh (mis à jour à distance avec eux).
SERVEUR="http://192.168.1.10:8765"   # adresse du Mac ; s'il change d'adresse, boucle.sh le retrouve (serveur.txt)
PORT=8765
INTERVALLE=20          # secondes entre deux lectures de etat.txt (une touche pressée coupe l'attente)
DELAI=15               # secondes au plus par téléchargement (le wget de busybox n'a pas toujours de délai)
HORS_LIGNE_APRES=6     # échecs d'affilée avant d'afficher « HORS LIGNE » (2 min)
RELANCE_WIFI_APRES=15  # échecs d'affilée avant de relancer le wifi et de chercher le Mac (5 min, puis tous les 15)
export TZ="CET-1CEST,M3.5.0,M10.5.0/3"   # heure de Paris pour le journal ; l'horloge système reste en UTC
