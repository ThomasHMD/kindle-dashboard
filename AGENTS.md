# Consigne pour une IA : installer ce dashboard

Le dépôt peut être confié à un assistant de code (Claude Code, Codex, Cursor…) avec la consigne « installe ce dashboard sur ma liseuse ». Lire d'abord [`README.md`](README.md) en entier, puis [`RECHERCHE.md`](RECHERCHE.md) pour le modèle de liseuse en jeu.

1. **Identifier la liseuse** avant tout geste : `system_profiler SPUSBHostDataType` (préfixe du numéro de série, `RECHERCHE.md` §1) et la version du firmware lue sur l'écran des réglages. Le jailbreak dépend des deux.
2. **Le jailbreak se fait à la main**, par la personne, en suivant la source officielle (kindlemodding.org). Relire tout script avant de le copier sur la liseuse ; vérifier le sha256 des archives. Ne jamais réinitialiser un Paperwhite 1.
3. **Rien de personnel dans git** : lieu, agendas, stations et identifiants Notion vont dans `config.json`, les clés dans `.env`, tous deux exclus par `.gitignore`. Ne jamais afficher la valeur d'une clé.
4. **Voir avant de brancher** : `python3 demo.py`, puis regarder les PNG de `demo/`.
5. **Scripts de la liseuse** : BusyBox 1.7.2 sur le Kindle 4 (limites dans le README, « Ce que j'ai appris »). Tout script modifié passe par `python3 publier.py` (contrôle `dash -n`) ; ne jamais remplacer `noyau.sh` à distance : c'est lui qui remet la version précédente si une mise à jour casse.
6. **Fini** = `python3 verifier.py` rend le code 0 et l'écran de la liseuse change tout seul.
