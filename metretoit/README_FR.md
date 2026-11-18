# MétréToit — prototype

À partir d'une adresse en France, MétréToit calcule le métré d'une toiture : les pans,
la pente et la surface réelle (rampant) de chaque pan. Il utilise les données ouvertes de l'IGN
(LiDAR HD, BD TOPO, géocodage de la Géoplateforme, licence Etalab 2.0), sans clé d'API.

## Installation (une seule fois)

Il faut Python 3.10 ou plus récent. Dans un terminal, depuis le dossier `metretoit/` :

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

L'ordinateur doit pouvoir joindre `data.geopf.fr` (données IGN).

## Les 2 commandes

**1. Métrer un toit**

```bash
.venv/bin/python metretoit.py "12 rue Exemple, 49000 Angers"
```

Le tableau des pans s'affiche, et le dossier `resultats/12-rue-exemple-49000-angers/` contient :
- `rapport.json` : toutes les valeurs (pans, pentes, surfaces, date du relevé LiDAR, bâtiment retenu…) ;
- `toit.png` : vue de dessus, pans en couleur et numérotés, flèche dans le sens de la pente,
  contour noir = emprise BD TOPO, pointillés = étendue réelle des points LiDAR, gris = zone non mesurée.

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
5. **Surfaces** : grille de 25 cm sur l'emprise, chaque cellule attribuée au pan le plus proche ;
   surface réelle = surface projetée ÷ cos(pente). Deux totaux :
   - **selon emprise** : limité au contour BD TOPO ;
   - **selon nuage de points** : limité à l'étendue réelle des points (inclut les débords visibles).

## Validation sur toits simulés

4 toits (2 pans 35°, 4 pans 30°, en L, plat), 10 points/m², bruit 5 cm, cheminée, branches d'arbre
et bout de mur parasites, 60 tirages aléatoires chacun (240 toits) :

| Critère | Résultat |
|---|---|
| Bon nombre de pans | 240 / 240 |
| Erreur de pente | 0,4° au maximum |
| Erreur de surface, variante emprise | 0,2 % au maximum |
| Erreur de surface, variante nuage | 0,5 % en moyenne, 2,6 % au maximum |

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
- Prototype de test : pas d'interface web.
