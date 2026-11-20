# MétréToit — prototype

À partir d'une adresse en France, MétréToit calcule le métré d'une toiture : les pans,
la pente et la surface réelle (rampant) de chaque pan. Il utilise les données ouvertes de l'IGN
(LiDAR HD, BD TOPO, géocodage de la Géoplateforme, licence Etalab 2.0), sans clé d'API.

## Le plus simple : l'interface de test

**Double-cliquez** sur `lancer_interface.bat` (Windows) ou `lancer_interface.command` (Mac).
La première fois, il installe ce qu'il faut (1 à 3 minutes, Python 3 doit être installé :
python.org), puis la page s'ouvre dans votre navigateur à l'adresse http://localhost:5000.
Pour arrêter : fermez la fenêtre noire (ou Ctrl+C).

Dans la page :
1. **Tapez une adresse** (des suggestions apparaissent) → le toit est métré automatiquement.
2. Si l'adresse tombe à côté : **zoomez sur la photo et cliquez sur le bon toit**.
   La couche « Cadastre » (bouton en haut à droite de la carte) aide à repérer les bâtiments.
3. Si le bâtiment est mal découpé (maisons mitoyennes regroupées…) : **« Dessiner l'emprise »**,
   cliquez sur chaque angle du toit, puis « Terminer et calculer ».
4. Les pans s'affichent en couleur sur la photo (cliquez sur un pan pour son détail), avec le tableau,
   les deux surfaces totales et un **indice de fiabilité** (bonne / moyenne / à vérifier) expliqué.
5. **« Comparer avec ma mesure »** : saisissez la vraie surface → l'écart s'affiche, et un bouton
   ajoute ce toit à `toits_reference.csv`. Quand vous en avez 10 : **« Lancer le test de précision »**
   donne le verdict GO / NO-GO directement dans la page.

## Installation à la main (si vous préférez le terminal)

Il faut Python 3.10 ou plus récent. Dans un terminal, depuis le dossier `metretoit/` :

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

L'ordinateur doit pouvoir joindre `data.geopf.fr` (données IGN).

## Les commandes (terminal)

**0. Interface de test** : `.venv/bin/python interface.py` puis ouvrir http://localhost:5000


**1. Métrer un toit**

```bash
.venv/bin/python metretoit.py "12 rue Exemple, 49000 Angers"
```

Le tableau des pans s'affiche, et le dossier `resultats/12-rue-exemple-49000-angers/` contient :
- `rapport.json` : toutes les valeurs (pans, pentes, surfaces, date du relevé LiDAR, bâtiment retenu…) ;
- `toit.png` : vue de dessus, pans en couleur et numérotés, flèche dans le sens de la pente,
  contour noir = emprise BD TOPO, pointillés = étendue réelle des points LiDAR, gris = zone non mesurée.
- `toit.kml` : les pans en 3D (vraie pente, hauteur au-dessus du sol mesurée par le LiDAR), à ouvrir
  dans Google Earth (Pro sur ordinateur, ou earth.google.com → Projets → Importer un fichier KML).
  Utile pour **contrôler** : bon bâtiment, débords, et avec l'historique des images de Google Earth Pro,
  travaux faits depuis la date du relevé LiDAR. Cela n'améliore pas la précision du calcul lui-même.

Options utiles si l'adresse tombe à côté :
- `--xy 432559 6713935` : position en Lambert-93 (on la lit par exemple sur geoportail.gouv.fr) ;
- `--emprise mon_toit.geojson` : contour du toit dessiné à la main (Lambert-93 ou GPS) ;
- `--laz dalle.copc.laz` : fichier LiDAR téléchargé à la main si l'accès automatique échoue.

**2. Tester la précision sur des toits connus**

Remplir `toits_reference.csv` (séparateur `;`, une ligne par toit) :

```
nom;adresse;surface_reelle_m2;pente_reelle_deg;nb_pans;debords_inclus;source_mesure;notes
Maison Dupont;12 rue Exemple, 49000 Angers;142.5;35;2;oui;devis couvreur 2024;
```

`pente_reelle_deg` et `nb_pans` peuvent rester vides. `debords_inclus` = `oui` ou `non`.
Colonnes facultatives : `x_l93;y_l93` pour forcer la position d'un toit.

```bash
.venv/bin/python test_precision.py toits_reference.csv
```

Résultat : `resultats/test_precision.md` (tableau toit par toit, images, verdict).
**GO** si l'écart de surface est inférieur à 5 % sur au moins 8 toits sur 10, sinon **NO-GO** avec les causes probables.

(Les tests sur toits simulés se lancent avec `.venv/bin/python -m pytest tests -v`.)

## Comment ça marche

1. **Géocodage** de l'adresse (Géoplateforme) → coordonnées Lambert-93.
2. **Emprise** du bâtiment : BD TOPO (`BDTOPO_V3:batiment`), celui qui contient le point,
   sinon le plus proche à moins de 15 m.
