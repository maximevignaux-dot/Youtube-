"""Calcul des surfaces par pan, selon l'emprise et selon le nuage de points."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely
from scipy import ndimage
from scipy.spatial import cKDTree

from .segmentation import Pan

CELLULE = 0.25                 # m
AIRE_CELLULE = CELLULE ** 2    # 0,0625 m²
DIST_NON_MESUREE = 1.5         # m
RAYON_FERMETURE = 1.5          # m, pour l'enveloppe du nuage
CELLULE_NUAGE = 0.10           # m, grille fine pour l'enveloppe du nuage


@dataclass
class Grille:
    x0: float
    y0: float
    nx: int
    ny: int
    etiquettes: np.ndarray     # (ny, nx) : -2 hors zone, -1 non mesurée, k = pan k
    cellule: float = CELLULE
    demi_maille: float = 0.0

    def centres(self):
        xs = self.x0 + (np.arange(self.nx) + 0.5) * self.cellule
        ys = self.y0 + (np.arange(self.ny) + 0.5) * self.cellule
        return np.meshgrid(xs, ys)

    @property
    def aire_cellule(self):
        return self.cellule ** 2

    @property
    def etendue(self):
        return (self.x0, self.x0 + self.nx * self.cellule, self.y0, self.y0 + self.ny * self.cellule)


def _grille_vide(xmin, ymin, xmax, ymax, c=CELLULE) -> Grille:
    x0 = np.floor(xmin / c) * c
    y0 = np.floor(ymin / c) * c
    nx = int(np.ceil((xmax - x0) / c))
    ny = int(np.ceil((ymax - y0) / c))
    return Grille(x0, y0, nx, ny, np.full((ny, nx), -2, dtype=int), c)


def _points_pans(pts, pans):
    xy = np.concatenate([pts[p.indices, :2] for p in pans])
    k = np.concatenate([np.full(len(p.indices), i) for i, p in enumerate(pans)])
    return xy, k


def grille_emprise(pts, pans: list[Pan], emprise) -> Grille:
    """Cellules de l'emprise attribuées au pan du point le plus proche."""
    g = _grille_vide(*emprise.bounds)
    X, Y = g.centres()
    dedans = shapely.contains_xy(emprise, X, Y)
    if pans:
        xy, k = _points_pans(pts, pans)
        d, i = cKDTree(xy).query(np.c_[X[dedans], Y[dedans]])
        lab = np.where(d <= DIST_NON_MESUREE, k[i], -1)
    else:
        lab = -1
    g.etiquettes[dedans] = lab
    return g


def grille_nuage(pts, pans: list[Pan], marge: float = 2.0) -> Grille:
    """Étendue des points eux-mêmes : fermeture morphologique (on comble les trous
    entre points, sans déborder au-delà des points les plus extérieurs)."""
    xy, k = _points_pans(pts, pans)
    # on ignore les points isolés (feuillage, bruit) : un vrai bord de toit a des voisins
    arbre = cKDTree(xy)
    d_nn = arbre.query(xy, k=2)[0][:, 1]
    espacement = 2 * float(np.median(d_nn))         # ≈ 1/√densité
    nb = arbre.query_ball_point(xy, 2.5 * espacement, return_length=True) - 1
    ok = nb >= 3
    if ok.sum() >= 3:
        xy, k = xy[ok], k[ok]
    mn, mx = xy.min(axis=0) - marge - RAYON_FERMETURE, xy.max(axis=0) + marge + RAYON_FERMETURE
    c = CELLULE_NUAGE
    g = _grille_vide(mn[0], mn[1], mx[0], mx[1], c)
    X, Y = g.centres()
    arbre = cKDTree(xy)
    d, i = arbre.query(np.c_[X.ravel(), Y.ravel()])
    d, i = d.reshape(X.shape), i.reshape(X.shape)
    dil = d < RAYON_FERMETURE
    # érosion du même rayon -> fermeture
    dist_ext = ndimage.distance_transform_edt(dil) * c
    enveloppe = dist_ext > RAYON_FERMETURE + c / 2   # passe par les points les plus extérieurs
    # Les points les plus extérieurs sont en moyenne à une demi-maille du vrai bord :
    # on élargit donc l'enveloppe d'une demi-maille, estimée d'après la densité.
    densite = len(xy) / max(enveloppe.sum() * c * c, 1e-6)
    demi_maille = 0.5 / np.sqrt(densite)
    couvert = dist_ext > RAYON_FERMETURE + c / 2 - demi_maille
    couvert |= d < c / 2           # toujours garder les cellules contenant un point
    g.demi_maille = float(demi_maille)
    g.etiquettes[couvert] = k[i[couvert]]
    return g


def surfaces_par_pan(g: Grille, pans: list[Pan]):
    res = []
    for k, p in enumerate(pans):
        n = int((g.etiquettes == k).sum())
        proj = n * g.aire_cellule
        cosp = abs(p.normale[2])
        res.append({"projetee": proj, "reelle": proj / cosp})
    return res


def pourcentage_non_mesure(g: Grille) -> float:
    tot = (g.etiquettes >= -1).sum()
    return float(100 * (g.etiquettes == -1).sum() / tot) if tot else 0.0
