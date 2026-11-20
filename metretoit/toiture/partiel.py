"""Métré d'une PARTIE du toit (devis partiel) : pans choisis ou zone dessinée.

On réutilise le découpage fait sur le toit entier (enregistré dans grille.npz) :
c'est plus fiable que de refaire la détection des pans sur un petit morceau.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import shapely
from shapely.geometry import LineString

from .lignes import TYPES

MARGE_LIGNES = 0.5      # m : une ligne (égout, faîtage…) au bord de la zone dessinée est comptée


def enregistrer_grille(dossier: Path, res: dict):
    g = res.get("grille_emprise")
    if g is None:
        return
    np.savez_compressed(dossier / "grille.npz", etiquettes=g.etiquettes.astype(np.int16),
                        x0=g.x0, y0=g.y0, cellule=g.cellule, origine=np.asarray(res["origine"]),
                        cos_pente=np.array([abs(p.normale[2]) for p in res["objets_pans"]]),
                        numeros=np.array([p["numero"] for p in res["pans"]]))


def metre_zone(dossier: Path, zone_l93) -> dict:
    """Surface et linéaires des parties du toit situées dans la zone (polygone Lambert-93)."""
    z = np.load(dossier / "grille.npz")
    rap = json.loads((dossier / "rapport.json").read_text())
    ox, oy = float(z["origine"][0]), float(z["origine"][1])
    lab, c = z["etiquettes"], float(z["cellule"])
    ny, nx = lab.shape
    X = float(z["x0"]) + ox + (np.arange(nx) + 0.5) * c
    Y = float(z["y0"]) + oy + (np.arange(ny) + 0.5) * c
    XX, YY = np.meshgrid(X, Y)
    dedans = shapely.contains_xy(zone_l93, XX, YY) & (lab >= 0)
    infos = {p["numero"]: p for p in rap["pans"]}
    pans = []
    for k, num in enumerate(z["numeros"]):
        n = int((dedans & (lab == k)).sum())
        if n == 0:
            continue
        proj = n * c * c
        p = infos[int(num)]
        pans.append({"numero": int(num), "pente_deg": p["pente_deg"], "pente_pct": p["pente_pct"],
                     "orientation": p["orientation"], "type": p["type"],
                     "surface_projetee_m2": round(proj, 2), "surface_reelle_m2": round(proj / z["cos_pente"][k], 2),
                     "part_du_pan_pct": round(100 * proj / max(p["surface_projetee_m2"], 1e-6), 0)})
    # lignes : la partie de chaque ligne qui tombe dans la zone (élargie de 50 cm)
    zone_large = zone_l93.buffer(MARGE_LIGNES)
    lin = {}
    lignes_zone = []
    for l in rap.get("lignes", []):
        geo = LineString(l["coords_l93"])
        if geo.length < 1e-6:
            continue
        part = geo.intersection(zone_large).length / geo.length
        if part < 0.02:
            continue
        lg = l["longueur_m"] * part
        lin[l["type"]] = lin.get(l["type"], 0.0) + lg
        lignes_zone.append({**{k: v for k, v in l.items() if k != "coords"}, "longueur_dans_zone_m": round(lg, 2)})
    return {"pans": pans,
            "surface_reelle_m2": round(sum(p["surface_reelle_m2"] for p in pans), 2),
            "surface_projetee_m2": round(sum(p["surface_projetee_m2"] for p in pans), 2),
            "lineaires_m": {k: round(lin[k], 2) for k in TYPES if k in lin},
            "lignes": lignes_zone}
