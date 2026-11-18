"""Toits simulés dont on connaît les mesures exactes.

10 points/m², bruit 5 cm, points parasites (cheminée, branches d'arbre, mur).
Critères : bon nombre de pans, erreur de pente < 1°, erreur de surface < 2 %.
Lancement : .venv/bin/python -m pytest tests -v
"""
import sys
from pathlib import Path

import numpy as np
import pytest
from shapely.geometry import Polygon, box
from shapely.ops import unary_union
import shapely

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from toiture.analyse import analyser  # noqa: E402

DENSITE = 10.0
BRUIT = 0.05
X0, Y0 = 432000.0, 6713000.0   # on se place en coordonnées Lambert-93 réalistes
H_GOUTTIERE = 6.0


def semer(poly, rng, densite=DENSITE):
    n = rng.poisson(densite * poly.area)
    xmin, ymin, xmax, ymax = poly.bounds
    pts = []
    while sum(len(p) for p in pts) < n:
        c = rng.uniform([xmin, ymin], [xmax, ymax], (2 * n, 2))
        pts.append(c[shapely.contains_xy(poly, c[:, 0], c[:, 1])])
    return np.concatenate(pts)[:n]


def parasites(rng, cx, cy, z_toit):
    """Cheminée 0,8 × 0,8 m (1,2 m de haut), branches au-dessus du toit, un bout de mur."""
    out = []
    # cheminée : dessus + côtés
    top = rng.uniform([cx, cy], [cx + 0.8, cy + 0.8], (8, 2))
    out.append(np.c_[top, np.full(8, z_toit(cx, cy) + 1.2)])
    for _ in range(30):
        t = rng.uniform(0, 0.8)
        cote = rng.integers(4)
        x, y = [(cx + t, cy), (cx + t, cy + 0.8), (cx, cy + t), (cx + 0.8, cy + t)][cote]
        out.append(np.array([[x, y, z_toit(x, y) + rng.uniform(0, 1.2)]]))
    # branches d'arbre débordant sur le toit : nuage diffus
    b = rng.uniform([cx - 4, cy - 4, 0.3], [cx - 1, cy - 1, 2.5], (70, 3))
    b[:, 2] += np.array([z_toit(x, y) for x, y in b[:, :2]])
    out.append(b)
    return np.concatenate(out)


def mur(rng, x0, x1, y):
    n = 60
    return np.c_[rng.uniform(x0, x1, n), np.full(n, y), rng.uniform(0.5, H_GOUTTIERE, n)]


def fabriquer(emprise, z, rng, parasite_xy):
    xy = semer(emprise, rng)
    zz = np.array([z(x, y) for x, y in xy]) + rng.normal(0, BRUIT, len(xy))
    pts = np.c_[xy, zz]
    para = parasites(rng, *parasite_xy, z)
    xmin, ymin, xmax, _ = emprise.bounds
    pts = np.concatenate([pts, para, mur(rng, xmin, xmax, ymin)])
    pts[:, 0] += X0
    pts[:, 1] += Y0
    from shapely import affinity
    return pts, affinity.translate(emprise, X0, Y0)


# ---------- définitions des toits ----------

def toit_2_pans():
    t = np.tan(np.radians(35))
    emp = box(0, 0, 12, 9)
    z = lambda x, y: H_GOUTTIERE + t * min(y, 9 - y)
    return emp, z, 2, [35], emp.area / np.cos(np.radians(35)), (5, 2)


def toit_4_pans():
    t = np.tan(np.radians(30))
    emp = box(0, 0, 13, 9)
    z = lambda x, y: H_GOUTTIERE + t * min(x, 13 - x, y, 9 - y)
    return emp, z, 4, [30], emp.area / np.cos(np.radians(30)), (6, 2)


def toit_en_L():
    """Deux ailes de 8 m de large (20 m de long) à 35°, croupe à l'angle extérieur,
    noue à l'angle intérieur. Tous les pans ont la même pente."""
    t = np.tan(np.radians(35))
    emp = unary_union([box(0, 0, 20, 8), box(0, 0, 8, 20)])

    def z(x, y):
        a = min(y, 8 - y, x) if y <= 8 else -np.inf     # aile A (le long de x)
        b = min(x, 8 - x, y) if x <= 8 else -np.inf     # aile B (le long de y)
        return H_GOUTTIERE + t * max(a, b)
    return emp, z, 4, [35], emp.area / np.cos(np.radians(35)), (14, 1.5)


def toit_plat():
    pente = 1.0
    t = np.tan(np.radians(pente))
    emp = box(0, 0, 15, 10)
    z = lambda x, y: H_GOUTTIERE + t * x
    return emp, z, 1, [pente], emp.area / np.cos(np.radians(pente)), (7, 5)


CAS = {"2 pans 35°": toit_2_pans, "4 pans 30°": toit_4_pans,
       "en L 2 ailes": toit_en_L, "toit plat": toit_plat}


GRAINES = range(1, 11)
_ERREURS_NUAGE: dict[str, list[float]] = {}


@pytest.mark.parametrize("nom", list(CAS))
@pytest.mark.parametrize("graine", GRAINES)
def test_toit(nom, graine):
    emp, z, nb_pans, pentes, surface_vraie, para = CAS[nom]()
    rng = np.random.default_rng(graine)
    pts, emp_l93 = fabriquer(emp, z, rng, para)
    res = analyser(pts, emp_l93)

    resume = [(p["pente_deg"], p["orientation"], p["surface_reelle_m2"], p["nb_points"]) for p in res["pans"]]
    print(nom, resume, res["surface_emprise_m2"], res["surface_nuage_m2"], round(surface_vraie, 2))

    # 1) bon nombre de pans
    assert len(res["pans"]) == nb_pans, resume
    # 2) erreur de pente < 1°
    for p in res["pans"]:
        assert min(abs(p["pente_deg"] - v) for v in pentes) < 1.0, p
    # 3) erreur de surface < 2 % (surface selon emprise : critère strict, toit par toit)
    err_emp = abs(res["surface_emprise_m2"] - surface_vraie) / surface_vraie
    assert err_emp < 0.02, f"surface emprise : écart {100 * err_emp:.2f} %"
    # Surface selon nuage : le bord exact du toit tombe entre deux points (10 pts/m²),
    # d'où un aléa d'environ ±0,7 % : < 3 % par tirage, < 2 % en moyenne (test suivant).
    err_nua = (res["surface_nuage_m2"] - surface_vraie) / surface_vraie
    _ERREURS_NUAGE.setdefault(nom, []).append(err_nua)
    assert abs(err_nua) < 0.03, f"surface nuage : écart {100 * err_nua:.2f} %"
    if nom == "toit plat":
        assert res["pans"][0]["type"] == "toit plat"


@pytest.mark.parametrize("nom", list(CAS))
def test_surface_nuage_moyenne(nom):
    errs = _ERREURS_NUAGE.get(nom)
    if not errs:
        pytest.skip("lancer avec test_toit")
    moy = float(np.mean(np.abs(errs)))
    assert moy < 0.02, f"surface nuage : écart moyen {100 * moy:.2f} %"
