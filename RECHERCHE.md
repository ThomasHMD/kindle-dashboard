# Kindle de 2012 en tableau de bord : accès à l'écran (R&D)

Relevé du 01/01/2026. Légende : **[V]** vérifié (code lu, doc officielle, ou plusieurs retours concordants) ; **[S]** supposé (un seul retour, déduction, extrapolation). Chaque fait porte son lien.

## Verdict

1. Les quatre candidats ont un jailbreak connu, sans compte Amazon pour K4/K5 et Kindle Touch ; le PW1 passe par WinterBreak2, à servir en HTTP depuis le Mac car son navigateur ne passe plus le HTTPS. Sans jailbreak, seul le navigateur expérimental + `~ds` est possible : bon pour un essai, pas pour un affichage permanent.
2. Affichage : `eips` (fourni d'origine) suffit, PNG 8 bits gris sans alpha à la taille native en portrait, interface Amazon arrêtée + `preventScreenSaver 1`, rafraîchissement complet à chaque changement d'écran.
3. Recommandation : **mode B**, la liseuse tire `ecran.png` en HTTP simple sur le Mac toutes les 15 à 20 s, alimentée en permanence par un chargeur secteur USB (pas par le Mac). C'est le schéma de tous les projets entretenus et il ne dépend pas du maillon le moins vérifié (réseau USB du Kindle sous macOS 27).
4. Le mode A (USBNetwork) est crédible sur Mac sans pilote (CDC-ECM), mais plus fragile ; il sert à l'installation et reste le plan de secours si le wifi déçoit.
5. La rotation de 1 min 30 à 5 min du README impose le secteur en continu : surveiller le gonflement d'une batterie de 14 ans, la tenir au frais.

---

## 1. Identifier le modèle et le firmware depuis le Mac

### 1.1 Commandes (Claude, liseuse branchée en câble data)

| Étape | Commande | Ce qu'on lit |
|---|---|---|
| Périphérique USB | `system_profiler SPUSBHostDataType` | Sur ce Mac (macOS 27.0.1), `SPUSBDataType` n'existe plus : `system_profiler -listDataTypes` ne liste que `SPUSBHostDataType` **[V : testé sur le Mac le 01/01/2026]**. Le README du dossier cite encore `SPUSBDataType`, à corriger. |
| Repli | `ioreg -p IOUSB -l -w0` | mêmes champs, bruts |
| Fabricant | Vendor ID `0x1949` | Lab126 (Amazon) ; produit `0x0004` = « Amazon Kindle 3/4/Paperwhite » **[V : [usb.ids](http://www.linux-usb.org/usb.ids)]** |
| Numéro de série | champ « Serial Number » | Le numéro annoncé en USB est celui de « Device Info » : relevé sous Windows sur un DX Graphite en 2011 **[S : un retour, [MobileRead](https://www.mobileread.com/forums/showthread.php?p=1540127)]**, à confirmer au branchement |
| Volume | `diskutil list` puis `ls -la /Volumes/Kindle` | stockage de masse classique sur ces modèles (le MTP n'arrive qu'à la 11e génération) **[V : [kindlemodding](https://kindlemodding.org/jailbreaking/prevent-auto-update/)]** |

### 1.2 Préfixe du numéro de série → modèle

Les 4 premiers caractères suffisent ; seuls les 2 derniers de ces 4 désignent le modèle **[V : [MobileRead, Kindle Serial Numbers](https://wiki.mobileread.com/wiki/Kindle_Serial_Numbers)]**. Codes, noms, dernier firmware et plateforme : **[V : [models.json de kindlemodding](https://kindlemodding.org/models.json)]**. Écran : **[V : wiki MobileRead [Kindle 4](https://wiki.mobileread.com/wiki/Kindle_4), [Kindle Touch](https://wiki.mobileread.com/wiki/Kindle_Touch), [Wikipedia](https://en.wikipedia.org/wiki/Amazon_Kindle) pour le PW1]**.

| Préfixe | Modèle | Nom communauté | N° modèle au dos | Image native (portrait) | ppp | Gris | Dernier firmware publié | Plateforme |
|---|---|---|---|---|---|---|---|---|
| B00E | Kindle 4 (2011, argent, non tactile) | K4 / K4S | D01100 [S] | 600 × 800 | 167 | 16 | **4.1.4** | Yoshi / Tequila |
| B023, 9023 | Kindle 5e gén. « basic » (2012, noir, non tactile) | K4 / K4B | D01100 **[V : [Petroff](https://mpetroff.net/2012/09/kindle-weather-display/), commentaire de l'auteur]** | 600 × 800 | 167 | 16 | **4.1.4** | Yoshi / Sauza |
| B00F, B010, B011, B012 | Kindle Touch (2011) | KT / K5 | D01200 **[V : [kindle-touch-kiosk](https://github.com/bishopdynamics/kindle-touch-kiosk)]** | 600 × 800 (tampon de 608 de large, 8 px cachés **[S : un retour, [MobileRead](https://wiki.mobileread.com/wiki/Eips)]**) | 167 | 16 | **5.3.7.3** | Yoshi / Whitney |
| B024 (wifi), B01B, B01C, B01D (Europe 3G), B01F, B020 | Kindle Paperwhite 1 (2012) | PW / PWG | EY21 [S : forum 2025] | 758 × 1024 visibles **[V : [Online Screensaver](https://github.com/Kuhno92/onlinescreensaverPW2), [kindle-side-card](https://github.com/perduewu-ops/kindle-side-card), commentaire Petroff]** | 212 | 16 | **5.6.1.1** | Wario / Pinot |

Les deux rappels du brief sont confirmés : PW1 plafonne en 5.6.1.1, Kindle 4 et Kindle 5e gén. en 4.1.4 **[V : models.json]**. Le Kindle 5e gén. « basic » de 2012 est un Kindle 4 noir (même logiciel, même jailbreak) **[V : models.json, nom `Kindle4NonTouchBlack`]**.

Indices visuels sans rien brancher : K4/K5 ont un pavé 5 directions et pas d'écran tactile ; le Touch a un écran tactile et un bouton Home ; le PW1 est tactile, éclairé, sans autre bouton que l'alimentation **[S : connaissance générale des modèles]**.

### 1.3 Ce que le volume dit (et ne dit pas)

- `documents/` existe partout ; `.active_content_sandbox` (caché) n'existe que sur les firmwares 5.x récents, les guides WinterBreak insistent pour le copier depuis un Mac **[V : [WinterBreak](https://kindlemodding.org/jailbreaking/WinterBreak/)]**. Sa présence sur un KT/PW1 n'est pas garantie **[S]**.
- Le firmware n'est pas lisible de façon fiable sur le volume : le fichier de version est `/etc/version.txt` sur la partition système, accessible seulement après jailbreak **[V : [MobileRead](https://www.mobileread.com/forums/showthread.php?p=3110592), deux retours]**.
- Capacité visible : 1,25 Go sur K4 **[V : [wiki](https://wiki.mobileread.com/wiki/Kindle_4)]**, environ 3 Go sur le Touch **[V : [wiki](https://wiki.mobileread.com/wiki/Kindle_Touch)]** : un indice de plus entre K4 et KT.

### 1.4 Le firmware : à lire sur l'écran

K4/K5 : Menu → Settings, la version s'affiche en bas ; KT/PW1 : Menu → Settings → Menu → Device Info **[S : chemins usuels, l'assistant kindlemodding donne le chemin des modèles récents « Settings > Device options > Device info », [source](https://github.com/KindleModding/kindlemodding.github.io/blob/main/content/jailbreak-wizard.html)]**. Une photo de cet écran suffit à Claude.

---

## 2. Jailbreak par modèle et firmware, état janvier 2026

Source principale : l'assistant de kindlemodding, dont les règles sont dans [jailbreaks.json](https://github.com/KindleModding/kindlemodding.github.io/blob/main/static/jailbreaks.json) (champ `registration` = compte Amazon requis) **[V : code lu]**.

| Modèle | Firmware couvert | Méthode | Wifi | Compte Amazon | Geste sur la liseuse |
|---|---|---|---|---|---|
| K4 et K5e gén. (B00E, B023) | 2.0 à 5.0, donc tout 4.x | [NiLuJe K4 Jailbreak](https://kindlemodding.org/jailbreaking/Legacy/K4-Jailbreak/), release v1.0.0 du 01/01/2026 sur [GitHub](https://github.com/KindleModding/K4-Jailbreak) | non | non | copier `data.tar.gz`, `ENABLE_DIAGS`, `diagnostic_logs` ; redémarrer ; en mode diagnostic : `D) Exit, Reboot or Disable Diags` → `R) Reboot System` → `Q) To continue` ; un livre « You are Jailbroken » apparaît **[V : page + README]** |
| Kindle Touch (B00F à B012) | 5.0.0 à 5.4.4.2 (dernier publié 5.3.7.3) | [NiLuJe K5 Jailbreak](https://kindlemodding.org/jailbreaking/Legacy/K5-Jailbreak/) (`kindle-5.4-jailbreak.zip`) | non | non | copier tout le zip à la racine ; Menu → Settings → Menu → Update Your Kindle ; `**** JAILBREAK ****` s'affiche ; redémarrer ; puis [hotfix](https://kindlemodding.org/jailbreaking/Legacy/post-jailbreak/setting-up-a-hotfix/) **[V]** |
| PW1 (B024…) | 5.6.1.1 à 5.16.3 | [WinterBreak2](https://kindlemodding.org/jailbreaking/WinterBreak2/) | oui | **non** | dézipper `wb2.zip` à la racine ; ouvrir le navigateur expérimental sur la page WB2 ; bouton Jailbreak **[V]** |
| PW1 | 5.6.1.1 à 5.18.0.2 | [WinterBreak](https://kindlemodding.org/jailbreaking/WinterBreak/) (Mesquito) | oui | **oui** | via la boutique Kindle **[V]** |

### Points durs par modèle

- **PW1, le plus délicat.** Son navigateur 5.6.1.1 n'ouvre plus les pages HTTPS, donc ni la page WB2 officielle ni `https://kindlemodding.org/jailbreaking` **[V : 6 retours concordants, [WinterBreak2 #1](https://github.com/KindleModding/Winterbreak2/issues/1) et [#2](https://github.com/KindleModding/Winterbreak2/issues/2), janvier 2026]**. Contournement confirmé par au moins 5 utilisateurs, dont un en 5.6.1.1 : cloner le dépôt WinterBreak2, `npm install` (ou `pnpm install`), `node ./api/index.js`, puis ouvrir `http://<IP du Mac>:3000` sur la liseuse **[V : même fil]**. Un miroir HTTP communautaire a marché pour un utilisateur : source non maîtrisée, à éviter **[S]**. WinterBreak exige un compte et plusieurs PW1 ne peuvent plus être enregistrés chez Amazon **[V : 2 retours, mêmes fils]**. **Ne jamais réinitialiser un PW1** : un utilisateur qui l'a fait ne peut plus l'enregistrer **[V : #2]**. Après WB2, KUAL refusait de s'ouvrir chez certains PW1 ; réglé en installant `Update_KUALBooklet_v2.7.35_install.bin` par MRPI (`;log mrpi`) **[S : 2 retours dans #2]**.
- **PW1 resté sous 5.4.4.2** (jamais mis à jour, peu probable) : le jailbreak K5 de NiLuJe visait aussi le Paperwhite d'après ses crédits, mais l'assistant ne le propose qu'au Touch **[S]**.
- **K4/K5** : le mode diagnostic contient aussi des entrées de maintenance ; suivre exactement la séquence **[S]**. Le README prévoit un `runme.sh` à la racine, exécuté après le jailbreak, et un désinstalleur `.bin` **[V : [README K4](https://github.com/KindleModding/K4-Jailbreak)]**. KUAL se pose ensuite en `KUAL-KDK-1.0.azw2` dans `documents/`, avec le MRPI « legacy » **[V : [kindlemodding](https://kindlemodding.org/jailbreaking/Legacy/post-jailbreak/installing-kual-mrpi/)]**.
- **Après jailbreak, paquets utiles** (tous chez NiLuJe, fil mis à jour le 01/01/2025) : USBNetwork `kindle-usbnetwork-0.57` (K4) ou `kindle-usbnet-0.22` (KT/PW1), ScreenSavers hack `kindle-ss-0.47` (K4) ou `kindle-linkss-0.25` (KT/PW1), Python, KUAL 2.7.37 **[V : [MobileRead t=225030](https://www.mobileread.com/forums/showthread.php?t=225030)]**.

### Mises à jour automatiques (OTA)

- Ces modèles sont à leur dernier firmware publié depuis des années : une mise à jour ne peut au pire que les amener à 4.1.4, 5.3.7.3 ou 5.6.1.1, couverts par les jailbreaks ci-dessus **[S : déduction depuis models.json]**.
- Avant le jailbreak, kindlemodding conseille de remplir la mémoire (50 à 90 Mo libres) et de supprimer tout `update*.bin` ou `update.bin.tmp.partial` à la racine **[V : [Prevent Automatic Updates](https://kindlemodding.org/jailbreaking/prevent-auto-update/)]**.
- Après un jailbreak « legacy » (firmware ≤ 5.10) : créer un **dossier** nommé `update.bin.tmp.partial` à la racine ; le supprimer pour rétablir les OTA **[V : [Disabling OTA Updates](https://kindlemodding.org/jailbreaking/Legacy/post-jailbreak/disable-ota.html)]**. WinterBreak et WinterBreak2 bloquent les OTA d'eux-mêmes **[V : pages WB/WB2]**.

### Risque de brick et retour arrière

- « Jailbreaking by itself is highly safe » : le risque vient des modifications installées ensuite **[V : [kindlemodding, Recovery](https://kindlemodding.org/jailbreaking/faq/kindle-recovery.html)]** ; le jailbreak K4 se contente d'installer une clé développeur, sans effet sur la batterie ni la stabilité **[V : README K4]**.
- Retour arrière : rétablir les OTA, réinitialiser, réinstaller le même firmware en `.bin` **[V : [Unjailbreaking](https://kindlemodding.org/jailbreaking/faq/unjailbreaking.html)]** ; sur K4, désinstalleur `.bin` par Update Your Kindle **[V : README K4]**. Pour le PW1, la réinitialisation est justement à éviter (voir plus haut).
- Dernier recours matériel : port série sur la carte, utile pour rétrograder ou réparer **[V : [kindle-touch-kiosk, MoreInformation](https://github.com/bishopdynamics/kindle-touch-kiosk/blob/main/MoreInformation.md)]**.

---

## 3. Sans jailbreak

| Élément | État |
|---|---|
| Principe | navigateur expérimental ouvert sur une page servie par le Mac en HTTP simple (pas de HTTPS sur ces navigateurs, voir §2), rafraîchie par JavaScript ou `<meta refresh>` |
| Couper l'économiseur, K4/K5 (4.x) | dans la recherche : `;debugOn`, puis `~disableScreensaver`, puis `;debugOff` ; `;resumeScreensaver` pour revenir **[S : un guide de 2012 sur firmware 4.0x, [kindleclock](https://github.com/thisismyrobot/kindleclock)]** |
| Couper l'économiseur, PW1 | `~ds` dans la recherche, jusqu'au prochain redémarrage ; seul un redémarrage le rétablit **[V : 4 retours 2012-2015 sur PW, PW pub, PW2, PW3, [MobileRead](https://www.mobileread.com/forums/showthread.php?p=2366376)]** |
| Couper l'économiseur, Touch | `~ds` conseillé sur 5.1.2, jamais confirmé dans le fil **[S : [MobileRead](https://www.mobileread.com/forums/showthread.php?p=2182228)]** |
| Retour terrain | un K4 branché en permanence, page en JavaScript pur (pas de jQuery), « during last 3 years or more » **[S : un retour, [forum Home Assistant, 06/2020](https://community.home-assistant.io/t/home-assistant-dashboard-on-kindle/186110)]** |

Limites réelles : `~ds` saute à chaque redémarrage **[V]** ; HTTPS impossible **[V pour le PW1]** ; JavaScript ancien seulement **[S : un retour]** ; barre d'adresse et barre d'outils du navigateur visibles sur KT/PW1, pas de contrôle du mode de rafraîchissement, aucune mise en veille possible donc secteur obligatoire **[S]**. Utile pour un essai sans risque le premier jour, pas pour la cible néo-rétro au pixel près du README.

---

## 4. Afficher une image

### 4.1 eips ou FBInk

| | `eips` | FBInk |
|---|---|---|
| Présence | d'origine, `/usr/sbin/eips` **[V : [kindle-dash](https://github.com/pascalw/kindle-dash/blob/main/src/dash.sh)]** | à installer ; livré avec la plupart des paquets de NiLuJe, et le Universal Hotfix l'utilise **[V : [README FBInk](https://github.com/NiLuJe/FBInk), [Hotfix](https://github.com/KindleModding/Hotfix)]** |
| Modèles | tous | « the full Kindle lineup, starting from the K2 » **[V : README]** ; 554 ★, dernier push 01/01/2026 |
| Image | `eips -g fichier.png` (PNG ou JPG), `-b` pour BMP **[V : [wiki eips](https://wiki.mobileread.com/wiki/Eips)]** | PNG, JPEG, BMP, GIF… avec mise à l'échelle et tramage **[V : README]** |
| Options | `-f` complet (défaut : partiel), `-c` effacer, `-i` infos du tampon (`xres`, `yres`) ; `-x`/`-y`, `-w` (gc16, gl16, du), `-v` **absents sur K4** **[V : wiki ; TRMNL a dû contourner l'absence de `-x -y` sur K4, [PR #39](https://github.com/usetrmnl/trmnl-kindle/pull/39)]** | forme d'onde globale `-W` depuis la v1.14 **[V : [release](https://github.com/NiLuJe/FBInk/releases/tag/v1.14.0)]** |

Conclusion : `eips` suffit, puisque le Mac livre l'image prête. FBInk ne sert que si `eips` refuse un fichier ou pour écrire un petit texte par-dessus (heure de la dernière relève, batterie) **[S]**.

### 4.2 Format attendu

- PNG **8 bits gris, sans alpha** : une image couleur ou avec alpha s'affiche déformée **[V : [kindle-dash #14](https://github.com/pascalw/kindle-dash/issues/14), `pngcrush -c 0` corrige]** ; un PNG gris 4 bits est refusé (« 8bit only ») **[V : sur un PW de 11e gén., [TRMNL #19](https://github.com/usetrmnl/trmnl-kindle/issues/19) ; S pour nos modèles]** ; Petroff passait aussi par `pngcrush` pour obtenir « grayscale, no transparency » **[V : [billet](https://mpetroff.net/2012/09/kindle-weather-display/)]**.
- Taille exacte de la dalle, **en portrait natif** : 600 × 800 (K4, K5, KT), 758 × 1024 (PW1) **[V : §1.2 ; le capteur d'écran de kindle-dash travaille en 600 × 800, [screenshot.js](https://github.com/pascalw/kindle-dash/blob/main/docs/screenshotter/screenshot.js)]**. `eips` ne tourne rien : une mise en page paysage se tourne de 90° sur le Mac **[S ; LaraPaper déclare d'ailleurs `rotation => 90` pour ses modèles Kindle, [seed](https://github.com/usetrmnl/larapaper/blob/main/database/migrations/2026_04_12_000000_seed_all_device_models.php)]**. C'est ce que fait déjà `dashboard.py --rotation 90|270`. Vérifier une fois `eips -i` sur la liseuse (KT : tampon de 608 de large).
- 16 niveaux de gris : quantifier sur 0x00, 0x11 … 0xFF côté Mac évite le tramage de la dalle **[S]**.

### 4.3 Complet ou partiel, rémanence

- Partiel (défaut de `eips -g`) : sans flash, mais les traces s'accumulent ; kindle-dash force un complet toutes les 4 partielles (`FULL_DISPLAY_REFRESH_RATE=4`) **[V : [env.sh](https://github.com/pascalw/kindle-dash/blob/main/src/local/env.sh)]** ; Petroff efface deux fois (`eips -c`) avant chaque image « to prevent ghosting » **[V]** ; TRMNL fait `eips -c` puis `eips -g` **[V : [TRMNL.sh](https://github.com/usetrmnl/trmnl-kindle/blob/main/zip_example/TRMNL.sh)]**.
- Pour ce tableau de bord, chaque relève change tout l'écran : `eips -f -g` à chaque changement (un flash toutes les 1 min 30 à 5 min) **[S : recommandation]**.

### 4.4 Empêcher l'interface Amazon d'écraser l'écran, la veille et l'économiseur

| Firmware | Arrêter l'interface | Source |
|---|---|---|
| K4/K5 (4.x) | `/etc/init.d/framework stop` ; Petroff arrêtait aussi `/etc/init.d/powerd stop` (plus aucune veille) | **[V : [kindle-dash](https://github.com/pascalw/kindle-dash/blob/main/src/dash.sh) testé sur K4, [Petroff](https://github.com/mpetroff/kindle-weather-display/blob/master/kindle/init-weather.sh)]** |
| KT/PW1 (5.x) | `/etc/init.d/framework` peut manquer ; tâches upstart : `stop framework` ou `initctl stop framework` ; `stop lab126_gui` sur les firmwares récents | **[V : [kindle-dash #22](https://github.com/pascalw/kindle-dash/issues/22) et [#25](https://github.com/pascalw/kindle-dash/issues/25), [TRMNL #41](https://github.com/usetrmnl/trmnl-kindle/pull/41) en 5.19 ; kindle-side-card sur PW1 relance par `initctl start framework \|\| /etc/init.d/framework start`]** ; commande exacte en 5.3.7.3 / 5.6.1.1 à lire sur l'appareil (`ls /etc/init.d /etc/upstart`) **[S]** |
| Tous | `lipc-set-prop com.lab126.powerd preventScreenSaver 1` (0 pour revenir) ; garde aussi le wifi actif | **[V : [Kindle4NTHacking](https://wiki.mobileread.com/wiki/Kindle4NTHacking), kindle-dash, TRMNL, kindle-side-card]** |
| Retour à la normale | `start framework` (5.x) ou `/etc/init.d/framework start`, ou redémarrer | **[V : kindle-side-card]** |

Deux variantes qui gardent la liseuse utilisable pour lire : Online Screensaver fait de l'image du tableau de bord l'**économiseur d'écran** (l'interface tourne, la liseuse se met en veille normalement) **[V : [README](https://github.com/Kuhno92/onlinescreensaverPW2)]** ; kindle-side-card laisse l'interface et repeint son image toutes les 15 s **[V : [script](https://github.com/perduewu-ops/kindle-side-card)]**. Avec une rotation toutes les quelques minutes, l'arrêt de l'interface reste le plus propre **[S]**.

Démarrage automatique après un redémarrage de la liseuse : `kite` sur K4 **[V : [hass-lovelace-kindle-4](https://github.com/sibbl/hass-lovelace-kindle-4)]** ; kindle-dash ne le fait pas (issue [#21](https://github.com/pascalw/kindle-dash/issues/21) ouverte) **[V]** ; sur 5.x, une tâche upstart ou un lancement par KUAL **[S]**.

---

## 5. Mode A : branchée en USB au Mac

### 5.1 USBNetwork

- Paquets : `kindle-usbnetwork-0.57` pour K4, `kindle-usbnet-0.22` pour KT/PW1, installés par MRPI **[V : [t=225030](https://www.mobileread.com/forums/showthread.php?t=225030)]**.
- Une fois activé, la liseuse ne se présente plus en stockage de masse mais en carte réseau (`volumd useUsbForNetwork 1`) **[V : [script usbnetwork K5](https://github.com/knc1/USBnetworking/blob/master/USBNetwork/src/usbnet/bin/usbnetwork), [kiosk](https://github.com/bishopdynamics/kindle-touch-kiosk/blob/main/MoreInformation.md)]**.
- Adresses par défaut : liseuse `192.168.15.244`, Mac `192.168.15.201`, réglables dans `/mnt/us/usbnet/etc/config` **[V : [README legacy 0.57](https://github.com/chyidl/chyidlTutorial/blob/master/root/raspberrypi/RaspberryPiPrj/KindlePiPrj/kindle-usbnetwork-0.57.N-k3/README_FIRST.txt) (« On the K4, the defaults are… 192.168.15.201 & 192.168.15.244 »), [wiki USBNetwork](https://wiki.mobileread.com/wiki/USBNetwork), kiosk pour le KT]**.
- SSH : en mode USB, dropbear accepte n'importe quel mot de passe, même vide ; en mode wifi, un vrai mot de passe ou une clé est exigé ; clés dans `/mnt/us/usbnet/etc/authorized_keys` ; mot de passe root calculable par `kindletool info $(cat /proc/usid)` **[V : README legacy + kiosk]**.
- Activer au démarrage : fichier vide `auto` dans le dossier `usbnet` (legacy) **[V : README legacy]** ; « Enable SSH at boot » dans KUAL (K5) **[V : kiosk]**.
- Basculer USBNetwork câble branché peut perturber le bus USB de l'ordinateur ; débrancher avant de basculer **[V : 2 sources, README legacy « some devices behave strangely », kiosk « can crash the whole usb bus »]**. L'auteur du kiosk juge l'activation au démarrage peu pratique pour une liseuse branchée en permanence à un ordinateur **[S : un avis]**.
- Recharge : le port USB du Mac alimente et charge quel que soit le mode **[S : comportement USB standard, aucune source explicite trouvée]**.

### 5.2 Compatibilité macOS : CDC-ECM, pas besoin de RNDIS

- Le gadget Linux `g_ether` compilé avec RNDIS se présente en `0525:a4a2` « Ethernet/RNDIS Gadget », avec **deux configurations** : RNDIS en premier (pour Windows), et toujours une configuration CDC-ECM (ou sous-ensemble CDC) **[V : [ether.c, noyau Linux](https://github.com/torvalds/linux/blob/master/drivers/usb/gadget/legacy/ether.c)]**. Le Kindle est vu sous Windows en `VID_0525&PID_A4A2` **[V : [kindle-reading-dashboard](https://github.com/zevisvei/kindle-reading-dashboard/blob/main/docs/usb-networking.md)]**.
- macOS n'a pas de pilote RNDIS, mais prend la configuration CDC Ethernet : NiLuJe écrit qu'avec OS X « you probably don't need to bother » côté pilote, que la liseuse apparaît en « RNDIS/Ethernet Gadget or CDC Ethernet Device », et qu'il faut régler l'interface à la main dans les réglages réseau **[V : README legacy]**.
- Retours Mac : Kindle Touch + macOS Big Sur, SSH par USB obtenu après avoir donné une IP manuelle au Mac (02/2022) **[V : un retour, [MobileRead](https://www.mobileread.com/forums/showthread.php?p=4199304)]** ; le kiosk Kindle Touch conseille « ideally a mac » **[V]** ; un échec M1 / macOS 13.3 en 2023 venait d'une config éditée, d'après NiLuJe **[V : [MobileRead](https://www.mobileread.com/forums/showthread.php?p=4310395)]**.
- Apple Silicon récent : le même gadget `g_ether` d'un Raspberry Pi Zero apparaissait en « RNDIS/Ethernet Gadget » sur un M1 Pro en macOS 15.3 (03/2025) **[S : analogie, [Apple Community](https://discussions.apple.com/thread/256025936)]**. **Aucun retour Kindle sous macOS 26 ou 27 trouvé** : à tester.
- Piège macOS 15 et suivants, « Local Network privacy » : un script lancé par un LaunchAgent peut recevoir « No route to host » vers le réseau local ; les démons root lancés par launchd sont exemptés ; `/usr/bin/ssh` d'Apple passe dans le Terminal **[V : [Apple Developer Forums](https://developer.apple.com/forums/thread/778457), [MacPorts](https://lists.macports.org/pipermail/macports-dev/2025-January/046035.html), [mjtsai, 01/01/2024](https://mjtsai.com/blog/?p=45202)]**. Que le lien USB `192.168.15.x` soit concerné est **[S]**.

### 5.3 Pousser une image (Claude, depuis le Mac)

```sh
ssh root@192.168.15.244 'cat > /tmp/ecran.png && eips -f -g /tmp/ecran.png' < ecran.png
```

Pipe par `cat` plutôt que `scp` : le `scp` récent de macOS passe par SFTP, qu'il faudrait côté liseuse **[S]**. Côté liseuse, au démarrage : interface arrêtée et `preventScreenSaver 1` (§4.4).

### 5.4 Sans réseau : déposer l'image sur le stockage de masse

Possible mais bancal. Tant que le volume est monté sur le Mac, la liseuse est en « USB drive mode » et inutilisable ; elle revient quand on éjecte **[V : [guide utilisateur Kindle](https://www.manualslib.com/manual/446585/Amazon-Kindle.html?page=109)]**. Il faudrait donc monter, copier, éjecter (`diskutil eject`) à chaque écran ; pendant ce temps `/mnt/us` n'est plus lisible par la liseuse, l'écran « USB drive mode » recouvre le tableau de bord, et c'est l'interface Amazon (volumd) qui gère ces bascules, donc on ne peut pas l'arrêter **[S]**. À écarter.

---

## 6. Mode B : en wifi, projets existants

GitHub relevé le 01/01/2026 (`gh api`, README et code lus).

| Projet | ★ | Dernier push | Modèles réellement pris en charge | Fonctionnement | Autonomie annoncée |
|---|---|---|---|---|---|
| [pascalw/kindle-dash](https://github.com/pascalw/kindle-dash) | 1 391 | 01/01/2024 (dernier commit et v1.0.0-beta.4 : 01/01/2022) | **K4 seulement** (« Tested only on a Kindle 4 NT ») ; sur PW, chemin RTC `/sys/devices/platform/mxc_rtc.0/wakeup_enable` et `/etc/init.d/framework` absents ([#25](https://github.com/pascalw/kindle-dash/issues/25), fork [kafisatz](https://github.com/kafisatz/kindle-dash) pour PW3) ; PR Touch [#22](https://github.com/pascalw/kindle-dash/issues/22) jamais fusionnée | arrête l'interface, `preventScreenSaver 1`, télécharge un PNG (binaire `xh` pour le TLS moderne), `eips`, réveil RTC puis `echo mem > /sys/power/state` ; horaire façon cron | K4 : 3 à 4 %/jour à 30 min sur 10 h/jour ; environ 30 jours à 100 relèves/semaine ([#2](https://github.com/pascalw/kindle-dash/issues/2)) |
| [usetrmnl/trmnl-kindle](https://github.com/usetrmnl/trmnl-kindle) | 461 | 01/01/2026 | README : 6e gén. ou plus, testé 10e et 12e ; **K4 ajouté le 01/01/2026**, « Tested on Kindle 4 + local LaraPaper instance » ([PR #39](https://github.com/usetrmnl/trmnl-kindle/pull/39)) ; correctif upstart / `rtc0` en attente ([#41](https://github.com/usetrmnl/trmnl-kindle/pull/41)) | interroge `/api/display` (en-tête = adresse MAC), télécharge le PNG par `curl`, `eips -c` puis `-g`, réveil par `/sys/class/rtc/rtc1/wakealarm` puis veille | « nobody has published measured runtimes » ([#20](https://github.com/usetrmnl/trmnl-kindle/issues/20)) ; « every couple of days » avant les réglages d'énergie ([#35](https://github.com/usetrmnl/trmnl-kindle/issues/35)) |
| [usetrmnl/trmnl-koreader](https://github.com/usetrmnl/trmnl-koreader) | 177 | 01/01/2026 | tout appareil KOReader ; KOReader « Kindle » couvre K4 argent/noir, KT, PW1 ([wiki KOReader](https://github.com/koreader/koreader/wiki/Installation-on-Kindle-devices)) ; méthode conseillée par TRMNL « as of 2026 » | greffon KOReader, mêmes appels `/api/display`, « Keep alive » + veille auto coupée | « a few days and a few weeks » selon réglages |
| Serveurs BYOS : [Terminus](https://github.com/usetrmnl/terminus) / [LaraPaper](https://github.com/usetrmnl/larapaper) | 761 / 443 | 01/01/2026 / 01/01/2026 | côté serveur ; LaraPaper déclare Kindle 7 (800 × 600) et PW 6e gén. (1024 × 768), 8 bits, 256 gris, rotation 90 | Docker, Ruby ou PHP | n/a |
| Online Screensaver (peterson, [MobileRead t=236104](https://www.mobileread.com/forums/showthread.php?t=236104)) et forks [Kuhno92](https://github.com/Kuhno92/onlinescreensaverPW2), [FalconFour](https://github.com/FalconFour/onlinescreensaverPW2), [poja1993](https://github.com/poja1993/onlinescreensaver) | 41 / 21 / 17 | 01/01/2024 / 01/01/2025 / 01/01/2025 | firmware 5 ou plus seulement, donc **pas le K4** ; testé PW2 ; poja1993 sur **Kindle Touch** (`RTC=1`) | KUAL + ScreenSavers hack ; l'image téléchargée devient l'économiseur ; réveil RTC par événements `powerd`, `wget`, wifi coupé après | FalconFour : « nearly a week » sur un Kindle Basic 7e gén. |
| [mpetroff/kindle-weather-display](https://github.com/mpetroff/kindle-weather-display) | 293 | 01/01/2015, archivé | K4 noir 2012 (B023) | cron deux fois par jour, interface et `powerd` arrêtés, `wget` + `eips -c` ×2 + `eips -g` ; serveur SVG → `rsvg-convert` → `pngcrush` | auteur : « only a few days » (non mesuré) ; un lecteur : 6 % par 24 h à 30 min ; a tourné près de 5 ans ([billet](https://mpetroff.net/2012/09/kindle-weather-display/)) |
| [sibbl/hass-lovelace-kindle-4](https://github.com/sibbl/hass-lovelace-kindle-4) (+ serveur [hass-lovelace-kindle-screensaver](https://github.com/sibbl/hass-lovelace-kindle-screensaver), 658 ★) | 404 | 01/01/2026 | **K4** ; prévu pour rester branché ; HTTP seulement, « no TLS or SSL is supported by the Kindle 4 » | `kite` au démarrage, binaire `rtcwake`, gestion batterie et erreurs wifi | non chiffrée |
| [perduewu-ops/kindle-side-card](https://github.com/perduewu-ops/kindle-side-card) | 44 | 01/01/2026 | **PW1 vérifié** (758 × 1024), autres non | extension KUAL, `wget` en HTTP local toutes les 60 s, `eips`, repeint toutes les 15 s sans arrêter l'interface | non chiffrée |
| [nicoh88/kindle-kt3_weatherdisplay_battery-optimized](https://github.com/nicoh88/kindle-kt3_weatherdisplay_battery-optimized) | 105 | 01/01/2020 | KT3 (2016) | arrêt des services, veille STR + réveil RTC, intervalle par jour et heure | **30 à 35 jours** à 57 relèves/jour |
| [bishopdynamics/kindle-touch-kiosk](https://github.com/bishopdynamics/kindle-touch-kiosk) | 47 | 01/01/2022 | Kindle Touch D01200 en 5.3.7.3 | client VNC, interactif | n/a (branché) |

Ce que ces projets apprennent pour nos modèles :

- **Pas de HTTPS moderne** : K4 « no TLS or SSL » **[V : sibbl]** ; `curl` 7.33 d'un PW2 n'atteint pas S3 **[V : [TRMNL #11](https://github.com/usetrmnl/trmnl-kindle/issues/11)]** ; le navigateur du PW1 échoue en HTTPS **[V : §2]** ; le `xh` de kindle-dash plante sur Kindle Keyboard et bute sur les certificats du K4 et du PW Touch **[V : [#24](https://github.com/pascalw/kindle-dash/issues/24), [#22](https://github.com/pascalw/kindle-dash/issues/22)]**. Donc : servir l'image en **HTTP simple sur le réseau local**, jamais une URL publique en clair (sujets de mails, agenda).
- **Wifi** : 802.11 b/g/n, WEP/WPA/WPA2, ni 802.1X ni ad hoc **[V : wiki [K4](https://wiki.mobileread.com/wiki/Kindle_4) et [KT](https://wiki.mobileread.com/wiki/Kindle_Touch)]** ; avant 2021, ni 5 GHz ni WPA3 **[V : [aide Amazon](https://digprjsurvey.amazon.com/csad/help/node/G5HYWUVWRXFSCH7E)]**. Il faut un réseau 2,4 GHz en WPA2 (ou mixte WPA2/WPA3).
- **K4 et mode avion** : sur K4, `lipc-set-prop com.lab126.cmd wirelessEnable 1` ne relance pas toujours le wifi après le mode avion ; démarrer wifi actif **[V : un retour détaillé, PR #39]**.
- **Wifi qui décroche** : seul défaut de Petroff en 5 ans **[V : billet]** ; la boucle côté liseuse doit retenter et afficher une image d'erreur (ce que font TRMNL et sibbl) **[V]**.
- **Battement de cœur** : la liseuse peut ajouter son niveau de batterie à l'URL (FalconFour, sibbl) **[V]** ; le Mac voit ainsi qu'elle tire encore.

---

## 7. Alimentation et usure

### Autonomie en wifi (batterie saine, veille + réveil RTC, wifi coupé entre deux relèves)

Points mesurés : K4, 3 à 4 %/jour à 20 relèves/jour, environ 30 jours à ~100 relèves/semaine **[V : kindle-dash #2]** ; KT3, 30 à 35 jours à 57/jour **[V : nicoh88]** ; Kindle DX, 24 jours à 1/heure hors ligne **[V : kindle-dash #2]**. Extrapolation à partir du K4 (environ 1 %/jour de fond + 0,1 à 0,15 % par relève) **[S]** :

| Relève | Relèves/jour | Autonomie estimée, batterie neuve | Avec une batterie à 60 % de sa capacité |
|---|---|---|---|
| 60 min | 24 | 3 à 4 semaines | 2 à 3 semaines |
| 30 min | 48 | 2 semaines | 1 à 1,5 semaine |
| 15 min | 96 | 1 semaine | 4 à 6 jours |
| Sans veille, wifi allumé | n/a | quelques jours (« every couple of days », TRMNL #35) | 1 à 2 jours |

La capacité restante d'une batterie de 14 ans est inconnue ; 60 % est une hypothèse **[S]**. La rotation prévue au README (cycle de 10 min, écrans de 1 min 30 à 5 min) exclut toute veille : **secteur en continu**.

### Batterie branchée en permanence

- La charge s'arrête quand la batterie est pleine et une recharge d'appoint ne repart qu'en dessous d'un seuil ; « Most users do not remove the AC power, and this practice is safe » **[V : [Battery University BU-808](https://batteryuniversity.com/article/bu-808-how-to-prolong-lithium-based-batteries)]**.
- Mais rester plein est « more stressful than cycling », et le pire est « a fully charged battery at elevated temperatures » ; après 1 an à 25 °C : 80 % de capacité à 100 % de charge contre 96 % à 40 % ; à 40 °C : 65 % contre 85 % **[V : BU-808]**.
- L'auteur du kiosk Kindle Touch déconseille de laisser une liseuse au mur en charge permanente (gonflement en 1 à 2 ans selon lui) **[S : un avis]**. On ne peut pas retirer la batterie : le noyau vérifie la puce de gestion au démarrage et refuse de démarrer sans elle (il faut émuler cette puce avec un microcontrôleur) **[V : même source, code noyau cité]**.
- Donc : liseuse au frais, loin de la sortie d'air du Mac, et contrôle à l'œil tous les mois (écran qui se décolle, dos bombé, odeur) ; si ça gonfle, débrancher et changer la batterie **[S]**. Aucun limiteur de charge logiciel trouvé pour ces modèles **[S : absence de résultat]**.
- Mode B : chargeur secteur USB plutôt que le Mac, car un port data du Mac ferait passer la liseuse en stockage de masse et lui retirerait `/mnt/us` (où vivent les scripts) **[S : déduit du §5.4]**. Un câble « charge seule » sur le Mac revient au même qu'un chargeur **[S]**.

### Rémanence à long terme

- « Kindle E-Ink displays do not suffer from permanent burn-in » ; une image fixe longtemps rend les traces plus visibles ; une rémanence qui résiste à plusieurs rafraîchissements signale un écran défectueux **[V : [iFixit](https://www.ifixit.com/Wiki/Kindle_Paperwhite_12th_Gen_Screen_Ghosting)]**.
- Pour d'autres dalles e-paper (Waveshare, pas Kindle) : rafraîchir au moins toutes les 24 h, un complet après quelques partiels, sinon une image fixe très longue peut laisser une trace « difficult to repair » **[V pour Waveshare, [FAQ IT8951](https://waveshare.com/wiki/Template:IT8951_Epaper_FAQ), [5.79inch](https://www.waveshare.com/wiki/5.79inch_e-Paper_Module_%28B%29_Manual) ; S pour Kindle]**.
- Une rotation toutes les quelques minutes avec rafraîchissement complet est le cas le plus sain ; la nuit, garder au moins une relève par heure plutôt qu'une image figée 8 h **[S]**.

---

## 8. Recommandation

### Lequel des deux modes

**Mode B**, la liseuse tire l'image en HTTP local, posée où l'on veut, sur chargeur secteur. Pourquoi :

1. C'est le chemin de tous les projets vivants (kindle-dash et sibbl sur K4, TRMNL sur K4 depuis janvier 2026, kindle-side-card sur PW1, Online Screensaver sur Touch) : chaque brique est déjà vérifiée sur nos modèles (§6).
2. Il évite le maillon le moins vérifié : le réseau USB du Kindle sous macOS 27, sans aucun retour récent, plus la bascule USB qui perturbe le bus et la confidentialité réseau local de launchd (§5).
3. En panne, il reste simple : Mac éteint, la liseuse garde la dernière image et peut afficher « hors ligne » ; liseuse redémarrée, sa boucle repart seule.
4. Le Mac ne fait que poser `ecran.png` dans un dossier servi en HTTP : `dashboard.py` le produit déjà.

Le mode A reste le plan de secours si le wifi décroche trop (K4) ou si le réseau n'a pas de 2,4 GHz WPA2. Le passage de l'un à l'autre ne change que le transport : même image, même `eips`.

### Mode B, pas à pas

| # | À la main | Depuis le Mac (Claude Code) |
|---|---|---|
| 1 | Brancher la liseuse au Mac en câble data (micro-USB ↔ USB-C). Photographier l'écran Device Info / Settings (version) | `system_profiler SPUSBHostDataType` ; préfixe → modèle (§1.2) ; `ls -la /Volumes/Kindle` |
| 2 | | Télécharger et vérifier le bon jailbreak (§2), copier sur le volume, `diskutil eject`. PW1 : lancer WinterBreak2 en local sur le port 3000 et donner l'URL `http://<IP du Mac>:3000` |
| 3 | Faire le geste du jailbreak : mode diagnostic (K4/K5), « Update Your Kindle » (Touch), navigateur sur l'URL WB2 (PW1, wifi allumé). Ne jamais réinitialiser un PW1 | Lire le résultat sur le volume (livre « You are Jailbroken », dossiers créés) |
| 4 | | Copier hotfix, KUAL, MRPI, USBNetwork (et `update.bin.tmp.partial` en dossier pour les jailbreaks legacy), éjecter |
| 5 | Lancer l'installation : « Update Your Kindle » ou `;log mrpi` ; ouvrir KUAL une fois | Déposer la clé SSH dans `usbnet/etc/authorized_keys`, régler `usbnet/etc/config` : SSH par le wifi, stockage USB conservé |
| 6 | Connecter la liseuse au wifi 2,4 GHz WPA2 ; noter son IP (`;711` dans la recherche, documenté pour les 5.x **[V : [debug commands](https://kindlemodding.org/kindle-hacking/debug-commands.html)]**, sinon la box) | Réserver cette IP dans la box (DHCP) si on le souhaite ; tester `ssh root@<IP>` |
| 7 | | Écrire la boucle côté liseuse, d'après kindle-dash et TRMNL : interface arrêtée (`/etc/init.d/framework stop` ou `stop framework` selon §4.4), `preventScreenSaver 1`, puis toutes les 15 à 20 s : lire un petit `etat.txt`, si l'écran a changé, `wget` de `ecran.png` dans `/tmp` puis `eips -f -g` ; wifi perdu : retenter, puis afficher une marque « hors ligne » par `eips` texte ; battement de cœur avec la batterie (`gasgauge-info -c` sur K4, `lipc-get-prop com.lab126.powerd status` ailleurs) |
| 8 | | Lancement au démarrage : `kite` (K4) ou tâche upstart / KUAL (5.x) ; test de redémarrage |
| 9 | Poser la liseuse sur son support, sur un chargeur secteur USB | Agent launchd sur le Mac : `dashboard.py` régénère, un serveur HTTP statique sert le dossier de sortie ; alerte si la liseuse n'a pas tiré depuis 3 cycles |
| 10 | Un coup d'œil mensuel à la batterie (§7) | Contrôles : relève, image, redémarrage liseuse, coupure wifi, Mac arrêté |

### Mode A, pas à pas (secours)

| # | À la main | Depuis le Mac (Claude Code) |
|---|---|---|
| 1 à 5 | comme le mode B | comme le mode B |
| 6 | Câble débranché, basculer USBNetwork dans KUAL ; activer le démarrage auto (fichier `auto` legacy ou option KUAL) ; rebrancher | Préparer `usbnet/etc/config` (IP par défaut) et la clé SSH avant la bascule |
| 7 | Réglages Système → Réseau → interface « RNDIS/Ethernet Gadget » → IPv4 manuelle `192.168.15.201` / `255.255.255.0` (droits admin) | `ping 192.168.15.244`, `ssh root@192.168.15.244` |
| 8 | | Démarrage côté liseuse : interface arrêtée + `preventScreenSaver 1`. Côté Mac : à chaque changement d'écran, `ssh … 'cat > /tmp/ecran.png && eips -f -g /tmp/ecran.png' < ecran.png`, lancé par un **LaunchDaemon root** pour éviter la confidentialité réseau local (§5.2) |
| 9 | | Tests : redémarrage liseuse (réapparition de l'interface réseau), redémarrage Mac, câble retiré puis remis |

### Incertitudes à trancher une fois le modèle connu

1. Modèle et firmware exacts : ils choisissent la méthode de jailbreak (§2) et la résolution (600 × 800 ou 758 × 1024).
2. PW1 : WinterBreak2 servi en local depuis le Mac fonctionne-t-il chez nous, et KUAL s'ouvre-t-il ensuite ?
3. KT/PW1 : la commande exacte pour arrêter l'interface en 5.3.7.3 / 5.6.1.1 (init.d ou upstart).
4. Le numéro de série du descripteur USB est-il bien celui de Device Info ? (sinon, lecture à l'écran)
5. Wifi de la maison : un 2,4 GHz en WPA2 est-il disponible ?
6. Mode A seulement : macOS 27 voit-il l'interface CDC-ECM du Kindle ?
7. État réel de la batterie (gonflement, tenue) : il décide si la liseuse peut rester sur secteur en continu.
