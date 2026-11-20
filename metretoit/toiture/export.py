"""Export des pans en GeoJSON (WGS84) pour l'affichage sur carte, et indice de fiabilité."""
from __future__ import annotations

import datetime as dt

import numpy as np
import shapely
from shapely import affinity

from .donnees import VERS_WGS84


def _vers_wgs84(geom):
    return shapely.transform(geom, lambda c: np.c_[VERS_WGS84.transform(c[:, 0], c[:, 1])])


def _contour_cellules(g, masque, simpl):
    """Polygone exact d'un ensemble de cellules : on assemble des carrés en indices
    entiers (aucune fente due aux arrondis), puis on passe en mètres."""
    if not masque.any():
        return shapely.Polygon()
    # bandes horizontales (suites de cellules d'une même ligne) : bien moins de
    # rectangles à assembler que de cellules
    m = np.pad(masque.astype(np.int8), ((0, 0), (1, 1)))
    dm = np.diff(m, axis=1)
    ys, x_deb = np.nonzero(dm == 1)
    _, x_fin = np.nonzero(dm == -1)
    poly = shapely.union_all(shapely.box(x_deb, ys, x_fin, ys + 1))
    poly = affinity.affine_transform(poly, [g.cellule, 0, 0, g.cellule, g.x0, g.y0])
    return poly.simplify(simpl)


def geojson_pans(res: dict) -> dict:
    """Contour de chaque pan (cellules de la grille emprise regroupées) + emprise."""
    feats = []
    g = res.get("grille_emprise")
    ox, oy = res["origine"][0], res["origine"][1]
    if g is not None:
        for k, p in enumerate(res["pans"]):
            m = g.etiquettes == k
            if not m.any():
                continue
            poly = _contour_cellules(g, m, 0.05)
            ref = poly.point_on_surface() if not poly.is_empty else poly.centroid
            # point d'étiquette : le plus loin possible du bord
            try:
                ref = shapely.Point(shapely.maximum_inscribed_circle(poly).coords[0]) \
                    if poly.geom_type == "Polygon" else ref
            except Exception:  # noqa: BLE001
                pass
            poly = _vers_wgs84(affinity.translate(poly, ox, oy))
            ref = _vers_wgs84(affinity.translate(ref, ox, oy))
            feats.append({"type": "Feature", "geometry": shapely.geometry.mapping(poly),
                          "properties": {**p, "etiquette": [ref.x, ref.y]}})
    emp = _vers_wgs84(affinity.translate(res["emprise_locale"], ox, oy))
    feats.append({"type": "Feature", "geometry": shapely.geometry.mapping(emp),
                  "properties": {"role": "emprise"}})
    gn = res.get("grille_nuage")
    if gn is not None:
        env = _contour_cellules(gn, gn.etiquettes >= 0, 0.1)
        feats.append({"type": "Feature", "geometry": shapely.geometry.mapping(
            _vers_wgs84(affinity.translate(env, ox, oy))), "properties": {"role": "nuage"}})
    return {"type": "FeatureCollection", "features": feats}


