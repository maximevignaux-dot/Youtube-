# Projet : chaîne YouTube « DOSSIERS » — les coulisses de l'argent

## Contexte
Je suis Maxime, je ne code pas : tu (Claude Code) construis et maintiens tout le pipeline.
Je fais le script et j'enregistre MA voix off. Le pipeline fait le montage et les visuels, et me sort
une liste claire des images/vidéos que je dois fournir moi-même.
Explique-moi chaque commande à lancer, pas à pas, en langage simple.

Stack : Node.js + Remotion (rendu vidéo en React), ffmpeg, Python pour les utilitaires
(Whisper pour la transcription, rembg pour détourer les images, edge-tts pour la voix test).

## LE BUT FINAL : coller un script → obtenir une vidéo montée
Mon usage quotidien doit être aussi simple que ça :
1. Je colle un script dans Claude Code en disant « Nouvelle vidéo : <script> ».
2. Tu crées /videos/<slug>/script.md et tu lances TOUT le pipeline sans me poser de questions
   techniques : voix test → découpage → images/vidéos auto → montage → aperçu → shotlist.
3. Je regarde l'aperçu et la shotlist. Je teste plein de scripts comme ça, SANS enregistrer ma voix.
4. Quand un script me plaît, j'enregistre ma voix et je dépose voix.mp3 dans le dossier.
   Je dis « Ma voix est prête pour <slug> » → tu recales tout le montage sur ma voix et tu fais le rendu final.

### Mode « voix test » (par défaut tant qu'il n'y a pas de voix.mp3)
- Retirer toutes les balises [ ... ] et les lignes de consignes (commençant par > ou ⚠️) du texte à lire.
- Générer voix-test.mp3 avec edge-tts (gratuit, sans clé API), voix française masculine
  naturelle (ex. fr-FR-HenriNeural), débit légèrement rapide (+8 %), avec les horodatages au mot.
- Les « … » et [PAUSE 1s] deviennent de vrais silences.
- Tout le montage est calé sur voix-test.mp3. Le rendu porte un petit filigrane « VOIX TEST ».

### Passage à ma vraie voix (`npm run revoice <slug>`)
- Nettoyer voix.mp3, transcrire avec Whisper (horodatage au mot).
- Réaligner chaque scène de scenes.json sur les nouveaux timecodes EN GARDANT les mêmes choix
  de visuels, assets et animations (on ne refait pas le montage, on le recale).
- Signaler les phrases que j'ai changées ou sautées par rapport au script.
- Rendu final 1080p sans filigrane.

### Assets manquants = pas bloquant pour l'aperçu
Tant qu'une image/vidéo manque, utiliser un placeholder dans le style maison (carton papier crème
avec la description tapée à la machine + numéro de scène). L'aperçu est toujours regardable.

### Liste de visuels préparée à la main (a-chercher.md)
Si /videos/<slug>/a-chercher.md existe, il est PRIORITAIRE sur la recherche automatique.
Les fichiers que je dépose dans assets/ sont nommés par l'ID de cette liste (V01.mp4, P03.jpg, I02.png).
Pour chaque ID : retrouver la phrase de la colonne « Moment » dans script.md, placer le fichier
sur la ou les scènes correspondantes, et le noter dans scenes.json. ID sans fichier → recherche auto
avec ses mots-clés, sinon placeholder. Quand j'écris un nouveau script, générer aussi son a-chercher.md
(même format) + une version PDF lisible sur téléphone.

## La ligne éditoriale
Chaîne française faceless sur les coulisses de l'argent : arnaques et affaires oubliées,
empires discrets, business models cachés, coups de génie marketing.
Ton : enquête, on révèle quelque chose que le spectateur ne savait pas. Jamais de conseil
d'investissement (« achetez X ») : on explique, on ne recommande pas.
Chaque vidéo = un « dossier » numéroté (DOSSIER N°001, N°002…).

## Ton de narration (pour tous les scripts)
Storytelling d'enquête décontracté, comme si on racontait l'histoire à un pote au comptoir.
- Phrases courtes. Beaucoup de rythme. Des pauses avant les révélations (« … »).
- Questions au spectateur (« Et vous pensez qu'il s'arrête là ? Évidemment que non. »).
- Humour et ironie en aparté, jamais méchant, jamais sur une accusation non prouvée.
- Relances régulières pour garder l'attention (« Gardez ce détail en tête. Il va revenir. »).
- Langage parlé (« bosser », « le gamin », « bref »), mais les faits restent précis et sourcés.
- Toute accusation contre une personne ou une entreprise est attribuée à sa source
  (« selon la justice genevoise », « d'après l'ONG X ») + la version de la défense + l'issue.

