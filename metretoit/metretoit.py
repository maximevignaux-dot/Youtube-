#!/usr/bin/env python3
"""MétréToit — métré d'une toiture à partir d'une adresse (données IGN LiDAR HD).

Exemples :
  python metretoit.py "12 rue Exemple, 49000 Angers"
  python metretoit.py --xy 432559 6713935
  python metretoit.py "12 rue Exemple, 49000 Angers" --emprise mon_toit.geojson
  python metretoit.py "12 rue Exemple, 49000 Angers" --laz dalle.copc.laz
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import numpy as np
import shapely

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

from toiture import donnees  # noqa: E402
from toiture.analyse import analyser, pour_json  # noqa: E402
from toiture.export import fiabilite, geojson_pans, kml_pans  # noqa: E402
from toiture.lignes import calculer_lignes, totaux  # noqa: E402
from toiture.partiel import enregistrer_grille  # noqa: E402
from toiture.rendu import dessiner, tableau  # noqa: E402

CLASSE_BATIMENT = 6


def slug(texte: str) -> str:
    t = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:80] or "toit"


def calculer(adresse: str | None = None, xy=None, emprise_fichier=None, laz=None,
             dossier_resultats: Path | None = None, nom: str | None = None, bavard=True) -> dict:
    """Calcul complet. Renvoie le rapport (dict) et écrit rapport.json + toit.png."""
    def dire(*a):
        if bavard:
            print(*a)

    rapport = {"adresse_demandee": adresse}
    # Étape 1 : position
    if xy is not None:
        x, y = map(float, xy)
        rapport["localisation"] = {"source": "coordonnées --xy (Lambert-93)", "x": x, "y": y}
    elif adresse:
        geo = donnees.geocoder(adresse)
        x, y = geo["x"], geo["y"]
        rapport["localisation"] = {"source": "géocodage Géoplateforme", **geo}
        dire(f"Adresse trouvée : {geo['adresse_trouvee']} (score {geo['score']:.2f}, type {geo['type']})")
        if geo["score"] is not None and geo["score"] < 0.6:
            dire("  ⚠ Score de géocodage faible : vérifiez l'adresse ou utilisez --xy.")
    elif emprise_fichier is None:
        raise SystemExit("Donnez une adresse, --xy X Y ou --emprise fichier.geojson")
    else:
        x = y = None

    # Étape 2 : emprise
    voisins = None
    if emprise_fichier is not None:
        if isinstance(emprise_fichier, (str, Path)):
            emprise = donnees.lire_emprise(emprise_fichier)
            rapport["emprise"] = {"source": f"fichier {emprise_fichier}"}
        else:   # géométrie shapely déjà en Lambert-93 (dessinée dans l'interface)
            emprise = emprise_fichier
            rapport["emprise"] = {"source": "dessinée à la main"}
        if x is None:
            x, y = emprise.centroid.x, emprise.centroid.y
        try:
            autour = donnees.batiments_autour(x, y)
            voisins = shapely.union_all([g for g, _ in autour if not g.intersects(emprise.buffer(-0.5))] or [shapely.Polygon()])
        except donnees.ErreurDonnees:
            voisins = None
    else:
        autour = donnees.batiments_autour(x, y)
        emprise, props, dist = donnees.choisir_batiment(x, y, autour)
        voisins = shapely.union_all([g for g, _ in autour if not g.equals(emprise)] or [shapely.Polygon()])
        rapport["emprise"] = {"source": donnees.COUCHE_BATI, "id": props.get("cleabs"),
                              "distance_au_point_m": round(dist, 1), "usage": props.get("usage_1"),
                              "hauteur_bdtopo_m": props.get("hauteur"), "nb_etages": props.get("nombre_d_etages")}
        dire(f"Bâtiment BD TOPO : {props.get('cleabs')} — emprise {emprise.area:.1f} m²"
             + (f" (à {dist:.1f} m du point)" if dist > 0 else " (contient le point)"))
    rapport["emprise"]["aire_m2"] = round(emprise.area, 2)
    rapport["emprise"]["geometrie_wkt_l93"] = emprise.wkt

    # Étape 3 : LiDAR
    xyz, cls, infos = donnees.points_lidar(emprise, marge=2.0, fichiers_laz=laz)
    pts6 = xyz[cls == CLASSE_BATIMENT]
    rapport["lidar"] = {**infos, "nb_points_zone": int(len(xyz)), "nb_points_classe6_zone": int(len(pts6))}
    dire(f"LiDAR HD : {infos['nb_dalles']} dalle(s), relevé du {infos['date_releve']}, "
         f"{len(xyz)} points lus dont {len(pts6)} « bâtiment »")

    # Étapes 4-5 : pans et surfaces
    res = analyser(pts6, emprise, voisins=voisins)
    rapport.update(pour_json(res))
    rapport["densite_points_m2"] = round(res["nb_points_classe6"] / max(emprise.buffer(1).area, 1), 1)
    rapport["fiabilite"] = fiabilite(rapport)
    # mètres linéaires (égouts, faîtages, rives, arêtiers, noues, solins…)
    ox, oy = res["origine"][0], res["origine"][1]
    lignes = calculer_lignes(res)
    for l in lignes:
        l["coords_l93"] = [[round(x + ox, 3), round(y + oy, 3)] for x, y in l.pop("coords")]
    res["lignes"] = lignes
    rapport["lignes"] = lignes
    rapport["lineaires_m"] = totaux(lignes)
    rapport["geojson_wgs84"] = geojson_pans(res)
    for l in lignes:
        lon, lat = donnees.VERS_WGS84.transform(*np.array(l["coords_l93"]).T)
        rapport["geojson_wgs84"]["features"].append({
            "type": "Feature", "geometry": {"type": "LineString", "coordinates": np.c_[lon, lat].round(8).tolist()},
            "properties": {"role": "ligne", "type": l["type"], "longueur_m": l["longueur_m"], "pans": l["pans"]}})

    # Étape 6 : sorties
    nom = nom or slug(adresse or f"{x:.0f}-{y:.0f}")
    dossier = (dossier_resultats or RACINE / "resultats") / nom
    dossier.mkdir(parents=True, exist_ok=True)
    titre = (f"{rapport.get('localisation', {}).get('adresse_trouvee') or adresse or nom}\n"
             f"Surface selon emprise : {res['surface_emprise_m2']:.1f} m² — selon nuage : {res['surface_nuage_m2']:.1f} m²"
             f" — relevé LiDAR {infos['date_releve']}")
    dessiner(res, titre, dossier / "toit.png")
    enregistrer_grille(dossier, res)
    # sol : points LiDAR classés « sol » (classe 2) autour du bâtiment
    sol = xyz[cls == 2, 2]
    z_sol = float(np.median(sol)) if len(sol) >= 10 else float(np.percentile(xyz[:, 2], 2)) if len(xyz) else 0.0
    rapport["altitude_sol_m"] = round(z_sol, 2)
    (dossier / "toit.kml").write_text(kml_pans(res, rapport.get("localisation", {}).get("adresse_trouvee") or adresse or nom,
                                               z_sol, infos["date_releve"]), encoding="utf-8")
    (dossier / "rapport.json").write_text(json.dumps(rapport, ensure_ascii=False, indent=2, default=_json))
    rapport["dossier"] = str(dossier)

    if bavard:
        print()
        print(tableau(res))
        print(f"Surface réelle totale selon emprise BD TOPO : {res['surface_emprise_m2']:8.2f} m²"
              f"   (projetée {res['surface_projetee_emprise_m2']:.2f} m², emprise {emprise.area:.2f} m²)")
        print(f"Surface réelle totale selon nuage de points : {res['surface_nuage_m2']:8.2f} m²"
              f"   (projetée {res.get('surface_projetee_nuage_m2', 0):.2f} m²)")
        if rapport["lineaires_m"]:
            print("Mètres linéaires : " + " · ".join(f"{k} {v:.1f} m" for k, v in rapport["lineaires_m"].items()))
        print(f"Partie de l'emprise non mesurée (aucun point à moins de 1,5 m) : {res['non_mesure_pct']:.1f} %")
        print(f"Date du relevé LiDAR : {infos['date_releve']}")
        fi = rapport["fiabilite"]
        print(f"Fiabilité : {fi['niveau'].upper()}")
        for t in fi["alertes"] + fi["remarques"]:
            print(f"  - {t}")
        print(f"\nRésultats : {dossier}/rapport.json, toit.png et toit.kml (à ouvrir dans Google Earth)")
    return rapport


def _json(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    return str(o)


def main():
    ap = argparse.ArgumentParser(description="Métré de toiture à partir d'une adresse (IGN LiDAR HD).")
    ap.add_argument("adresse", nargs="?", help="adresse postale en France")
    ap.add_argument("--xy", nargs=2, type=float, metavar=("X", "Y"), help="coordonnées Lambert-93 (EPSG:2154)")
    ap.add_argument("--emprise", help="fichier GeoJSON de l'emprise du toit (Lambert-93 ou WGS84)")
    ap.add_argument("--laz", nargs="+", help="fichier(s) LAZ/COPC téléchargé(s) à la main")
    ap.add_argument("--nom", help="nom du dossier de résultats")
    a = ap.parse_args()
    if not (a.adresse or a.xy or a.emprise):
        ap.error("donnez une adresse, --xy X Y ou --emprise")
    try:
        calculer(a.adresse, a.xy, a.emprise, a.laz, nom=a.nom)
    except donnees.ErreurDonnees as e:
        print(f"Erreur : {e}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
