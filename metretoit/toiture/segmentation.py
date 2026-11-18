"""Découpage d'un nuage de points de toit en pans plans.

Étapes : RANSAC successifs -> rejet des murs -> morceaux connexes vus de dessus
-> réattribution fine des points -> fusion des pans coplanaires voisins
-> recalcul par moindres carrés.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

SEUIL_DISTANCE = 0.12      # m, distance max point-plan (RANSAC)
MIN_POINTS = 25            # points minimum par pan
NZ_MIN = 0.2               # composante verticale mini de la normale (sinon mur)
GRILLE_CONNEXITE = 0.5     # m
FUSION_ANGLE = 3.0         # degrés
FUSION_DECALAGE = 0.15     # m
PENTE_PLAT = 3.0           # degrés


@dataclass
class Pan:
    indices: np.ndarray            # indices des points dans le nuage
    normale: np.ndarray            # normale unitaire orientée vers le haut
    centre: np.ndarray             # point moyen
    ecart_moyen: float = 0.0       # m, écart absolu moyen des points au plan
    infos: dict = field(default_factory=dict)

    @property
    def pente_deg(self) -> float:
        return float(np.degrees(np.arccos(np.clip(abs(self.normale[2]), 0, 1))))

    @property
    def azimut_deg(self) -> float | None:
        """Direction vers laquelle descend le pan (0 = Nord, 90 = Est)."""
        if self.pente_deg < PENTE_PLAT:
            return None
        nx, ny = self.normale[0], self.normale[1]
        return float(np.degrees(np.arctan2(nx, ny)) % 360)

    @property
    def plat(self) -> bool:
        return self.pente_deg < PENTE_PLAT


def ajuster_plan(pts: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Plan des moindres carrés (orthogonaux) : renvoie (normale, centre)."""
    c = pts.mean(axis=0)
    _, _, vt = np.linalg.svd(pts - c, full_matrices=False)
    n = vt[-1]
    if n[2] < 0:
        n = -n
    return n / np.linalg.norm(n), c


def distances(pts: np.ndarray, n: np.ndarray, c: np.ndarray) -> np.ndarray:
    return (pts - c) @ n


def _composantes(xy: np.ndarray, taille: float = GRILLE_CONNEXITE) -> np.ndarray:
    """Étiquette des morceaux connexes (vus de dessus) pour chaque point."""
    mn = xy.min(axis=0)
    ij = np.floor((xy - mn) / taille).astype(int)
    grille = np.zeros(ij.max(axis=0) + 1, dtype=bool)
    grille[ij[:, 0], ij[:, 1]] = True
    # petite fermeture pour combler les cellules vides dues à l'échantillonnage
    grille_f = ndimage.binary_closing(np.pad(grille, 1), structure=np.ones((3, 3)))[1:-1, 1:-1] | grille
    lab, _ = ndimage.label(grille_f, structure=np.ones((3, 3)))
    return lab[ij[:, 0], ij[:, 1]]


def _ransac_meilleur_plan(pts, arbre, rng, seuil, n_essais=600, rayon=2.5):
    """Échantillonnage local : 3 points voisins, on garde le plan avec le plus d'inliers."""
    n = len(pts)
    graines = rng.integers(0, n, n_essais)
    voisins = arbre.query_ball_point(pts[graines, :2], r=rayon)
    triplets = []
    for g, v in zip(graines, voisins):
        if len(v) < 3:
            continue
        a, b = rng.choice(v, 2, replace=False)
        triplets.append((g, a, b))
    if not triplets:
        return None
    t = np.array(triplets)
    p0, p1, p2 = pts[t[:, 0]], pts[t[:, 1]], pts[t[:, 2]]
    nrm = np.cross(p1 - p0, p2 - p0)
    long = np.linalg.norm(nrm, axis=1)
    ok = long > 1e-6
    nrm, p0 = nrm[ok] / long[ok, None], p0[ok]
    nrm[nrm[:, 2] < 0] *= -1
    garde = nrm[:, 2] >= NZ_MIN          # on ignore les plans de murs
    nrm, p0 = nrm[garde], p0[garde]
    if len(nrm) == 0:
        return None
    meilleur, score = None, -1
    for k in range(0, len(nrm), 64):     # par paquets pour limiter la mémoire
        nk, pk = nrm[k:k + 64], p0[k:k + 64]
        d = np.abs(nk @ pts.T - np.einsum("kj,kj->k", nk, pk)[:, None])
        cpt = (d < seuil).sum(axis=1)
        i = int(cpt.argmax())
        if cpt[i] > score:
            score, meilleur = int(cpt[i]), (nrm[k + i], p0[k + i])
    return meilleur, score


def detecter_pans(pts: np.ndarray, seuil: float = SEUIL_DISTANCE, min_points: int = MIN_POINTS,
                  graine: int = 0) -> list[Pan]:
    """Détecte les pans de toit dans un nuage (N, 3) en Lambert-93."""
    rng = np.random.default_rng(graine)
    restants = np.arange(len(pts))
    bruts: list[np.ndarray] = []
    echecs = 0
    while len(restants) >= min_points and echecs < 3:
        sous = pts[restants]
        arbre = cKDTree(sous[:, :2])
        res = _ransac_meilleur_plan(sous, arbre, rng, seuil)
        if res is None or res[0] is None or res[1] < min_points:
            break
        (n, c), _ = res
        inl = np.abs(distances(sous, n, c)) < seuil
        n, c = ajuster_plan(sous[inl])
        if n[2] < NZ_MIN:                 # mur : on retire ces points et on continue
            restants = restants[~inl]
            continue
        inl = np.abs(distances(sous, n, c)) < seuil
        lab = _composantes(sous[inl, :2])
        idx_inl = restants[inl]
        trouve = False
        for k in range(1, lab.max() + 1):
            m = lab == k
            if m.sum() >= min_points:
                bruts.append(idx_inl[m])
                trouve = True
        echecs = 0 if trouve else echecs + 1
        restants = restants[~inl]

    pans = [_faire_pan(pts, i) for i in bruts]
    pans = [p for p in pans if p is not None]
    for _ in range(2):
        pans = _reattribuer(pts, pans, seuil, min_points)
    pans = _fusionner(pts, pans)
    pans = _reattribuer(pts, pans, seuil, min_points)
    pans = _retirer_flottants(pts, pans)
    return pans