## Durée
- Vidéos 1 à 5 : 10–12 min (on apprend, la rétention compte plus que la durée).
- Ensuite : 12–15 min si la rétention moyenne tient au-dessus de ~35 %.
- Jamais de remplissage : la durée suit l'histoire. Minimum 8 min (publicités au milieu de la vidéo).
- Structure d'un script :
  1. Hook 0–30 s : la scène la plus folle de l'histoire, sans contexte.
  2. Promesse 30–60 s : ce que le spectateur va comprendre.
  3. Pièce n°1 (contexte) → Pièce n°2 (l'ascension / la mécanique) → Pièce n°3 (la chute / la révélation).
  4. Conclusion : la leçon + teaser du prochain dossier.

## LE STYLE MAISON : « le dossier d'enquête »
Objectif : qu'on reconnaisse une de mes vidéos en 2 secondes, sans voir le nom de la chaîne.
Univers visuel : un bureau d'enquêteur financier. Papier, tampons, fils rouges, billets, documents
caviardés. Sombre et premium, jamais cheap.

### Palette (à définir en variables, utilisée partout)
- Noir fond `#0D0D0D` · Papier crème `#EFE6D2` · Vert billet `#1F8A5B` (argent, gains)
- Rouge tampon `#C8102E` (danger, pertes, arnaques) · Jaune surligneur `#F2D023` (révélations)
- Grain papier léger + vignettage sur TOUTE la vidéo.

### Typographies (Google Fonts, gratuites)
- Titres et gros chiffres : **Anton** (condensé, impactant)
- Annotations, fiches, dates : **Special Elite** (machine à écrire)
- Texte courant à l'écran : **Inter**

### Éléments signature (composants Remotion)
- `OuvertureDossier` : chemise cartonnée qui s'ouvre, tampon « DOSSIER N°00X » frappé + son tampon.
- `FichePersonnage` : photo agrafée de travers, nom tapé à la machine, champs
  (Rôle / Fortune / Statut), tampon final (« CONDAMNÉ », « EN FUITE », « MILLIARDAIRE »…).
- `TableauEnquete` : liège sombre, photos punaisées, FIL ROUGE qui se tend entre personnes,
  entreprises et montants. Caméra qui glisse d'un élément à l'autre. Revient à chaque acte
  et se complète au fil de la vidéo.
- `CompteurBillets` : montant qui défile comme sur une compteuse de billets, en vert billet
  (gains) ou rouge (pertes), avec son de liasse.
- `DocumentCaviarde` : contrat / relevé / article recréé, barres noires qui se retirent
  une par une pour révéler l'info clé, puis surlignage jaune.
- `CarteFlux` : carte sombre style ancien, flux d'argent en pointillés verts entre pays/villes.
- `GraphiqueAnime` : courbes/barres qui se dessinent, style papier millimétré.
- `PhotoKenBurns` + `Parallaxe25D` : photos avec mouvement permanent, sujet détouré en avant.
- `TimelineMachine` : dates tapées à la machine qui défilent.
- `MotCle` : mot fort frappé à l'écran en Anton, synchro au mot exact de la voix.
- `CartonPiece` : tampon rouge « PIÈCE N°2 » en début d'acte (+ chapitres YouTube).
- Transitions : flash d'appareil photo (changement de lieu), feuille qui glisse (changement d'idée),
  cut sec le reste du temps.

### Sound design signature
Tampon (chapitres, verdicts), machine à écrire (fiches, dates), flash photo (transitions),
compteuse de billets (montants), nappe grave tendue en fond, silence d'1 s avant chaque révélation.
Musique qui change à chaque pièce. Ducking automatique sous la voix.
Uniquement depuis /musique et /sfx (YouTube Audio Library, Epidemic Sound ou Artlist).

### Miniatures (cohérentes avec la vidéo)
Fond noir, 1 visage ou objet détouré, tampon rouge en diagonale, 3 mots max en Anton,
un détail vert billet. Générer 3 variantes par vidéo pour tester.