def fiabilite(rapport: dict) -> dict:
    """Indice de confiance simple : vert / orange / rouge + les raisons."""
    alertes, info = [], []

    def a(niveau, texte):
        (alertes if niveau == 2 else info).append(texte)

    loc = rapport.get("localisation", {})
    if loc.get("score") is not None and loc["score"] < 0.7:
        a(2, f"Adresse incertaine (score de géocodage {loc['score']:.2f}, trouvé : « {loc.get('adresse_trouvee')} »). "
             "Vérifiez que c'est le bon bâtiment.")
    emp = rapport.get("emprise", {})
    if emp.get("distance_au_point_m", 0) > 0:
        a(1, f"Le point de l'adresse tombe hors bâtiment : bâtiment le plus proche pris ({emp['distance_au_point_m']} m).")
    if not rapport.get("pans"):
        a(2, "Aucun pan détecté (pas de points « bâtiment » dans le LiDAR à cet endroit).")
    if rapport.get("non_mesure_pct", 0) > 10:
        a(2, f"{rapport['non_mesure_pct']:.0f} % du toit sans mesure (arbre, verrière, toit récent ?).")
    elif rapport.get("non_mesure_pct", 0) > 3:
        a(1, f"{rapport['non_mesure_pct']:.0f} % du toit sans mesure.")
    se, sn = rapport.get("surface_emprise_m2") or 0, rapport.get("surface_nuage_m2") or 0
    if se and abs(sn - se) / se > 0.10:
        a(2, f"Emprise BD TOPO et nuage de points très différents ({se:.0f} / {sn:.0f} m²) : "
             "bâtiment mitoyen, gros débords ou emprise imprécise.")
    elif se and abs(sn - se) / se > 0.05:
        a(1, f"Écart emprise / nuage de {100 * abs(sn - se) / se:.0f} % (débords de toit ?).")
    pans = rapport.get("pans", [])
    if any(p["ecart_moyen_cm"] > 5 for p in pans):
        a(1, "Certains pans sont irréguliers (points dispersés de plus de 5 cm autour du plan).")
    if any(p["pente_deg"] > 60 for p in pans):
        a(1, "Pan très raide (> 60°) : mal vu d'avion, surface moins sûre.")
    if len(pans) > 8:
        a(1, f"Toit complexe ({len(pans)} pans).")
    if rapport.get("densite_points_m2", 99) < 5:
        a(1, f"Peu de points LiDAR ({rapport['densite_points_m2']} / m²).")
    date = (rapport.get("lidar", {}).get("date_releve") or "")[:10]
    try:
        age = (dt.date.today() - dt.date.fromisoformat(date)).days / 365.25
        if age > 3:
            a(1, f"Relevé LiDAR de {date} (il y a {age:.0f} ans) : travaux récents non visibles.")
    except ValueError:
        pass
    niveau = "rouge" if alertes else ("orange" if len(info) >= 2 else "vert")
    return {"niveau": niveau, "alertes": alertes, "remarques": info}


# ---------------- Export Google Earth (KML 3D) ----------------

COULEURS_KML = ["#4E79A7", "#F28E2B", "#59A14F", "#E15759", "#B07AA1", "#76B7B2", "#EDC948",
                "#FF9DA7", "#9C755F", "#86BCB6", "#D37295", "#A0CBE8", "#8CD17D", "#F1CE63"]


def _abgr(hexa: str, alpha: int) -> str:
    """Couleur KML : aabbggrr."""
    r, g, b = hexa[1:3], hexa[3:5], hexa[5:7]
    return f"{alpha:02x}{b}{g}{r}".lower()


