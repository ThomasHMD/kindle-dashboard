# Kindle-dashboard : recherche design (paysage, écrans qui tournent)

Relevé du 01/01/2026. Légende : **[V]** vérifié dans la source citée ; **[M]** mesuré ou calculé ici (Chromium de Playwright sur le Mac, mêmes polices que le projet, méthode en §2.5) ; **[S]** supposé, déduction ou avis de design, à confirmer sur la vraie liseuse. L'accès matériel (jailbreak, USB, wifi, `eips`) est dans [RECHERCHE.md](RECHERCHE.md), pas ici. Point de départ jugé : la v1 (portrait) et la v2 (paysage, 4 écrans plein écran, déjà codée dans [dashboard.py](dashboard.py) et [gabarit.html](gabarit.html)).

## Verdict

1. L'identité v1/v2 (VT323 + Silkscreen + Instrument Serif, bandeau inversé, trames) est meilleure que la quasi-totalité des dashboards e-ink publiés : on la garde. Ce qui pèche, c'est la lisibilité à distance et le rendu des pixels, pas le style.
2. Trois paliers de taille selon la distance : 2 m → capitale ≥ 60 px (un seul chiffre héros par écran) ; 1 m → ≥ 28 px ; de près → ≥ 14 px ; plancher 10 px. Silkscreen 12 à 15 px et le texte VT323 de 18 à 22 px de la v2 sortent.
3. Polices pixel à leurs tailles natives (VT323 : multiples de 25 px ; Silkscreen : de 8 px ; icônes 16 × 16 à échelle entière) avec `-webkit-font-smoothing: none` : 0 % de pixel gris parasite mesuré, contre 22 à 42 % aujourd'hui. Instrument Serif garde son lissage.
4. Plus aucun texte gris : sur une dalle Pearl (contraste 10:1), le `#666` de la v2 tombe vers 3:1 et le `#aaa` vers 1,8:1. Le gris sert aux aplats et aux trames, jamais aux lettres.
5. Rotation : la v2 change d'écran 24 fois par heure, 3 à 40 fois plus vite que les défauts de TRMNL (15 min), kindle-dash (30 min) et InkyPi (60 min). Proposé : cycle de 30 min le jour, plages matin / journée / nuit, rafraîchissement partiel et un flash sur 4 changements (2 flashs par heure au lieu de 24).
6. Mieux qu'une rotation plein écran : une **colonne météo fixe (304 px) + un panneau tournant (448 px)**. La météo est vue à chaque coup d'œil et ses pixels ne bougent pas pendant les rafraîchissements partiels.
7. Abonnés : pas de logos redessinés en pixel art (Instagram interdit de modifier son glyphe) ; garder les étiquettes typographiques de la v2, remplacer la courbe normalisée par des barres de gain quotidien.

---

## 1. Dashboards e-ink : ce qui marche visuellement

Captures téléchargées et regardées une à une ; le jugement porte sur l'image, pas sur le README. Étoiles et dernier push relevés par `gh api` le 01/01/2026 **[V]**.

### 1.1 Tableau