## Structure du projet
```
/videos/<slug>/
  script.md            # mon script (avec balises)
  voix.mp3             # ma voix off
  scenes.json          # découpage généré par toi
  assets/              # images/vidéos, nommées par ID de scène (S012.jpg, S044.mp4)
  shotlist.html        # liste des images/vidéos à trouver (générée)
  credits.txt          # crédits à coller dans la description YouTube
  chapitres.txt        # chapitres YouTube (timecodes)
  sortie.mp4
/src/components/       # composants Remotion du style maison
/sfx/  /musique/       # sons et musiques sous licence
/mes-rushs/            # mes propres vidéos (téléphone, drone)
```

## Étape 1 — Voix et découpage en scènes
- Nettoyer voix.mp3 (volume normalisé, suppression des blancs trop longs et des ratés :
  quand je me trompe, je marque une pause et je reprends la phrase → garder la dernière prise).
- Transcrire avec Whisper, horodatage au mot.
- Découper en scènes de 2 à 5 s MAX (jamais une image fixe > 5 s).
- Pour chaque scène dans scenes.json : id (S001…), début/fin (ms), texte prononcé, composant,
  asset (photo/vidéo), requête de recherche FR + EN, description de l'image idéale, animation, son.
- Détection automatique : montants → `CompteurBillets` ; dates → `TimelineMachine` ;
  personne citée pour la 1ʳᵉ fois → `FichePersonnage` ; lieux → `CarteFlux` ;
  comparaisons → `GraphiqueAnime` ; mots forts → `MotCle` ; tout déclenché au mot exact.
- Balises dans script.md (prioritaires, jamais lues à voix haute) :
  `[CHIFFRE 80 M€]`, `[FICHE Gilbert Chikli | Escroc | CONDAMNÉ]`, `[CARTE Paris→Tel Aviv]`,
  `[GRAPH ...]`, `[DOCUMENT "virement 5 M€" caviardé]`, `[TABLEAU ajouter X relié à Y]`,
  `[PHOTO ...]`, `[VIDEO ...]`, `[PIECE 2 "L'arnaque"]`, `[SHORT début]` / `[SHORT fin]`.

## Format liste → Shorts (vidéos « 10 façons de… »)
- Chaque segment entre `[SHORT début]` et `[SHORT fin]` est exporté en plus comme Short :
  9:16, 1080×1920, 45–60 s max, recadrage intelligent (sujet centré, éléments graphiques
  réorganisés en vertical, pas un simple crop), sous-titres dynamiques mot par mot
  (obligatoires en Short), première seconde = le mot-clé du segment en grand.
- `npm run shorts <slug>` → dossier /videos/<slug>/shorts/ avec un MP4 par segment
  + un titre et une description proposés pour chacun.
- Même style maison que les vidéos longues (palette, tampons, sons) pour qu'on reconnaisse la chaîne.

## Étape 2 — Images (licence enregistrée à chaque fois)
1. **Wikimedia Commons (API)** : photos réelles (personnes, lieux, bâtiments, objets).
   Uniquement CC0 / CC-BY / CC-BY-SA / domaine public. Auteur + licence dans credits.txt.
2. **Pexels / Pixabay (API gratuites)** : plans génériques (billets, bureaux, avions, tribunaux…).
3. **Images IA** : ambiances, scènes d'époque, objets. JAMAIS de visage réaliste d'une vraie personne.
4. **Généré par code** : documents, unes de journaux (recréées, pas copiées), cartes, graphiques, chiffres.
Tout ce qui manque → shotlist.html.

## Étape 2 bis — Vidéos (B-roll), ~40 % du film
1. Pexels Videos / Pixabay Videos (API) · 2. Wikimedia Commons ·
3. Envato Elements ou Storyblocks (je télécharge à la main depuis la shotlist) ·
4. Vidéo IA (Kling / Runway / Veo), 5–8 s max · 5. /mes-rushs (téléphone, drone) ·
6. Espaces presse officiels.
INTERDIT : vidéos YouTube, reportages TV, extraits de films/séries, pubs de marques (Content ID).
Chaque clip : recadrage 16:9, meilleur passage, son coupé, étalonnage uniforme
(même LUT « dossier » sur tout le film : noirs profonds, teinte légèrement chaude, grain).

