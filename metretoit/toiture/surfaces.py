"""Calcul des surfaces par pan, selon l'emprise et selon le nuage de points."""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import shapely
from scipy import ndimage
from scipy.spatial import cKDTree

from .segmentation import Pan

CELLULE = 0.0625               # m (6,25 cm : un faîtage aligné sur la grille ne fausse plus le partage entre pans)
AIRE_CELLULE = CELLULE ** 2
DIST_NON_MESUREE = 1.5         # m
RAYON_FERMETURE = 1.5          # m, pour l'enveloppe du nuage
CELLULE_NUAGE = 0.10           # m, grille fine pour l'enveloppe du nuage


CELLULES_MAX = 600_000           # au-delà, on grossit les cellules (grands bâtiments)


def taille_cellule(aire_zone: float, base: float) -> float:
    """Cellules fines pour une maison ; plus grandes pour un entrepôt, afin de garder
    un calcul rapide (l'erreur d'arrondi reste négligeable sur une grande surface)."""
    c = base
    while aire_zone / (c * c) > CELLULES_MAX:
        c *= 2
    return c


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


def _attribuer(cx, cy, pts, pans, xy, k, arbre):
    """Pan de chaque cellule. Parmi les pans présents tout près (8 points les plus
    proches), on prend celui dont le plan passe à la hauteur réellement mesurée à cet
    endroit (moyenne pondérée des 4 points les plus proches). Faîtages et noues
    sont ainsi bien droits, au lieu d'être en « escalier »."""
    q = np.c_[cx, cy]
    d, i = arbre.query(q, k=min(8, len(xy)))
    if d.ndim == 1:
        d, i = d[:, None], i[:, None]
    z_pts = np.concatenate([pts[p.indices, 2] for p in pans])
    w = 1.0 / np.maximum(d[:, :4], 0.05)
    z_loc = (z_pts[i[:, :4]] * w).sum(1) / w.sum(1)
    cand = k[i]                                    # (n, 8) étiquettes candidates
    best = cand[:, 0].copy()
    best_err = np.full(len(q), np.inf)
    for kk, p in enumerate(pans):
        est = (cand == kk).any(axis=1)
        if not est.any():
            continue
        nx, ny, nz = p.normale
        zp = p.centre[2] - (nx * (cx[est] - p.centre[0]) + ny * (cy[est] - p.centre[1])) / nz
        err = np.abs(zp - z_loc[est])
        idx = np.where(est)[0]
        mieux = err < best_err[idx]
        best[idx[mieux]], best_err[idx[mieux]] = kk, err[mieux]
    return best, d[:, 0]


def _nettoyer_ilots(etiq: np.ndarray, aire_cellule: float, aire_min: float = 0.5) -> None:
    """Un îlot de moins de 0,5 m² d'un pan, perdu au milieu d'un autre pan (bruit),
    est rendu au pan qui l'entoure. La surface totale ne change pas."""
    n_min = max(1, int(round(aire_min / aire_cellule)))
    ny, nx = etiq.shape
    for k in np.unique(etiq[etiq >= 0]):
        lab, n = ndimage.label(etiq == k)
        if n <= 1:
            continue
        tailles = np.bincount(lab.ravel(), minlength=n + 1)[1:]
        petits = np.where(tailles < n_min)[0] + 1
        if not len(petits):
            continue
        boites = ndimage.find_objects(lab)
        for j in petits:
            sl = boites[j - 1]
            y0, y1 = max(sl[0].start - 1, 0), min(sl[0].stop + 1, ny)
            x0, x1 = max(sl[1].start - 1, 0), min(sl[1].stop + 1, nx)
            m = lab[y0:y1, x0:x1] == j
            bord = ndimage.binary_dilation(m) & ~m
            autour = etiq[y0:y1, x0:x1][bord]
            autour = autour[(autour >= 0) & (autour != k)]
            if len(autour):
                etiq[y0:y1, x0:x1][m] = np.bincount(autour).argmax()


def grille_emprise(pts, pans: list[Pan], emprise) -> Grille:
    """Cellules de l'emprise attribuées au pan du point le plus proche."""
    g = _grille_vide(*emprise.bounds, taille_cellule(emprise.envelope.area, CELLULE))
    X, Y = g.centres()
    dedans = shapely.contains_xy(emprise, X, Y)
    if pans:
        xy, k = _points_pans(pts, pans)
        best, d = _attribuer(X[dedans], Y[dedans], pts, pans, xy, k, cKDTree(xy))
        lab = np.where(d <= DIST_NON_MESUREE, best, -1)
    else:
        lab = -1
    g.etiquettes[dedans] = lab
    _nettoyer_ilots(g.etiquettes, g.aire_cellule)
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
    c = taille_cellule((mx[0] - mn[0]) * (mx[1] - mn[1]), CELLULE_NUAGE)
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
    xy_t, k_t = _points_pans(pts, pans)
    best, _ = _attribuer(X[couvert], Y[couvert], pts, pans, xy_t, k_t, cKDTree(xy_t))
    g.etiquettes[couvert] = best
    _nettoyer_ilots(g.etiquettes, g.aire_cellule)
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