| Projet | ★ / dernier push | Capture (lien direct) | Jugement de design |
|---|---|---|---|
| [usetrmnl/trmnl-framework](https://github.com/usetrmnl/trmnl-framework) (design system TRMNL) | 118 / 01/01/2026 | [planche des composants](https://github.com/user-attachments/assets/8a2cd2d5-65d3-4881-978a-cd9af0e0c53b) | Le système le plus abouti du domaine. Un vocabulaire court : `value` (grand chiffre) + `label`, `title_bar`, `item` avec une barre tramée verticale à gauche, filets pointillés, gris rendus en trames (`bg--gray-*`). Tout est pensé pour la grille de pixels (§2.5). C'est la référence de méthode. |
| [usetrmnl/plugins](https://github.com/usetrmnl/plugins), plugin Météo | 238 / 01/01/2026 | [weather](https://trmnl.com/assets/plugin_previews/weather-397bb093.png) | Grille de tuiles sans cadres : chaque bloc est délimité par une fine barre tramée verticale à sa gauche, ce qui structure sans alourdir. Gros « 79° » en grotesque fine, icônes au trait. Barre de titre tramée en bas (icône + nom + lieu). Lisible et calme. |
| idem, YouTube Analytics | idem | [youtube_analytics](https://trmnl.com/assets/plugin_previews/youtube_analytics-2d65d0fe.png) | Le motif « nombre énorme + étiquette » sur trois niveaux (2 héros, puis 2 × 3 secondaires), séparés par des pointillés. Chiffres à chasse fixe (`value--tnums`) **[V : [vue](https://github.com/usetrmnl/plugins/blob/master/lib/youtube_analytics/views/full.html.erb)]**. Le meilleur modèle pour un écran de compteurs. |
| idem, Email Meter | idem | [email_meter](https://trmnl.com/assets/plugin_previews/email_meter-9369bcfc.png) | Même motif, un seul héros (« 220 ») en très grand : se lit à 2 m. Prouve qu'un écran de compteurs n'a besoin d'aucun graphique. |
| idem, Google Calendar | idem | [google_calendar](https://trmnl.com/assets/plugin_previews/google_calendar-c581ee56.png) | Trois colonnes de jours, titres gras, horaires en petit, numéros d'index tramés. Dense et propre à 50 cm, illisible à 2 m : c'est un écran « de près ». |
| idem, Motivational Quote | idem | [motivational_quote](https://trmnl.com/assets/plugin_previews/motivational_quote-c6836974.png) | Contre-exemple : citation en 16 à 18 px perdue au milieu du blanc, aucune hiérarchie. |
| [VisualYeti/wisdom_trmnl](https://github.com/VisualYeti/wisdom_trmnl) (citation) | 1 / 01/01/2026 | [screenshot](https://raw.githubusercontent.com/VisualYeti/wisdom_trmnl/main/screenshot.png) | La bonne citation : serif à environ 50 px sur 800, guillemets gris en ouverture et en fermeture, source dans la barre tramée. Rien d'autre. |
| [lmarzen/esp32-weather-epd](https://github.com/lmarzen/esp32-weather-epd) | 6 329 / 01/01/2026 | [demo-london](https://raw.githubusercontent.com/lmarzen/esp32-weather-epd/main/showcase/demo-london.jpg) | La meilleure météo dense : courbe de température sur 24 h, probabilité de pluie en barres **tramées en points** (et non en gris plein), icônes au trait de grande taille, colonne d'indicateurs à gauche. Montre qu'une trame rend mieux qu'un aplat pour une donnée secondaire. |
| [fatihak/InkyPi](https://github.com/fatihak/InkyPi) | 4 269 / 01/01/2026 | [inky_clock](https://raw.githubusercontent.com/fatihak/InkyPi/main/docs/images/inky_clock.jpg) | Écran couleur (Inky Impression) : visuellement hors sujet pour 16 gris. Intérêt : sa logique de playlists horaires (§3.1). |
| [speedyg0nz/MagInkCal](https://github.com/speedyg0nz/MagInkCal) | 3 267 / 01/01/2024 | [rendu](https://user-images.githubusercontent.com/5581989/134775456-d6bacaca-03c7-4357-af28-7c06aa19ed90.png), [photo](https://user-images.githubusercontent.com/5581989/134661608-bac1f0bf-e7e3-41fe-b92e-37c26dad8fbe.jpg) | Mois en grille aérée, grand numéro du jour. La photo réelle est instructive : de loin, seuls les chiffres de date se lisent, les événements écrits en petit sous chaque date disparaissent. |
| [speedyg0nz/MagInkDash](https://github.com/speedyg0nz/MagInkDash) | 177 / 01/01/2023 | [rendu annoté](https://user-images.githubusercontent.com/5581989/231484018-6ff6a883-3226-42c7-a387-fcef7ee9d49c.png) | Bonne hiérarchie (grand jour du mois, météo à gauche, liste à droite) gâchée par un fond texturé gris : sur e-ink, une texture de fond n'est que du bruit. |
| [pascalw/kindle-dash](https://github.com/pascalw/kindle-dash) (Kindle 4) | 1 391 / 01/01/2024 | [example](https://raw.githubusercontent.com/pascalw/kindle-dash/main/example/example.png) | Boîtes à bord 1 px, sans-serif, icônes : propre mais générique. Son intérêt est la mécanique (cadence, flash, §3.1). |
| [davidhampgonsalves/Life-Dashboard](https://github.com/davidhampgonsalves/Life-Dashboard) (Kindle) | 1 306 / 01/01/2026 | [photo](https://github.com/davidhampgonsalves/life-dashboard/raw/master/example.jpg) | Une ligne par information, pictos noirs : simple. La photo montre surtout la **rémanence** : le texte de l'image précédente reste visible en fantôme gris sous « overnight. Low 7 ». Preuve visuelle du coût des rafraîchissements partiels **[M : observé sur la capture]**. |
| [deskbuddy-app/desk-buddy](https://github.com/deskbuddy-app/desk-buddy) (Paperwhite) | 25 / 01/01/2026 | [weather](https://raw.githubusercontent.com/deskbuddy-app/desk-buddy/main/docs/weather.png), [calendar](https://raw.githubusercontent.com/deskbuddy-app/desk-buddy/main/docs/calendar.png) | Le plus « produit » : grotesque grasse, barres min/max (gris clair + noir) façon iOS, colonne « semaine » où la ligne du jour est **inversée** (blanc sur noir). Leçon : l'inversion désigne « maintenant » sans autre code. |
| [terminalbytes/kindle-dashboard](https://github.com/terminalbytes/kindle-dashboard) (Paperwhite, paysage) | 92 / 01/01/2025 | [dash](https://raw.githubusercontent.com/terminalbytes/kindle-dashboard/master/public/dash.png) | Deux colonnes, prévisions heure par heure en liste. Lisible mais monotone : tout au même corps et au même poids. |
| [matopeto/kindle-weather-dashboard](https://github.com/matopeto/kindle-weather-dashboard) (Kindle 4) | 273 / 01/01/2026 | [Kindle 4](https://raw.githubusercontent.com/matopeto/kindle-weather-dashboard/master/screenshot_kindle4.gif) | 600 × 800 : icône géante et chiffre géant, 4 créneaux en dessous. Se lit de loin, mais l'icône mange un tiers de l'écran pour rien. |
| [sibbl/hass-lovelace-kindle-screensaver](https://github.com/sibbl/hass-lovelace-kindle-screensaver) | 658 / 01/01/2026 | [sample](https://raw.githubusercontent.com/sibbl/hass-lovelace-kindle-screensaver/main/assets/sample.png) | Courbes avec aplat gris clair : les gris clairs rendent bien **en grande surface** ; les libellés gris fins, eux, s'effacent. |
| [fberrez/quietdash.com](https://github.com/fberrez/quietdash.com) | 87 / 01/01/2026 | [dashboard](https://raw.githubusercontent.com/fberrez/quietdash.com/main/docs/screenshots/dashboard.png) | « Calm » : heure pixel géante, grille de filets noirs, très peu de chiffres. Mélange police pixel (chiffres) et grotesque (texte), l'équivalent de notre VT323 + Silkscreen. |
| [kimmobrunfeldt/eink-weather-display](https://github.com/kimmobrunfeldt/eink-weather-display) | 339 / 01/01/2023 | [photo réelle](https://raw.githubusercontent.com/kimmobrunfeldt/eink-weather-display/main/docs/closeup.jpg) | Même chaîne que ce projet (HTML + Chrome headless → PNG). La photo montre que les tuiles grises sous les icônes éteignent le contraste et que les trois lignes de texte sous chaque heure sont illisibles à un mètre. |
| [mendhak/waveshare-epaper-display](https://github.com/mendhak/waveshare-epaper-display) | 531 / 01/01/2026 | [photo](https://raw.githubusercontent.com/mendhak/waveshare-epaper-display/master/screenshots/display.png) | Heure géante, date, filet vertical, liste d'événements en gras : sur photo, les grosses lettres noires se lisent de loin. Simple et efficace. |
| [chrisjtwomey/inkplate10-weather-cal](https://github.com/chrisjtwomey/inkplate10-weather-cal) | 129 / 01/01/2026 | [today_dublin](https://raw.githubusercontent.com/chrisjtwomey/inkplate10-weather-cal/main/doc/assets/today_dublin.png) | Carte de la ville en gris clair en fond, fondu en dégradé : très éditorial. Sur 16 gris sans tramage, ce dégradé fera des bandes **[S]**. |
| [alexishida/kindle-dashboard](https://github.com/alexishida/kindle-dashboard) | 304 / 01/01/2026 | [painel](https://raw.githubusercontent.com/alexishida/kindle-dashboard/main/screenshot/painel.jpg) | Barres de progression noires pleines dans des cadres : lisible, style formulaire. |
| [mt-empty/pi-inky-weather-epd](https://github.com/mt-empty/pi-inky-weather-epd) | 104 / 01/01/2026 | [dashboard](https://raw.githubusercontent.com/mt-empty/pi-inky-weather-epd/master/misc/dashboard-default.png) | Couleur, surchargé : contre-exemple pour du gris. |

Aussi vus, sans capture jugée : [aceinnolab/Inkycal](https://github.com/aceinnolab/Inkycal) (1 483 ★, modules empilés, photos de la communauté seulement), [lanrat/homeplate](https://github.com/lanrat/homeplate) (315 ★, client TRMNL pour Inkplate), [eindpunt/awesome-TRMNL](https://github.com/eindpunt/awesome-TRMNL) (173 ★, liste des plugins communautaires).

### 1.2 Ce qui revient chez les réussis

- **Un héros par écran**, en très grand, et au plus trois niveaux de taille (TRMNL Email Meter, quietdash, mendhak).
- **Structure par filets et trames, pas par boîtes** : barre tramée verticale de TRMNL, filets noirs de quietdash, pointillés entre lignes.
- **Le gris va aux surfaces** (barres, aplats de courbe, barre de titre tramée), **le texte reste noir**.
- **Un cadre constant** : la barre de titre au même endroit sur tous les écrans d'une rotation (TRMNL, v2).
- **L'inversion désigne « maintenant »** (deskbuddy, la v1 pour les titres).

Ce qui rate : textures de fond, petits textes secondaires, tuiles grises sous les icônes, couleurs ramenées au gris, dégradés.

---

## 2. Règles de l'e-ink en petit format

### 2.1 Taille du texte selon la distance

Un pixel logique mesure 0,152 mm sur un Kindle 4/5/Touch (167 ppp) et 0,151 mm sur un Paperwhite 1 dessiné en 800 de large puis agrandi ×1,28 : les tableaux valent pour les deux **[M]**. Repères : une lettre au seuil d'acuité (10/10) mesure 5 minutes d'arc et son trait 1 minute **[V : [Snellen](https://en.wikipedia.org/wiki/Snellen_chart)]** ; la lecture fluide demande une hauteur d'x d'au moins 0,2° (12 minutes) **[V : [Legge et Bigelow 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3428264)]** ; un afficheur consulté d'un coup d'œil vise des caractères d'au moins 20 minutes d'arc **[V : [MIL-STD-411](https://aircraftandairframestructuralcompone.emilspec.com/MIL-STD-411/page19.html)]**.

| Distance | Seuil d'acuité (5') | Lecture fluide (x ≥ 12') | Capitale 15' | Capitale 20' (coup d'œil) |
|---|---|---|---|---|
| 0,5 m | 5 px | x 11 px | 14 px | 19 px |
| 1 m | 10 px | x 23 px | 29 px | 38 px |
| 1,5 m | 14 px | x 34 px | 43 px | 57 px |
| 2 m | 19 px | x 46 px | 57 px | 77 px |

**[M]** À 2 m, l'écran entier ne couvre que 3,5° de large : il n'y tient qu'un ou deux éléments lisibles. D'où trois paliers **[S, déduit du tableau]** :

| Palier | Capitale | Ce qu'on y met |
|---|---|---|
| A, de l'autre bout de la pièce (2 m) | ≥ 60 px | un seul héros par écran : température, nombre de non lus |
| B, en passant (1 m) | ≥ 28 px | min/max, heures et titres des rendez-vous du jour, nombres d'abonnés, citation |
| C, de près (50 cm) | ≥ 14 px, plancher 10 px | objets des courriels, lieux, lendemain, éphéméride |

La v1 et la v2 n'ont presque que du palier C : seule la température (VT323 132 puis 196 px, capitale 74 puis 110 px) passe le palier A **[M]**.

### 2.2 Épaisseur de trait

À 1 m, 1 px vaut 0,52 minute d'arc, sous le trait d'une lettre au seuil (1') ; 2 px valent 1,05' **[M]**. Donc : un « pixel de style » = 2 px Kindle minimum pour tout ce qui doit se lire à 1 m, 4 px pour 2 m ; filets de structure 2 px ; le filet de 1 px n'est qu'une décoration de près (pointillés de conduite). Repère amusant : un pixel du Macintosh 128K (512 × 342 sur 9 pouces, 72 ppp **[V : [Wikipédia](https://en.wikipedia.org/wiki/Macintosh_128K)]**) mesure 0,353 mm, soit 2,3 px Kindle **[M]** : dessiner à l'échelle ×2 donne la densité d'un Mac de 1984.

### 2.3 Contraste et nombre de gris utiles

- Dalle E Ink Pearl : contraste 10:1, réflectance 40,6 %, état blanc ≥ 70, état noir ≤ 24, 16 niveaux, mise à jour 120 ms en 1 bit et 450 ms en 4 bits **[V : [MobileRead](https://wiki.mobileread.com/wiki/E_Ink_Pearl)]**. Le blanc est donc un gris clair (papier journal), et tout l'écart noir/blanc tient en environ 46 unités de clarté L*.
- Estimation en supposant les 16 niveaux espacés régulièrement en L* **[S]** : `#444` ≈ 4,5:1 contre le blanc, `#666` (gris texte de la v2) ≈ 3,2:1, `#777` ≈ 2,7:1, `#aaa` (texte « passé » de la v2) ≈ 1,8:1. Pour du texte fin, sous 4,5:1 c'est faible ; sous 2:1, c'est à peine visible.
- Combien de gris distinguer ? Le Minitel 1 faisait toute son interface avec 8 nuances de gris, noir et blanc compris **[V : [Wikipédia](https://fr.wikipedia.org/wiki/Minitel)]** ; la palette de base de TRMNL a 9 gris, son texte secondaire est `#555`, ses bordures discrètes `#CCC`, ses aplats `#BBB` et `#DDD` **[V : [_tokens.scss](https://github.com/usetrmnl/trmnl-framework/blob/main/app/assets/stylesheets/framework/config/_tokens.scss), [_variables_root.scss](https://github.com/usetrmnl/trmnl-framework/blob/main/app/assets/stylesheets/framework/config/_variables_root.scss)]**. Sur de grandes surfaces voisines, 6 à 8 niveaux se séparent ; pour de petits éléments vus à 1 m, compter 4 : noir, gris foncé, gris clair, blanc **[S]**.

Règle : **texte en noir** (`#444` toléré pour un texte secondaire d'au moins 28 px de capitale) ; gris réservés aux surfaces de plus de 8 × 8 px.

### 2.4 Trames, aplats, dégradés

- TRMNL rend ses gris en trames sur les écrans 1 et 2 bits et en aplats sur les écrans 4 bits (16 gris) **[V : [Rendering Modes](https://trmnl.com/framework/docs/3.4/rendering_modes)]**. Sur un Kindle 16 gris, les deux marchent ; la trame est un choix de style.
- Perception : un damier de 1 px (0,15 mm) vaut 0,52' à 1 m, sous le pouvoir séparateur de l'œil, donc il se voit comme un gris uni ; un damier de 2 px (1,05') laisse voir sa texture de près et se fond vers 2 m **[M]**. Donc damier 1 px = « gris 50 % » ; damier 2 px ou plus = texture rétro visible.
- Les trames n'ont que du noir et du blanc : elles passent par les modes rapides 1 bit (DU, A2) qui ignorent les gris **[V : [fbink.h](https://github.com/NiLuJe/FBInk/blob/master/fbink.h)]** ; un aplat gris exige GC16 ou GL16.
- Dégradés : 16 niveaux donnent des marches visibles. `dashboard.py` arrondit chaque pixel au niveau le plus proche sans tramage (`point(lambda v: round(v / 17) * 17)`) **[V : code]**, donc tout dégradé fera des bandes. FBInk recommande des images « dithered down to the eInk palette » **[V : [fbink.h](https://github.com/NiLuJe/FBInk/blob/master/fbink.h)]**. Règle : pas de dégradé ; s'il en faut un, le tramer en amont.

### 2.5 Anticrénelage et tailles natives des polices pixel

TRMNL l'explique : les pixels gris de l'anticrénelage, forcés en noir ou blanc, rendent le texte « randomly bold or distorted » ; ses polices pixel sont dessinées sur la grille et rendues avec `font-smoothing: none`, ses grands chiffres en Inter lissée **[V : [Pixel Perfect](https://trmnl.com/framework/docs/3.4/pixel_perfect), [_variables_root.scss](https://github.com/usetrmnl/trmnl-framework/blob/main/app/assets/stylesheets/framework/config/_variables_root.scss)]**. Sur les écrans 4 bits, TRMNL désactive ses polices pixel-perfect et passe à Inter **[V : [Rendering Modes](https://trmnl.com/framework/docs/3.4/rendering_modes), commentaire de [_fonts.scss](https://github.com/usetrmnl/trmnl-framework/blob/main/app/assets/stylesheets/framework/config/_fonts.scss)]** : sur 16 gris, un texte lissé est propre, et la police pixel reste un choix de style, à condition de la rendre nette.

**Mesure [M]** : chaque police rendue de 8 à 96 px dans le Chromium de Playwright du Mac, passée en 16 gris comme `dashboard.py`, puis part des pixels d'encre qui sont gris. La grille native se lit sur la largeur du fût du « l » rendu à 1 000 px.

| Police | Grille (fût / em) | Tailles nettes | Capitale / em | Pixels gris, lissage normal | Pixels gris, `-webkit-font-smoothing: none` |
|---|---|---|---|---|---|
| VT323 | 0,088 em, grille non carrée héritée du terminal | 25, 50, 75, 100, 150, 200 (capitale entière : 14, 28, 42, 56, 84, 112 px) | 0,56 | 42 % en moyenne | 0 % |
| Silkscreen | 1/8 em | 8, 16, 24, 32, 48 | 0,625 (capitales seules) | 32 % | 0 % |
| Departure Mono | 1/11 em (le README dit « increments of 11px » **[V]**) | 11, 22, 33, 44, 88 | 0,727 | 39 % | 0 % |
| Bedstead (Teletext) | 1/10 em | 10, 20, 30, 40 | 0,70 | 33 % | 0 % |
| Instrument Serif | vectorielle | toutes | 0,72 | 51 % | 0 %, mais crénelée : à garder lissée |

Sur la planche, Silkscreen à 12 px (×1,5) montre des traits de 1 et 2 px mélangés en rendu net et des franges grises en rendu lissé ; à 16 px elle est parfaite. VT323 à 25 px est régulière, à 26 px (taille de la v1) ses colonnes deviennent inégales **[M]**. `-webkit-font-smoothing: none` n'agit que dans Chromium sur macOS **[S]** : c'est notre cas.

Icônes pixel 16 × 16 : même règle, échelle entière (32, 48, 64, 80, 160). La v2 les dessine à 168 et 40 px (×10,5 et ×2,5) : pixels de largeurs inégales **[V : code, `icone(..., 168)` et `icone(..., 40)`]**.

### 2.6 Marges et grille

TRMNL travaille sur 800 × 480 avec une marge et une gouttière de 10 px et quatre dispositions (`full`, `half_horizontal`, `half_vertical`, `quadrant`) **[V : [_variables_root.scss](https://github.com/usetrmnl/trmnl-framework/blob/main/app/assets/stylesheets/framework/config/_variables_root.scss), [vues des plugins](https://github.com/usetrmnl/plugins/tree/master/lib/youtube_analytics/views)]**. Pour nous : unité de 8 px (la grille de Silkscreen ×1), marges de 16 px, gouttière de 16 px **[S]**. Le cadre plastique du Kindle peut mordre de quelques pixels sur les bords : rien d'important à moins de 16 px du bord **[S, à vérifier sur la liseuse]**.

### 2.7 Ce qui rend mal (récapitulatif)

| Rend mal | Pourquoi | À la place |
|---|---|---|
| Texte gris (`#666`, `#777`, `#aaa`) | contraste 1,8 à 3,2:1 sur Pearl **[S]** | noir, hiérarchie par la taille et la casse |
| Texte fin sous 10 px de capitale | sous le seuil d'acuité à 1 m **[M]** | 16 px Silkscreen ou 25 px VT323 minimum |
| Police pixel à taille non native | traits inégaux ou franges grises **[M]** | multiples natifs + lissage coupé |
| Filet gris de 1 px | presque invisible, cassé en trame | filet noir de 2 px ou pointillé noir |
| Dégradé | marches de 16 niveaux **[V code]** | trame ou aplat |
| Texture de fond, photo non tramée | bruit, contraste perdu | fond blanc |
| Grand aplat noir qui change d'un écran à l'autre | laisse le plus de rémanence en partiel **[S]** | aplats noirs aux mêmes endroits sur tous les écrans (bandeau, étiquettes) |

---

## 3. Rotation des écrans

### 3.1 Comment font les autres

| Projet | Unité tournante | Durée | Pondération, horaires | Écran inchangé | Flash |
|---|---|---|---|---|---|
| TRMNL | élément de playlist : plugin plein écran ou « mashup » (écran partagé) | durée propre à chaque élément, qui remplace le taux de l'appareil ; minimum du compte 15 min, 5 min avec TRMNL+ ; « 4 éléments à 15 min → chaque plugin toutes les heures » **[V : [aide](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work)]** | éléments programmés par heure et jour de la semaine **[V : [Smart Playlists, 01/01/2025](https://trmnl.com/blog/smart-playlists)]** ; la pondération passe par les durées | Smart Skip : données identiques → pas de nouveau rendu **[V : [aide](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work)]** | non étudié (firmware) |
| InkyPi | playlist de plugins | intervalle global, défaut 3 600 s **[V : [refresh_task.py](https://github.com/fatihak/InkyPi/blob/main/src/refresh_task.py)]** | playlists à plages horaires ; la plage active la plus courte l'emporte ; tourniquet simple à l'intérieur **[V : [model.py](https://github.com/fatihak/InkyPi/blob/main/src/model.py)]** | même empreinte d'image → pas d'affichage **[V : refresh_task.py]** | sans objet |
| kindle-dash | un écran | cron, défaut `2,32 8-17 * * MON-FRI` (toutes les 30 min, heures de bureau) **[V : [env.sh](https://github.com/pascalw/kindle-dash/blob/main/src/local/env.sh)]** | hors plage : écran « sleeping » | non | un complet toutes les 4 partielles, « to keep the screen clean » **[V : [dash.sh](https://github.com/pascalw/kindle-dash/blob/main/src/dash.sh)]** |
| KOReader | page | sans objet | sans objet | sans objet | un complet toutes les 6 pages par défaut (`DEFAULT_FULL_REFRESH_COUNT = 6`) **[V : [uimanager.lua](https://github.com/koreader/koreader/blob/master/frontend/ui/uimanager.lua)]** |
| v2 actuelle | 4 écrans plein écran | 300 / 120 / 90 / 90 s, cycle de 10 min **[V : `PLAYLIST`]** | aucune | non | [RECHERCHE.md](RECHERCHE.md) §4.3 propose `eips -f` à chaque changement |

Aucun projet ne tire au sort avec des poids : la pondération se fait par la durée de chaque élément et par des plages horaires.

### 3.2 Ce que coûte un rafraîchissement

Modes d'affichage des contrôleurs i.MX (Kindle) **[V : [fbink.h](https://github.com/NiLuJe/FBInk/blob/master/fbink.h)]** :

| Mode | Transition | Durée | Flash | Rémanence |
|---|---|---|---|---|
| GC16 | tout vers tout, 16 gris | ≈ 450 ms | seulement si demandé ; sinon « only changed pixels will update » | la plus faible |
| GL16 | du blanc vers tout, optimisé texte | ≈ 450 ms | non | un peu |
| DU | vers noir et blanc seulement | ≈ 260 ms | jamais | légère ; les gris ne sont pas dessinés |
| A2 | noir et blanc vers noir et blanc | ≈ 120 ms | jamais | oui |
| INIT | vers blanc | ≈ 2 000 ms, plusieurs flashs | oui | efface tout |

- **Partiel** (`eips -g`) : pas de flash, seuls les pixels qui changent bougent, mais les traces s'accumulent (photo de Life-Dashboard, §1.1). **Complet** (`eips -f -g`) : un flash noir d'environ une demi-seconde sur tout l'écran, qui nettoie. Sur Kindle 4, `eips` n'a pas `-x`/`-y` : impossible de ne flasher qu'une zone sans FBInk **[V : [RECHERCHE.md](RECHERCHE.md) §4.1]**.
- **Trop rare** : une image figée longtemps rend ses traces plus tenaces, sans brûlure permanente sur Kindle **[V : iFixit, cité dans [RECHERCHE.md](RECHERCHE.md)]** ; Waveshare demande au moins un rafraîchissement par 24 h, un complet après environ 5 partiels et au moins 180 s entre deux rafraîchissements pour ses dalles **[V pour Waveshare : [2.13inch HAT](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual), [4.26inch FAQ](https://docs.waveshare.com/4.26inch_e-Paper_G/FAQ) ; S pour la Pearl]**.
- **Trop souvent** : le coût n'est pas l'énergie (secteur) mais l'œil. Un flash noir dans une pièce attire le regard comme un mouvement ; l'intérêt de l'e-ink, c'est le calme **[S]**. La v2 avec un flash à chaque changement donne 24 flashs par heure.

### 3.3 Cadence proposée

Avec la disposition recommandée en §3.4 (colonne météo fixe + panneau tournant P1 à P4) :

| Plage | Panneau tournant | Durées | Changements / h |
|---|---|---|---|
| Matin, 06:30 à 09:00 | P1 Agenda, P2 Courrier | 10 min, 5 min (cycle 15 min) | 8 |
| Journée, 09:00 à 23:00 | P1 Agenda, P2 Courrier, P3 Abonnés, P4 Citation | 8, 8, 7, 7 min (cycle 30 min) | 8 |
| Nuit, 23:00 à 06:30 | P1 en version « Demain », fixe | régénéré toutes les 30 min, affiché seulement si l'image a changé | ≤ 2 |

Justification : 7 à 10 min par panneau restent sous le plancher de TRMNL (15 min), mais chaque panneau se voit au moins deux fois par heure ; l'agenda pèse plus le matin ; la citation change une fois par jour, inutile de la montrer plus d'un quart du temps ; la nuit, personne ne regarde **[S]**. La météo, elle, ne tourne plus : elle est toujours là (§3.4), ce qui répond mieux à « la météo reste affichée le plus longtemps » qu'une durée plus longue dans la rotation.

Rafraîchissement **[S, à régler à l'œil sur la liseuse]** :
- **partiel** (`eips -g`) par défaut : les pixels de la colonne météo et du bandeau qui n'ont pas changé ne bougent pas ;
- **complet** (`eips -f -g`) un changement sur 4, comme kindle-dash : en journée, au passage P4 → P1, soit 2 flashs par heure (au lieu de 24) ; et au moins un complet par heure en toutes plages ;
- **nettoyage** à 04:00 : deux `eips -c` puis l'image, comme le font Petroff et TRMNL **[V : [RECHERCHE.md](RECHERCHE.md) §4.3]** ;
- si des traces gênent, passer à un complet sur 2 changements avant de changer le design.

Dans `dashboard.py`, la forme pourrait être :

```python
PLAYLIST = {  # plage → (début, fin, [(panneau, secondes)]) ; la plage la plus courte l'emporte, comme InkyPi
    "matin":   ("06:30", "09:00", [("agenda", 600), ("courrier", 300)]),
    "journee": ("09:00", "23:00", [("agenda", 480), ("courrier", 480), ("reseaux", 420), ("citation", 420)]),
    "nuit":    ("23:00", "06:30", [("demain", 1800)]),
}
COMPLET_TOUS_LES = 4  # un eips -f sur 4 changements d'écran (kindle-dash : 4, KOReader : 6)
```

Heure affichée : avec un changement toutes les 7 min au plus, une heure à la minute serait fausse jusqu'à 7 min. Le bandeau affiche donc « RELEVÉ 08:35 » plutôt qu'une fausse horloge. Une vraie horloge reste possible plus tard : régénérer chaque minute et laisser le partiel ne changer que les chiffres **[S]**.

### 3.4 Colonne météo fixe ou rotation plein écran ?

| | A. Plein écran (v2) | B. v2 + mini-météo dans le bandeau | C. Colonne météo fixe + panneau tournant |
|---|---|---|---|
| Météo au coup d'œil | 50 % du temps (5 min sur 10) | toujours, réduite (icône + température en palier B) | toujours, complète (température en palier A) |
| Surface qui change à chaque rotation | presque tout l'écran | presque tout | 448 × 512 px, soit 48 % de l'écran **[M]** |
| Rémanence | partout | partout | dans le panneau seulement ; la colonne ne bouge qu'avec les données |
| Place par panneau | 768 × 512 | 768 × 470 | 448 × 512 |
| Travail | fait | petit | refonte des 4 écrans |
| Avis | | repli rapide | **recommandé** |

C est l'équivalent d'un « mashup » `half_vertical` de TRMNL **[V : [mashups](https://help.trmnl.com/en/articles/10168132-mashups)]**, avec une moitié qui ne tourne pas. Avec `eips` sur Kindle 4, le flash couvre tout l'écran de toute façon (§3.2) : l'avantage de C tient aux partiels et à la météo toujours visible, pas à la surface flashée **[S]**. La contrainte de 448 px de large est saine : elle force chaque panneau à ne garder que l'essentiel.

---

## 4. Écran « abonnés »

### 4.1 Ce qui existe

- **TRMNL YouTube Analytics** : grille de valeurs `value--xlarge` + `label`, chiffres à chasse fixe, séparateurs pointillés, aucun graphique **[V : [vue](https://github.com/usetrmnl/plugins/blob/master/lib/youtube_analytics/views/full.html.erb), [capture](https://trmnl.com/assets/plugin_previews/youtube_analytics-2d65d0fe.png)]**. Aucun plugin officiel Instagram, TikTok, Facebook ou Threads dans le catalogue TRMNL **[V : [intégrations](https://trmnl.com/integrations)]**.
- **Smiirl** : le compteur d'abonnés physique de référence, un afficheur mécanique à volets de 5 chiffres, un réseau par compteur **[V : [Smiirl Instagram](https://smiirl.com/en/counter/instagram)]**. C'est la bonne métaphore néo-rétro : le chiffre exact qui « tombe ».
- **GitHub** : les compteurs d'abonnés e-ink publiés sont de petits montages ESP32 sans intérêt visuel (≤ 4 ★, par exemple [superwoodle/ink-sub](https://github.com/superwoodle/ink-sub)) **[V : recherche `gh` du 01/01/2026]**. Rien de beau à reprendre en multi-réseaux.
- **v2** : étiquette inversée par réseau, nombre VT323 72 px, Δ 7 j et Δ 30 j, barres tramées sur 30 jours. C'est déjà le meilleur des exemples vus ; trois défauts : chiffres de 72 px hors grille VT323, textes gris (« sur 7 j »), et des barres normalisées entre le minimum et le maximum de chaque réseau, qui font monter Threads (+10 en 30 j) aussi fort qu'Instagram (+1 009) **[M : maquette v2]**.

### 4.2 Logos de marque en pixel art

| Marque | Règle relevée |
|---|---|
| Instagram | glyphe en noir ou en blanc recommandé, recoloriable en aplat ; ne pas le modifier, le redessiner ni le tourner ; n'utiliser que les fichiers fournis par Meta **[V partiel : [page officielle](https://about.meta.com/brand/resources/instagram/icons) lue à travers le résumé de la recherche, la page ne s'ouvre pas sans navigateur]** |
| YouTube | icône en trois versions, couleur, noir monochrome, blanc monochrome ; d'anciennes versions des règles interdisent d'étirer, de tourner ou de modifier le triangle **[V partiel : [brand.youtube](https://brand.youtube), via résumé de recherche]** |
| TikTok | versions monochromes noire et blanche prévues **[V partiel : règles TikTok For Business trouvées seulement sur des hébergements tiers]** |
| Simple Icons (SVG monochromes de logos) | dépôt sous CC0, mais « that doesn't mean to imply that all icons within the project are also CC0 » ; les marques restent aux marques **[V : [DISCLAIMER.md](https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md)]** |

Conclusion : redessiner un logo en pixel art, c'est le modifier, ce qu'Instagram interdit **[S, lecture des règles]**. À la maison, le risque est nul ; mais un dashboard peut finir dans une vidéo **[S]**. Alternative propre et plus cohérente avec le style : **les étiquettes typographiques inversées de la v2** (« INSTAGRAM » en Silkscreen gras blanc sur noir), façon en-tête de page Teletext. Si un pictogramme est voulu : le glyphe monochrome officiel, à au moins 32 px, passé en noir pur sans gris **[S]**.

### 4.3 Règles d'affichage des chiffres

- YouTube arrondit le nombre d'abonnés à trois chiffres significatifs dans l'API depuis 2019 **[V, sources secondaires : [Rival IQ](https://help.rivaliq.com/en/articles/9788197-why-youtube-subscriber-counts-are-rounded), [Tubefilter](https://www.tubefilter.com/2019/09/16/youtubes-abbreviated-subscriber-counts-are-here/amp/)]**. « 12 300 » affiche une précision fausse et produit les marches visibles dans les barres de la v2. Afficher « 12,3 k » avec « ≈ », ou lire le chiffre exact de YouTube Analytics si la source n8n y a accès **[S]**.
- Chiffres à chasse fixe et alignés à droite (VT323 est monospace), séparateur de milliers en espace fine insécable.
- Variation : une seule par ligne, sur 7 jours (le rythme de publication) ; les 30 jours se lisent dans les barres.
- Barres : **gain net par jour** sur 30 jours, ligne de base à zéro, échelle propre à chaque réseau. On voit les jours qui ont rapporté (un reel qui marche) au lieu d'une rampe qui monte toujours.
- Total multi-réseaux : il compte deux fois les gens abonnés à plusieurs réseaux ; le remplacer par « +412 cette semaine » **[S]**.

---

## 5. Néo-rétro : références et polices

### 5.1 Références adaptables à 16 gris

| Référence | Ce qui la définit | Ce qu'on lui prend |
|---|---|---|
| Minitel 1 | 25 lignes de 40 colonnes en vidéotex, 8 nuances de gris, caractères semi-graphiques de 6 gros pixels en 2 × 3 **[V : [Wikipédia](https://fr.wikipedia.org/wiki/Minitel)]** | palette courte (4 à 5 gris), pictogrammes en mosaïque de blocs pleins, bandeau inversé |
| Teletext / Ceefax | grille 40 × 24, palette de 8 couleurs, graphismes 2 × 3 « sixels », double hauteur, police du générateur SAA5050 **[V : [Wikipédia](https://en.wikipedia.org/wiki/Teletext)]** | numéros de page comme repère de la rotation (« P1 » à « P4 »), titres en double hauteur, police Bedstead si l'on veut l'authentique |
| Macintosh 128K (1984) | 512 × 342 monochrome, 72 ppp **[V : [Wikipédia](https://en.wikipedia.org/wiki/Macintosh_128K)]** | échelle ×2 (même densité, §2.2), trames de remplissage 8 × 8, filets noirs de 2 px **[S]** |
| Tableaux Solari | afficheurs à volets « Solari boards », horaires de gares et d'aéroports de 1960 à 1990 environ ; horloge Cifra 3 de Gino Valle en 1965 **[V : [Wikipédia](https://en.wikipedia.org/wiki/Split-flap_display)]** | nombres d'abonnés en tuiles noires, un chiffre par tuile, filet blanc horizontal au milieu de chaque tuile ; c'est aussi le compteur Smiirl (§4.1) |
| Terminaux et DOS | VT323 reprend les glyphes du terminal DEC VT320 **[S, description Google Fonts non relue]** | texte mono, cadres en double filet, puces carrées, curseur bloc |
| Almanach, éphéméride | lever et coucher du soleil, lune, numéro du jour **[S]** | pied de la colonne météo, déjà présent en v1 et v2 |

### 5.2 Polices libres comparées

| Police | Licence | Grille et tailles nettes **[M]** | Chasse du « 0 » **[M]** | Avis e-ink | Usage |
|---|---|---|---|---|---|
| **VT323** (en place) | OFL **[V : README du projet]** | 25, 50, 75, 100, 150, 200 px | 0,40 em : condensée, 66 caractères sur 760 px à capitale 16 | chaleureuse, idéale pour les chiffres ; petites irrégularités de colonnes, invisibles au-delà de 50 cm | chiffres, texte courant |
| **Silkscreen** (en place) | OFL | 8, 16, 24, 32 px | 0,75 em (large, capitales seules) | parfaite à ×2 et ×3, illisible en dessous de 16 px | étiquettes, bandeau |
| **Instrument Serif** (en place) | OFL | vectorielle | 0,46 em | belle en grand ; ses déliés fins grisent sous 32 px | citation seulement, ≥ 32 px |
| Departure Mono | OFL pour la police **[V : [dépôt](https://github.com/rektdeckard/departure-mono)]** | 11, 22, 33, 44, 88 px | 0,64 em | la plus nette et la plus régulière ; plus froide que VT323 | plan B des chiffres |
| Pixel Operator | CC0 **[V : [DaFont](https://www.dafont.com/pixel-operator.font)]** | grille de 16 px **[V : DaFont]** | non mesurée | sobre, sans caractère | plan B du texte |
| Bedstead | domaine public, CC0 ; Debian la range pourtant en non-free **[V : [site](https://bjh21.me.uk/bedstead/)]** | 10, 20, 30, 40 px | 0,60 em | Teletext authentique, sextants inclus | en-têtes « P1 » si thème Ceefax |
| Jersey 10 / 15 / 25 | Google Fonts, donc licence libre **[S]** | grille non entière en px | 0,38 à 0,46 em | grasse, condensée, très jeu vidéo | non |
| Doto | Google Fonts **[S]** | matrice de points | 0,60 em | afficheur de gare ; 61 % de pixels gris en rendu lissé, la pire du lot | gros chiffres seulement, en rendu net |
| Pixelify Sans, Tiny5, Micro 5, Sixtyfour | Google Fonts **[S]** | variables | 0,36 à 1,0 em | Tiny5 et Micro 5 trop petites ; Sixtyfour (Commodore 64) trop large | non |
| Monaspace Neon | OFL **[V : [dépôt](https://github.com/githubnext/monaspace)]** | vectorielle | 0,62 em | propre, mais « code moderne », pas rétro | non |
| IBM Plex Mono | OFL **[V : [dépôt](https://github.com/IBM/plex)]** | vectorielle | 0,60 em | très lisible, rétro IBM discret | texte courant si VT323 lasse |
| Clones de Chicago (Mac) | Chicago est la police système d'Apple ; aucun clone à licence libre vérifiable (paquet [Chicago Kare](https://aur.archlinux.org/packages/ttf-chicago-kare) sans licence lisible) **[V]** | | | | écarter |

Choix : **garder le trio en place**, qui couvre chiffres, étiquettes et citation, et le rendre net (§2.5). Pas de quatrième police. Departure Mono est la seule alternative sérieuse si VT323 déçoit sur la vraie dalle.

---

## 6. Recommandation : maquettes en paysage, 800 × 600 logiques

### 6.1 Système commun

- Grille : unité 8 px ; marges 16 px ; bandeau 40 px + trame 8 px ; corps de y = 72 à y = 584 (512 px) ; **colonne météo x = 16 à 320 (304 px)**, gouttière 16 px avec filet double de 4 px centré, **panneau tournant x = 336 à 784 (448 px)**.
- Encres : `#000` texte et filets ; `#fff` fond ; gris seulement en aplats ou trames (damier 1 px = gris lu de loin ; damier 2 px = texture de près).
- Le bandeau ne change pas d'un panneau à l'autre (seule l'heure du relevé bouge) : l'indicateur de page descend dans le panneau.
- Échelle typographique, rien en dehors :

| Rôle | Police | Taille | Capitale | Palier |
|---|---|---|---|---|
| Température | VT323 | 200 px (150 si 3 caractères, « -12 ») | 112 px | A |
| Héros du panneau (non lus) | VT323 | 150 | 84 | A |
| Nombres d'abonnés | VT323 | 75 | 42 | B (1,5 m) |
| Min/max, créneaux, rendez-vous du jour | VT323 | 50 | 28 | B |
| Citation | Instrument Serif italique, lissée | 48 / 40 / 32 selon la longueur | 35 / 29 / 23 | B |
| Texte courant (objets, lieux, demain) | VT323 | 25 | 14 | C |
| Titres, étiquettes inversées, bandeau | Silkscreen gras | 24 ou 16 | 15 ou 10 | C |
| Micro (éphéméride, unités) | Silkscreen | 16 | 10 | plancher |
| Icônes | grille 16 × 16 | 16, 32, 48, 80 | | |

### 6.2 Écran complet : cadre et colonne météo (fixe)

```
x 16                              320 336                                                 784
y16 ┌─────────────────────────────────────────────────────────────────────────────────────────┐
    │▓▓ JEUDI 29 OCTOBRE ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ RELEVÉ 08:35 ▓▓│ bandeau noir 40 px
y56 │┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊┊│ trame 8 px (rayures 2 px)
y72 │ ┌────────┐                       ║ PANNEAU TOURNANT P1 à P4                             │
    │ │ icône  │  1 0 ▣                ║ 448 × 512                                            │
    │ │ 16×16  │                       ║                                                      │
    │ │  ×5    │                       ║                                                      │
y208│ └────────┘                       ║                                                      │
    │ COUVERT                          ║                                                      │
    │ 9° / 15°         ressenti 9°     ║                                                      │
    │ vent 5 km/h SE · pluie 0 %       ║                                                      │
y316│ ════════════════════════════════ ║                                                      │
    │ 12H  ☁  13°  ▒▒▒▒░░░░   20%      ║                                                      │
    │ 15H  ☁  15°  ▒░░░░░░░    5%      ║                                                      │
    │ 18H  ☾  14°  ░░░░░░░░    0%      ║                                                      │
    │ 21H  ☾  12°  ░░░░░░░░    0%      ║                                                      │
y500│ ──────────────────────────────── ║                                                      │
    │ ▐DEMAIN▌  ☀  6°/14°              ║                                                      │
y560│ ☼ 07:33 › 17:28    ◑    J302     ║                                                      │
y584└─────────────────────────────────────────────────────────────────────────────────────────┘
```

| Élément | Spécification |
|---|---|
| Bandeau | `JEUDI 29 OCTOBRE` Silkscreen gras 24, interlettre 2 px, blanc sur noir ; à droite `RELEVÉ 08:35` Silkscreen 16 |
| Héros | icône 80 px (×5) ; température VT323 200, interlettre -6 px ; degré = carré de 24 px à bord de 6 px |
| État | `COUVERT` Silkscreen gras 24 ; au-delà de 12 caractères (« AVERSES DE NEIGE »), Silkscreen gras 16 |
| Min/max | `9° / 15°` VT323 50 ; `ressenti 9°` VT323 25 ; vent et pluie VT323 25 |
| Créneaux | 4 lignes de 44 px, toutes les 3 h : heure Silkscreen gras 24, icône 32 (×2), température VT323 50, barre de pluie 64 × 16 à bord de 2 px remplie en trame proportionnellement au %, `20%` VT323 25 |
| Demain | étiquette inversée Silkscreen gras 16, icône 32, `6°/14°` VT323 50 |
| Éphéméride | Silkscreen 16 : lever › coucher, icône de lune à la vraie phase (16 px), numéro du jour ; plus de nom de phase en toutes lettres |

### 6.3 P1 Agenda (et version « Demain » la nuit)

```
┌──────────────────────── 448 ─────────────────────────┐
│ ▐AGENDA▌                                ■ □ □ □      │ y72  étiquette Silkscreen gras 16 ; pages : carrés 10 px
│ AUJOURD'HUI                                          │      Silkscreen gras 16
│ 11:30  Piscine                                       │      VT323 50 : heure 100 px + 16 caractères puis « … »
│        Centre aquatique                              │      VT323 25, noir
│ 19:00  Dîner chez Léa                                │      pas 56 px (+ 20 si lieu), 4 rendez-vous max
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │      pointillé noir 2 px
│ DEMAIN                                               │      Silkscreen gras 16
│ 09:00  Dentiste                                      │      VT323 25 (42 caractères), 5 max
│ 14:00  Appel banque                                  │
└──────────────────────────────────────────────────────┘ y584
```

Rendez-vous passés retirés (plus de `#aaa`) ; s'il n'en reste aucun : « Plus rien aujourd'hui » en VT323 25 noir. Nuit : même panneau, titre `DEMAIN`, rendez-vous du lendemain en VT323 50.

### 6.4 P2 Courrier

```
┌──────────────────────── 448 ─────────────────────────┐
│ ▐COURRIER▌                              □ ■ □ □      │
│  3          NON LUS                                  │ VT323 150 (capitale 84) | Silkscreen gras 24
│             11 en boîte                              │ VT323 25
│ ════════════════════════════════════════════════════ │ filet double 4 px
│ ■ CAMILLE DURAND                           08:12     │ puce 12 px pleine = non lu ; Silkscreen gras 16 ; VT323 25
│   Re: Votre commande est en route…                   │ VT323 25 noir, une ligne
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │ pas 52 px, 5 courriels
│ □ MÉDIATHÈQUE                              hier      │ puce vide = lu
│   Rappel : deux livres à rendre…                     │
└──────────────────────────────────────────────────────┘
```

Le héros est le nombre de **non lus** (ce qui appelle une action), pas le total. À zéro : `0` et `TOUT EST LU`. Expéditeur en capitales Silkscreen (34 caractères tiennent). Caractères absents des polices pixel (« 回复 » dans la v2) : les retirer ou les remplacer, sinon une police système s'invite **[S]**.

### 6.5 P3 Abonnés

```
┌──────────────────────── 448 ─────────────────────────┐
│ ▐ABONNÉS▌                +412 CETTE SEMAINE  □ □ ■ □ │ Silkscreen gras 16
│ ▐YOUTUBE▌ ≈                          ±0 / 7 J        │ étiquette inversée | Silkscreen 16
│ 12,3 k     ▁ ▁ ▂ ▁ ▁ ▃ ▁ ▁ ▁ ▂ ▁ ▁ ▁ ▄ ▁ ▁ ▁ ▁ ▂ ▁ │ VT323 75 (capitale 42) | 30 barres de gain/jour
│ ┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄┄ │ pas 88 px × 5 réseaux
│ ▐INSTAGRAM▌                         +313 / 7 J       │
│ 18 205     ▂ ▃ ▂ ▅ ▂ ▁ ▃ ▆ ▂ ▃ ▄ ▂ ▁ ▂ ▃ ▂ ▇ ▃ ▂ ▂ │
│ ▐FACEBOOK▌   ▐TIKTOK▌   ▐THREADS▌  (même motif)      │
└──────────────────────────────────────────────────────┘
```

| Élément | Spécification |
|---|---|
| Nombre | VT323 75, aligné à droite dans 180 px, espace fine insécable entre milliers ; YouTube en « 12,3 k » précédé de « ≈ » |
| Barres | 30 barres de 6 px + 2 px d'écart (240 × 40 px), hauteur = gain net du jour, base à zéro, échelle par réseau ; remplissage damier 2 px, barre du jour en noir plein |
| Variation | une seule, 7 jours, Silkscreen 16 ; signe moins typographique (−) |
| Ordre | fixe (YouTube, Instagram, Facebook, TikTok, Threads) : l'œil apprend la place de chaque ligne |
| Option Solari | chaque chiffre dans une tuile noire de 32 × 52 px, chiffre blanc VT323 75, filet blanc de 2 px à mi-hauteur ; à essayer pour Instagram seul, en héros **[S]** |

### 6.6 P4 Citation

```
┌──────────────────────── 448 ─────────────────────────┐
│ ▐CITATION▌                              □ □ □ ■      │
│ «                                                    │ Instrument Serif 120 px, noir
│ Je fais des photographies complexes                  │ Instrument Serif italique 40 (capitale 29), interligne 1,15
│ parce que j'éprouve le monde, et de                  │ environ 26 caractères par ligne, 7 lignes max
│ plus en plus en vieillissant, comme                  │ ≤ 80 caractères : 48 px ; ≤ 180 : 40 px ; au-delà : 32 px
│ un endroit compliqué et finalement                   │
│ inexplicable. »                                      │
│ ────                                                 │ filet noir 2 × 48 px
│ ALEX WEBB                                            │ Silkscreen gras 24
│ The New York Times (Lens), 2013                      │ VT323 25, noir
└──────────────────────────────────────────────────────┘
```

Guillemets français « » avec espace fine insécable (U+202F), au lieu du “ de la v1 et de la v2. Source et portrait du blog en VT323 25 noir, plus en gris.

### 6.7 À changer dans gabarit.html et dashboard.py (v2 → v3)

| # | Fichier | Changement |
|---|---|---|
| 1 | gabarit.html | `body { -webkit-font-smoothing: none; }` (au lieu de `antialiased`) et `.citation blockquote, .citation .guillemet { -webkit-font-smoothing: antialiased; }` |
| 2 | gabarit.html | tailles : Silkscreen 12, 13, 14, 15, 18, 20 → 16 ou 24 ; VT323 18, 20, 21, 22, 26, 28, 30 → 25 ou 50 ; 72 → 75 ; 92 → 100 ou 150 ; 196 → 200 |
| 3 | gabarit.html | `--gris` et `--clair` interdits pour du texte : `.lieu`, `.sujet`, `.jour`, `.vide`, `.h small`, `.reseau .delta small`, `.citation .source` passent en `var(--encre)` ; `.ligne.passe` disparaît |
| 4 | dashboard.py | icônes à échelle entière : `icone(..., 168)` → 160, `icone(..., 40)` → 32 ou 48 |
| 5 | gabarit.html | deux trames nommées : `.gris50` (damier 1 px, `background-size: 2px 2px`, se lit comme un gris) et `.tramee` actuelle (damier 2 px, texture) ; aucun `linear-gradient` hors trames |
| 6 | les deux | disposition C : `.ecran` en grille `304px 16px 448px`, colonne météo commune à tous les écrans, panneau tournant à droite ; indicateur de pages sorti du bandeau ; `RELEVÉ hh:mm` à droite du bandeau |
| 7 | dashboard.py | écran Agenda + Courrier coupé en deux panneaux P1 et P2 ; P2 : héros = non lus |
| 8 | dashboard.py | Abonnés : barres = gain quotidien, base zéro ; YouTube « ≈ 12,3 k » ; en-tête « +N CETTE SEMAINE » au lieu du total |
| 9 | dashboard.py | Citation : guillemets « » + U+202F ; tailles 48 / 40 / 32 |
| 10 | dashboard.py | `PLAYLIST` par plages (§3.3) et un complet sur 4 changements ; ne pas renvoyer une image identique (empreinte, comme InkyPi) |
| 11 | dashboard.py | Paperwhite 1 : le zoom ×1,28 sort les polices pixel de leur grille. Sur `pw1`, garder `-webkit-font-smoothing: antialiased` partout (rendu doux mais propre) plutôt que des pixels inégaux **[S]** |

### 6.8 Si la rotation plein écran est gardée (plan B)

Appliquer 1 à 5 et 8 à 11 du tableau, garder les 4 écrans de la v2, et ajouter dans le bandeau des écrans autres que Météo une mini-météo (icône 32 px + température VT323 50) : la météo reste visible à chaque coup d'œil. Cadence : journée Météo 12 min, Agenda + Courrier 8, Abonnés 5, Citation 5 (cycle 30 min), mêmes plages matin et nuit, même politique de flash.

---

## Sources (relevé du 01/01/2026)

- TRMNL : [framework](https://github.com/usetrmnl/trmnl-framework), [Rendering Modes](https://trmnl.com/framework/docs/3.4/rendering_modes), [Pixel Perfect](https://trmnl.com/framework/docs/3.4/pixel_perfect), [Layout](https://trmnl.com/framework/docs/3.4/layout), [plugins](https://github.com/usetrmnl/plugins), [intégrations](https://trmnl.com/integrations), [taux de rafraîchissement](https://help.trmnl.com/en/articles/10113695-how-refresh-rates-work), [mashups](https://help.trmnl.com/en/articles/10168132-mashups), [Smart Playlists](https://trmnl.com/blog/smart-playlists), [awesome-TRMNL](https://github.com/eindpunt/awesome-TRMNL).
- Rafraîchissement : [fbink.h](https://github.com/NiLuJe/FBInk/blob/master/fbink.h), [kindle-dash env.sh](https://github.com/pascalw/kindle-dash/blob/main/src/local/env.sh), [dash.sh](https://github.com/pascalw/kindle-dash/blob/main/src/dash.sh), [KOReader uimanager.lua](https://github.com/koreader/koreader/blob/master/frontend/ui/uimanager.lua), [InkyPi refresh_task.py](https://github.com/fatihak/InkyPi/blob/main/src/refresh_task.py), [InkyPi model.py](https://github.com/fatihak/InkyPi/blob/main/src/model.py), [Waveshare 2.13inch](https://www.waveshare.com/wiki/2.13inch_e-Paper_HAT_Manual), [Waveshare 4.26inch FAQ](https://docs.waveshare.com/4.26inch_e-Paper_G/FAQ).
- Dalle et vision : [E Ink Pearl, MobileRead](https://wiki.mobileread.com/wiki/E_Ink_Pearl), [Snellen chart](https://en.wikipedia.org/wiki/Snellen_chart), [Legge et Bigelow 2011](https://pmc.ncbi.nlm.nih.gov/articles/PMC3428264), [MIL-STD-411](https://aircraftandairframestructuralcompone.emilspec.com/MIL-STD-411/page19.html).
- Marques et chiffres : [Instagram icons](https://about.meta.com/brand/resources/instagram/icons), [brand.youtube](https://brand.youtube), [Simple Icons DISCLAIMER](https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md), [Smiirl](https://smiirl.com/en/counter/instagram), [Rival IQ](https://help.rivaliq.com/en/articles/9788197-why-youtube-subscriber-counts-are-rounded), [Tubefilter 2019](https://www.tubefilter.com/2019/09/16/youtubes-abbreviated-subscriber-counts-are-here/amp/).
- Rétro : [Minitel](https://fr.wikipedia.org/wiki/Minitel), [Teletext](https://en.wikipedia.org/wiki/Teletext), [Macintosh 128K](https://en.wikipedia.org/wiki/Macintosh_128K), [Split-flap display](https://en.wikipedia.org/wiki/Split-flap_display).
- Polices : [Departure Mono](https://github.com/rektdeckard/departure-mono), [Monaspace](https://github.com/githubnext/monaspace), [IBM Plex](https://github.com/IBM/plex), [Pixel Operator](https://www.dafont.com/pixel-operator.font), [Bedstead](https://bjh21.me.uk/bedstead/), [Chicago Kare (AUR)](https://aur.archlinux.org/packages/ttf-chicago-kare).
- Dépôts et captures : voir le tableau du §1.1.