## Étape 3 — shotlist.html (pour moi, lisible sur téléphone)
Une ligne par élément manquant : ID + timecode + phrase prononcée, photo OU vidéo, durée,
description exacte, 2–3 pistes de recherche, nom de fichier à utiliser (S027.jpg),
aperçu du placeholder actuel, case à cocher. Je dépose le fichier dans assets/ → tu relances.

## Règles de montage
- Hook 0–30 s : 1 visuel toutes les 1,5–2 s, la scène la plus forte d'abord.
- Ensuite : changement de visuel toutes les 3–5 s, mouvement permanent.
- Un élément signature (fiche, tableau, compteur, document) au moins toutes les 60 s.
- Le TableauEnquete revient à chaque pièce pour résumer où on en est.
- Pas de sous-titres complets (format long) : seulement les MotCle.

## Étape 4 — Rendu et contrôle
- `npm run video <slug>` → voix test si pas de voix.mp3, scenes.json, assets auto, shotlist.html,
  aperçu 720p (Remotion Studio + fichier apercu.mp4).
- `npm run revoice <slug>` → recalage sur ma vraie voix.
- `npm run final <slug>` → rendu 1080p + credits.txt + chapitres.txt + 3 miniatures.
- `npm run shorts <slug>` → Shorts verticaux (si balises [SHORT]).
- Bloquer le rendu final si un asset manque ou si une licence est inconnue (pas l'aperçu).
- Clés API (Pexels, Pixabay, génération d'images) dans un fichier .env : si une clé manque,
  continuer avec les placeholders et me dire quelle clé ajouter et où la créer.

## Construction du pipeline (à faire une seule fois, en plusieurs sessions si besoin)
Session 1 — Fondations
1. Vérifier / installer Node, ffmpeg, Python, Whisper, edge-tts, rembg, en m'expliquant chaque étape.
2. Créer le projet Remotion : palette, polices, grain + vignettage, sons de base dans /sfx
   (YouTube Audio Library), et les composants OuvertureDossier, FichePersonnage,
   CompteurBillets, DocumentCaviarde, MotCle, PhotoKenBurns, CartonPiece.
3. Démo de 30 s sur le hook du script /videos/castel/script.md pour valider le style avec moi.
Session 2 — Chaîne complète
4. Voix test edge-tts + découpage automatique en scènes + lecture des balises.
5. Récupération auto des images/vidéos (Wikimedia, Pexels, Pixabay) + placeholders + shotlist.html.
6. Composants restants : TableauEnquete, CarteFlux, GraphiqueAnime, TimelineMachine,
   Parallaxe25D, transitions, sound design automatique, ducking musique.
7. Test complet : `npm run video castel` doit sortir la vidéo entière du DOSSIER N°001 en voix test.
Session 3 — Finitions
8. `revoice`, `final`, `shorts`, miniatures. Puis itérations sur le style jusqu'au niveau des grosses chaînes.

Quand le pipeline est fini, écris un fichier MODE-EMPLOI.md d'une page, en français simple,
avec uniquement les phrases que je dois taper pour chaque situation.

## Mémo technique (pour Claude Code, ajouté après la construction)
Phrase de Maxime → ce que tu fais :
- « Nouvelle vidéo : <script> » → choisir un slug court, écrire videos/<slug>/script.md (+ a-chercher.md et sa
  version PDF si besoin), puis `npm run video <slug>` ; envoyer apercu.mp4 et shotlist.html.
- « J'ai ajouté des images… » / « J'ai modifié le script… » → `npm run video <slug>` (le montage est réutilisé
  si le script n'a pas changé ; `-- --refaire` pour tout recalculer).
- « Ma voix est prête pour <slug> » → `npm run revoice <slug>` puis montrer rapport-voix.txt ; enchaîner
  `npm run final <slug>` si tout est prêt (visuels + assets/sources.txt), sinon dire ce qui manque.
- « Fais les Shorts de <slug> » → `npm run shorts <slug>`.
Code : scripts/video.py, revoice.py, final.py, shorts.py (orchestration) ; scripts/dossiers/ (script_md, voix,
scenes, assets_auto, shotlist, revoix, decoupes) ; src/ (Remotion : Video, Short, Miniature, components/).
Visuels : assets/<ID>.ext (fournis) passent devant assets/auto/<ID>.ext (trouvés) ; détourages dans assets/decoupes/.
