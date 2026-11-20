"""Export GeoJSON des pans (affichage carte) et indice de fiabilité."""
import sys
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_synthetique as T  # noqa: E402
from toiture.analyse import analyser  # noqa: E402
from toiture.donnees import VERS_L93  # noqa: E402
from toiture.export import fiabilite, geojson_pans  # noqa: E402


def test_contours_des_pans():
    emp, z, n, _, _, para = T.toit_4_pans()
    pts, emp_l93 = T.fabriquer(emp, z, np.random.default_rng(5), para)
    res = analyser(pts, emp_l93)
    gj = geojson_pans(res)
    pans = [f for f in gj["features"] if "numero" in f["properties"]]
    assert len(pans) == n
    assert {f["properties"].get("role") for f in gj["features"]} >= {"emprise", "nuage"}
    total = 0.0
    polys = []
    for f in pans:
        g = shape(f["geometry"])
        g93 = shapely.transform(g, lambda c: np.c_[VERS_L93.transform(c[:, 0], c[:, 1])])
        assert g93.is_valid
        # un contour d'un seul tenant, sans « fentes » entre cellules
        assert g93.geom_type == "Polygon", g93.geom_type
        total += g93.area
        polys.append(g93)
    # les contours couvrent la surface projetée calculée (à 1 % près) sans se chevaucher
    assert abs(total - res["surface_projetee_emprise_m2"]) / res["surface_projetee_emprise_m2"] < 0.01
    assert shapely.union_all(polys).area > 0.99 * total


def test_fiabilite():
    base = {"localisation": {"score": 0.95}, "emprise": {"distance_au_point_m": 0.0},
            "pans": [{"ecart_moyen_cm": 2.0, "pente_deg": 35.0}], "non_mesure_pct": 0.5,
            "surface_emprise_m2": 100.0, "surface_nuage_m2": 102.0, "densite_points_m2": 12,
            "lidar": {"date_releve": "2025-01-14"}}
    assert fiabilite(base)["niveau"] == "vert"
    mauvais = {**base, "localisation": {"score": 0.4, "adresse_trouvee": "ailleurs"}}
    assert fiabilite(mauvais)["niveau"] == "rouge"
    arbre = {**base, "non_mesure_pct": 25.0}
    assert fiabilite(arbre)["niveau"] == "rouge"


def test_kml_google_earth():
    import xml.etree.ElementTree as ET
    from toiture.export import kml_pans
    emp, z, n, _, _, para = T.toit_2_pans()
    pts, emp_l93 = T.fabriquer(emp, z, np.random.default_rng(2), para)
    res = analyser(pts, emp_l93)
    racine = ET.fromstring(kml_pans(res, "Essai", z_sol=0.0, date_releve="2025-01-14").encode())
    ns = {"k": "http://www.opengis.net/kml/2.2"}
    assert len(racine.findall(".//k:Placemark", ns)) == n + 1        # pans + emprise
    h = np.concatenate([[float(v.split(",")[2]) for v in c.text.split()]
                        for c in racine.findall(".//k:Polygon//k:coordinates", ns)])
    # gouttière à 6 m, faîtage à 6 + tan(35°) × 4,5 ≈ 9,15 m
    assert 5.5 < h.min() < 6.5 and 8.7 < h.max() < 9.6, (h.min(), h.max())
