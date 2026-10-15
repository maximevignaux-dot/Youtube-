---
name: tshirts
description: Génère les designs de t-shirts humour à partir des slogans validés de banque-slogans.xlsx, et prépare pour chacun un dossier prêt à mettre sur Printful (fichiers d'impression, aperçus, fiche produit, prompts illustration et vidéo).
argument-hint: "[optionnel : un slogan à ajouter directement]"
---

# /tshirts — de l'idée au dossier prêt à publier

Maxime ne code pas. Tu fais tout, tu lui montres le résultat, il choisit.

## 0. Si un slogan est passé en argument
`$ARGUMENTS` non vide → ajoute-le à la fin de l'onglet Slogans de `banque-slogans.xlsx` (statut « Validé », niche, cible et couleur devinées) avant de continuer.

## 1. Lire les slogans à traiter
- Ouvre `banque-slogans.xlsx`, onglet **Slogans**, avec openpyxl.
- Prends les lignes au statut **Validé** (une fois traitées, elles passent en « Design fait », donc rien n'est fait deux fois).
- S'il n'y en a aucune, dis-le en une phrase et arrête-toi.

## 2. Écrire la fiche design (designs.json)
Pour chaque slogan, ajoute une entrée :
- `id` : slug court (ex. `saucisson-aux-herbes`).
- `tshirt` : `noir`, `blanc`, `kaki`, `marine`, `sable` ou `gris` (colonne Couleur, sinon noir pour les hommes, blanc pour les femmes).
- `lignes` : 3 à 6 lignes courtes. Niveaux : `petit` (mise en place), `grand` (texte principal), `accent` (la chute, en couleur). La chute va toujours en dernier et en `accent`.
- `icone` : un fichier de `icons/` (sans .svg). S'il en manque un, télécharge-le chez tabler-icons (MIT) : `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<nom>.svg`. Marque la ligne qui précède l'icône avec `"icone_apres": true`.
- `arc_haut`, `arc_bas` (25 caractères max) et `centre` (1 ou 2 lignes) pour le style écusson.
- `chute` : petite phrase manuscrite en bas, facultative.
- Slogan en forme de liste → `titre` + `liste` (`etat` : `ok`, `non` ou `jauge` avec `pct`).
- **Illustration** : si le slogan gagne à avoir un dessin (un personnage, un objet qui fait la blague), regarde si `illustrations/<id>.png` existe. Si oui, mets `"illustration": "<id>.png"` et `"illustration_apres": true` sur la ligne qui précède le dessin. Sinon, écris le prompt dans le dossier (étape 4) et génère quand même les versions sans illustration.

## 3. Générer
`python3 generate.py` — il ne refait que les nouveaux. Pour refaire un design : `python3 generate.py --only <id>`.
Ouvre `planche-du-jour.jpg` et vérifie toi-même : texte lisible, rien qui déborde, accents corrects. Corrige le découpage et relance si besoin.

## 4. Compléter chaque dossier `sortie/<id>/`
Le script y a déjà mis `impression_<style>.png` (4500 x 5400 px, transparent, 300 dpi), `apercu_<style>.jpg` et `planche.jpg`. Ajoute :

**fiche-produit.md**
- Titre produit (60 caractères max, avec le métier ou la niche : « T-shirt Pétanque Humour – Je sers l'apéro »)
- Description (3 phrases drôles + « Idée cadeau pour… » + matière et entretien standard)
- 13 tags Etsy (20 caractères max chacun)
- Couleur de t-shirt conseillée, et le style d'impression conseillé parmi les variantes
- Prix conseillé : 24,90 € (29,90 € pour un sweat)

**prompt-illustration.txt** (seulement si pas encore d'illustration)
Prompt en anglais, toujours dans le style maison :
« T-shirt print illustration, vintage cartoon mascot style with thick black outlines and flat limited colors (cream, mustard yellow, brick red, dark brown): [le sujet drôle]. Isolated on plain white background, centered, no text, no lettering, clean screen-print look. »
Maxime le génère (Canva, ChatGPT…) et dépose le PNG dans `illustrations/<id>.png`, puis relance `/tshirts`.

**video.md** — 3 idées de vidéo de 6 à 10 secondes, chacune avec :
- Le prompt image (en anglais) : personnage vu de dos ou de trois-quarts dos, qui porte le t-shirt (couleur exacte), dans un décor français sans aucun logo (supermarché, terrain de pétanque, garage, chantier, barbecue, camping, terrasse de café). Look photo smartphone, lumière naturelle.
- Le prompt vidéo (en anglais) : un seul mouvement simple et lent, caméra tenue à la main, « the t-shirt print stays sharp and unchanged ».
- La légende à incruster (une phrase + 1 émoji) qui complète la blague sans la répéter.
- Le texte du post Facebook (2 lignes + appel à l'action vers la boutique).
Personnage récurrent par défaut : **le daron un peu vénère** — 55-65 ans, cheveux gris, lunettes, short cargo, caddie ou verre à la main, l'air de quelqu'un qu'on n'emmerde pas. Variantes : la mamie qui a du caractère, le collègue de chantier.

## 5. Mettre à jour et résumer
- Passe le statut de ces lignes à « Design fait » dans `banque-slogans.xlsx`.
- Résume à Maxime en 3 lignes maximum : combien de designs, lesquels attendent une illustration, et le chemin de `planche-du-jour.jpg`.

## Règles de contenu
- Jamais de marque, constructeur, enseigne, logo, personnage connu, parole de chanson, réplique de film, ni slogan recopié d'une autre boutique.
- Provoc OK sur les choix de vie (végans, régime, diesel, Parisiens, belle-mère). Jamais sur l'origine, la religion, le handicap, l'orientation ou le physique des autres.
- Orthographe et accents parfaits : c'est imprimé.