def _esc(t) -> str:
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def kml_pans(res: dict, titre: str, z_sol: float, date_releve: str = "") -> str:
    """Fichier KML à ouvrir dans Google Earth : chaque pan est un polygone 3D posé à sa
    vraie pente et à sa hauteur au-dessus du sol (mesurée par le LiDAR)."""
    g = res.get("grille_emprise")
    ox, oy = res["origine"][0], res["origine"][1]

    def anneau(coords, plan=None, h_fixe=None):
        xy = np.asarray(coords)[:, :2]
        if plan is not None:
            nx, ny, nz = plan.normale
            cx, cy, cz = plan.centre
            z = cz - (nx * (xy[:, 0] - cx) + ny * (xy[:, 1] - cy)) / nz
        else:
            z = np.full(len(xy), h_fixe)
        lon, lat = VERS_WGS84.transform(xy[:, 0] + ox, xy[:, 1] + oy)
        h = np.maximum(z - z_sol, 0.0)
        return " ".join(f"{a:.8f},{b:.8f},{c:.2f}" for a, b, c in zip(lon, lat, h))

    def polygones(geom, **kw):
        out = []
        for p in getattr(geom, "geoms", [geom]):
            if p.is_empty or p.geom_type != "Polygon":
                continue
            s = f"<Polygon><altitudeMode>relativeToGround</altitudeMode><outerBoundaryIs><LinearRing><coordinates>{anneau(p.exterior.coords, **kw)}</coordinates></LinearRing></outerBoundaryIs>"
            for t in p.interiors:
                s += f"<innerBoundaryIs><LinearRing><coordinates>{anneau(t.coords, **kw)}</coordinates></LinearRing></innerBoundaryIs>"
            out.append(s + "</Polygon>")
        return out

    styles, marques = [], []
    if g is not None:
        for k, (p, q) in enumerate(zip(res["pans"], res["objets_pans"])):
            m = g.etiquettes == k
            if not m.any():
                continue
            poly = _contour_cellules(g, m, 0.15)
            if poly.is_empty:
                continue
            coul = COULEURS_KML[k % len(COULEURS_KML)]
            styles.append(f'<Style id="pan{k}"><LineStyle><color>{_abgr("#000000", 255)}</color><width>1</width></LineStyle>'
                          f'<PolyStyle><color>{_abgr(coul, 200)}</color></PolyStyle></Style>')
            desc = (f"{_esc(p['type'])}<br>Pente : {p['pente_deg']}° ({p['pente_pct']} %)<br>"
                    f"Orientation : {_esc(p['orientation'])}" + (f" ({p['azimut_deg']}°)" if p['azimut_deg'] is not None else "")
                    + f"<br>Surface réelle : <b>{p['surface_reelle_m2']} m²</b><br>Surface vue de dessus : {p['surface_projetee_m2']} m²"
                    f"<br>{p['nb_points']} points LiDAR, écart moyen {p['ecart_moyen_cm']} cm")
            geoms = polygones(poly, plan=q)
            corps = geoms[0] if len(geoms) == 1 else "<MultiGeometry>" + "".join(geoms) + "</MultiGeometry>"
            marques.append(f'<Placemark><name>Pan {p["numero"]} — {p["surface_reelle_m2"]} m²</name>'
                           f'<description><![CDATA[{desc}]]></description><styleUrl>#pan{k}</styleUrl>{corps}</Placemark>')
    # contour de l'emprise BD TOPO, au sol
    emp = res["emprise_locale"]
    lignes = []
    for p in getattr(emp, "geoms", [emp]):
        lignes.append(f"<LineString><altitudeMode>clampToGround</altitudeMode><coordinates>{anneau(p.exterior.coords, h_fixe=z_sol)}</coordinates></LineString>")
    styles.append('<Style id="emprise"><LineStyle><color>ff00ffff</color><width>2</width></LineStyle></Style>')
    marques.append('<Placemark><name>Emprise BD TOPO (au sol)</name><styleUrl>#emprise</styleUrl><MultiGeometry>'
                   + "".join(lignes) + "</MultiGeometry></Placemark>")
    lon, lat = VERS_WGS84.transform(emp.centroid.x + ox, emp.centroid.y + oy)
    resume = (f"Surface selon emprise : {res.get('surface_emprise_m2')} m²<br>"
              f"Surface selon nuage de points : {res.get('surface_nuage_m2')} m²<br>"
              f"Relevé LiDAR HD : {_esc(date_releve)}<br>Données © IGN (LiDAR HD, BD TOPO), licence Etalab 2.0")
    vue = (f"<LookAt><longitude>{lon:.7f}</longitude><latitude>{lat:.7f}</latitude><altitude>0</altitude>"
           f"<heading>0</heading><tilt>50</tilt><range>{max(40.0, 3 * np.sqrt(emp.area)):.0f}</range></LookAt>")
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<kml xmlns="http://www.opengis.net/kml/2.2"><Document>'
            f"<name>{_esc(titre)}</name><description><![CDATA[{resume}]]></description><open>1</open>{vue}"
            + "".join(styles) + "".join(marques) + "</Document></kml>\n")