def _retirer_flottants(pts, pans: list[Pan], rayon=0.35, dz=0.5, part_max=0.3) -> list[Pan]:
    """Le LiDAR voit le dessus du toit : sous un vrai pan, il n'y a pas d'autres
    points de toit. Un plan dont beaucoup de points ont, juste en dessous (< 35 cm
    vu de dessus), un point d'un autre pan plus bas de 0,5 m ou plus, est un plan
    « flottant » : branches d'arbre, câbles, cheminée… On l'écarte.
    Idem pour un plan majoritairement CACHÉ sous un autre pan (façade, mur)."""
    if len(pans) < 2:
        return pans
    garde = []
    for k, p in enumerate(pans):
        autres = np.concatenate([q.indices for j, q in enumerate(pans) if j != k])
        arbre = cKDTree(pts[autres, :2])
        voisins = arbre.query_ball_point(pts[p.indices, :2], r=rayon)
        z = pts[p.indices, 2]
        dessous = np.array([len(v) > 0 and (pts[autres[v], 2] < zi - dz).any()
                            for v, zi in zip(voisins, z)])
        # Inversement, une surface qui a un autre pan AU-DESSUS d'elle (façade sous
        # un débord, mur d'une lucarne…) n'est pas le dessus du toit.
        dessus = np.array([len(v) > 0 and (pts[autres[v], 2] > zi + dz).any()
                           for v, zi in zip(voisins, z)])
        if dessous.mean() <= part_max and dessus.mean() <= part_max:
            garde.append(p)
    return garde


def _faire_pan(pts, idx) -> Pan | None:
    if len(idx) < 3:
        return None
    n, c = ajuster_plan(pts[idx])
    if n[2] < NZ_MIN:
        return None
    d = distances(pts[idx], n, c)
    return Pan(indices=np.asarray(idx), normale=n, centre=c, ecart_moyen=float(np.abs(d).mean()))


def _reattribuer(pts, pans: list[Pan], seuil, min_points) -> list[Pan]:
    """Chaque point va au pan le plus proche (en distance au plan) parmi les pans
    présents à moins de 1 m de lui vu de dessus. Puis recalcul des plans."""
    if not pans:
        return pans
    best_d = np.full(len(pts), np.inf)
    best_k = np.full(len(pts), -1)
    compatible = np.zeros((len(pans), len(pts)), dtype=bool)
    for k, p in enumerate(pans):
        arbre = cKDTree(pts[p.indices, :2])
        dxy, _ = arbre.query(pts[:, :2], distance_upper_bound=1.0)
        d = np.abs(distances(pts, p.normale, p.centre))
        compatible[k] = (dxy < np.inf) & (d < seuil)
        ok = compatible[k] & (d < best_d)
        best_d[ok], best_k[ok] = d[ok], k
    # Lissage : près de la ligne où deux plans se croisent, un point est compatible
    # avec les deux. Il rejoint alors le pan majoritaire parmi ses 10 voisins.
    if len(pans) > 1:
        _, vois = cKDTree(pts[:, :2]).query(pts[:, :2], k=min(11, len(pts)))
        for _ in range(3):
            lab_v = best_k[vois[:, 1:]]
            change = 0
            for k in range(len(pans)):
                votes = (lab_v == k).sum(axis=1)
                autre = np.where(best_k >= 0, (lab_v == best_k[:, None]).sum(axis=1), 0)
                bascule = compatible[k] & (best_k != k) & (votes > autre) & (votes >= 4)
                best_k[bascule] = k
                change += int(bascule.sum())
            if change == 0:
                break
    nouveaux = []
    for k in range(len(pans)):
        idx = np.where(best_k == k)[0]
        if len(idx) < min_points:
            continue
        # on garde le plus gros morceau connexe (+ ceux assez gros)
        lab = _composantes(pts[idx, :2])
        for j in range(1, lab.max() + 1):
            m = lab == j
            if m.sum() >= min_points:
                p = _faire_pan(pts, idx[m])
                if p is not None:
                    nouveaux.append(p)
    return nouveaux


def _voisins(pts, a: Pan, b: Pan, dist=1.0) -> bool:
    ta = cKDTree(pts[a.indices, :2])
    d, _ = ta.query(pts[b.indices, :2], distance_upper_bound=dist)
    return bool(np.isfinite(d).any())


def _fusionner(pts, pans: list[Pan]) -> list[Pan]:
    cos_lim = np.cos(np.radians(FUSION_ANGLE))
    change = True
    while change:
        change = False
        for i in range(len(pans)):
            for j in range(i + 1, len(pans)):
                a, b = pans[i], pans[j]
                if a.normale @ b.normale < cos_lim:
                    continue
                dec = 0.5 * (abs(distances(b.centre[None], a.normale, a.centre)[0])
                             + abs(distances(a.centre[None], b.normale, b.centre)[0]))
                if dec >= FUSION_DECALAGE or not _voisins(pts, a, b):
                    continue
                fus = _faire_pan(pts, np.concatenate([a.indices, b.indices]))
                pans = [p for k, p in enumerate(pans) if k not in (i, j)] + [fus]
                change = True
                break
            if change:
                break
    return pans