3. **LiDAR HD** : l'index des dalles (`IGNF_LIDAR-HD_METADONNEE:metadata`, attribut `url_npl`)
   donne l'adresse du fichier COPC ; on ne lit que la zone du bâtiment (quelques centaines de Ko,
   jamais la dalle entière de 100 Mo à 2 Go). Bâtiment à cheval sur 2 dalles : géré.
   On garde les points de classe 6 (bâtiment). Tout est mis en cache dans `cache/`.
4. **Pans** : détection de plans par RANSAC (seuil 12 cm, 25 points minimum), rejet des murs,
   séparation des morceaux non connexes, fusion des pans coplanaires voisins, recalcul par moindres carrés.
   Filtres ajoutés : un plan de moins de 2 m², un plan surtout hors de l'emprise (arbre, toit du voisin),
   un plan « flottant » au-dessus d'un autre pan (branches) ou caché dessous (façade) est écarté.
   Pente < 3° = « toit plat ».
5. **Surfaces** : grille fine (6,25 cm) sur l'emprise. Chaque cellule va au pan, présent tout près,
   dont le plan passe à la hauteur réellement mesurée à cet endroit (faîtages et noues bien droits) ;
   un îlot de moins de 0,5 m² est rendu au pan qui l'entoure.
   Surface réelle = surface projetée ÷ cos(pente). Deux totaux :
   - **selon emprise** : limité au contour BD TOPO ;
   - **selon nuage de points** : limité à l'étendue réelle des points (inclut les débords visibles).

   Le cahier des charges prévoyait des cellules de 25 cm : avec un faîtage parallèle à la grille,
   une rangée entière de cellules basculait d'un côté (jusqu'à 2 % d'erreur sur un pan). D'où 6,25 cm.
   Sur les très grands bâtiments (> 3 000 m²), les cellules grossissent automatiquement pour rester rapides.
6. **Fiabilité** : vert / orange / rouge selon le score de géocodage, la part non mesurée, l'écart entre
   les deux surfaces, l'irrégularité des pans, les pans très raides et l'âge du relevé LiDAR.

## Validation sur toits simulés

5 toits (2 pans 35°, 4 pans 30°, en L, plat, 2 pans asymétriques 40°/25°), 10 points/m², bruit 5 cm,
cheminée, branches d'arbre et bout de mur parasites, 60 tirages aléatoires chacun (300 toits) :

| Critère | Résultat |
|---|---|
| Bon nombre de pans | 300 / 300 |
| Erreur de pente | 0,4° au maximum |
| Erreur de surface totale, variante emprise | 0,2 % au maximum |
| Erreur de surface totale, variante nuage | 0,6 % en moyenne, 2,6 % au maximum |
| Erreur de surface de chaque pan (toit asymétrique) | 0,2 % en moyenne, 1,1 % au maximum |

La variante « nuage » est un peu moins précise : avec 10 points/m², le bord exact du toit tombe
entre deux points (environ ±10 cm). Le test automatique exige donc < 2 % pour la variante emprise
sur chaque toit, et pour la variante nuage < 3 % par toit et < 2 % en moyenne.

## Limites connues

- **Date du relevé** : le LiDAR HD date de 2021 à 2025 selon les régions. Une extension, une véranda ou
  une réfection postérieure n'est pas vue. La date est indiquée dans chaque rapport.
- **Débords de toit** : la BD TOPO trace parfois le contour des murs, parfois celui du toit. D'où les
  deux surfaces ; l'écart entre elles donne une idée de l'importance des débords.
- **Maisons mitoyennes / bâtiments groupés** : si la BD TOPO regroupe plusieurs logements dans un seul
  bâtiment, la surface est celle de l'ensemble. Utiliser `--emprise` pour isoler le sien.
- **Toits complexes** (centre-ville ancien, lucarnes, brisis de mansarde, petits éléments < 2 m²) :
  les petits pans sont fusionnés avec leurs voisins ou ignorés ; les surfaces très raides (> 70°)
  sont mal vues d'avion.
- **Végétation** : un arbre qui couvre le toit masque une partie des points ; la part « non mesurée »
  est indiquée en %.
- **Vérandas et verrières** : le verre renvoie peu de points LiDAR.
- **Géocodage** : une adresse imprécise peut tomber sur le mauvais bâtiment (le score est affiché ;
  vérifier `toit.png` et corriger avec `--xy`).
- **Grands bâtiments** (commerces, entrepôts) : le calcul fonctionne (≈ 10 s pour 7 000 m²) mais les
  toits techniques (équipements, sheds) donnent des dizaines de pans ; MétréToit vise d'abord les maisons.
- L'interface tourne sur votre ordinateur (pas de site en ligne) : c'est un outil de test.
