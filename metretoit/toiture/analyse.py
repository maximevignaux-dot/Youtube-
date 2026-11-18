"""Analyse complète d'un toit à partir des points de classe « bâtiment » et de l'emprise."""
from __future__ import annotations

import numpy as np
import shapely
from shapely import affinity

from . import segmentation as seg
from . import surfaces as surf

SURFACE_MIN = 2.0   # m² projetés
SECTEURS = ["N", "NE", "E", "SE", "S", "SO", "O", "NO"]


def orientation(az):
    if az is None:
        return "—"
    return SECTEURS[int(((az + 22.5) % 360) // 45)]


def analyser(pts: np.ndarray, emprise, graine: int = 0, voisins=None) -> dict:
    """pts : (N, 3) points de classe 6 en Lambert-93. emprise : polygone shapely.
    voisins : emprises des bâtiments voisins (leurs toits sont exclus de la marge de 1 m)."""
    # on travaille en coordonnées locales (précision numérique)
    origine = np.array([*emprise.centroid.coords[0], 0.0])
    zone = emprise.buffer(1.0)
    if voisins is not None and not voisins.is_empty:
        zone = zone.difference(voisins.difference(emprise)).union(emprise)
    dedans = shapely.contains_xy(zone, pts[:, 0], pts[:, 1])
    p = pts[dedans] - origine
    emp = affinity.translate(emprise, -origine[0], -origine[1])

    pans = seg.detecter_pans(p, graine=graine) if len(p) >= seg.MIN_POINTS else []
    # tri : plus grand pan d'abord
    pans.sort(key=lambda q: -len(q.indices))

    res = {"nb_points_classe6": int(len(p)), "pans": [], "origine": origine.tolist()}
    if not pans:
        res.update(surface_emprise_m2=0.0, surface_nuage_m2=0.0, non_mesure_pct=100.0,
                   surface_projetee_emprise_m2=0.0, grille_emprise=None, grille_nuage=None,
                   emprise_locale=emp, points_locaux=p, objets_pans=[])
        return res

    # un « pan » qui couvre moins de 2 m² vu de dessus (côté de cheminée, lucarne
    # minuscule, branche…) est écarté : ses cellules reviennent aux pans voisins.
    while True:
        g_emp = surf.grille_emprise(p, pans, emp)
        g_nua = surf.grille_nuage(p, pans)
        # Un vrai pan de ce bâtiment est surtout DANS l'emprise (les débords font
        # moins de 1 m). Un plan majoritairement dehors = arbre, toit voisin, bruit.
        petits = []
        for k, q in enumerate(pans):
            xy = p[q.indices]
            part_dedans = shapely.contains_xy(emp, xy[:, 0], xy[:, 1]).mean()
            if part_dedans < 0.5 or (g_emp.etiquettes == k).sum() * g_emp.aire_cellule < SURFACE_MIN:
                petits.append(k)
        if not petits or len(petits) == len(pans):
            break
        pans = [q for k, q in enumerate(pans) if k not in petits]
    s_emp = surf.surfaces_par_pan(g_emp, pans)
    s_nua = surf.surfaces_par_pan(g_nua, pans)

    for k, (q, se, sn) in enumerate(zip(pans, s_emp, s_nua), start=1):
        pente = q.pente_deg
        az = q.azimut_deg
        res["pans"].append({
            "numero": k,
            "type": "toit plat" if q.plat else "pan incliné",
            "pente_deg": round(pente, 1),
            "pente_pct": round(100 * np.tan(np.radians(pente)), 1),
            "azimut_deg": None if az is None else round(az),
            "orientation": orientation(az),
            "surface_projetee_m2": round(se["projetee"], 2),
            "surface_reelle_m2": round(se["reelle"], 2),
            "surface_projetee_nuage_m2": round(sn["projetee"], 2),
            "surface_reelle_nuage_m2": round(sn["reelle"], 2),
            "nb_points": int(len(q.indices)),
            "ecart_moyen_cm": round(100 * q.ecart_moyen, 1),
            "altitude_moyenne_m": round(float(q.centre[2]), 2),
        })
    res["surface_emprise_m2"] = round(sum(s["reelle"] for s in s_emp), 2)
    res["surface_projetee_emprise_m2"] = round(sum(s["projetee"] for s in s_emp), 2)
    res["surface_nuage_m2"] = round(sum(s["reelle"] for s in s_nua), 2)
    res["surface_projetee_nuage_m2"] = round(sum(s["projetee"] for s in s_nua), 2)
    res["aire_emprise_m2"] = round(emprise.area, 2)
    res["non_mesure_pct"] = round(surf.pourcentage_non_mesure(g_emp), 1)
    # objets utiles pour le dessin (non sérialisés)
    res.update(grille_emprise=g_emp, grille_nuage=g_nua, emprise_locale=emp,
               points_locaux=p, objets_pans=pans)
    return res


CLES_INTERNES = ("grille_emprise", "grille_nuage", "emprise_locale", "points_locaux", "objets_pans")


def pour_json(res: dict) -> dict:
    return {k: v for k, v in res.items() if k not in CLES_INTERNES}
