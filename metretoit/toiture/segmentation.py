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


ECHANTILLON_MAX = 20000      # points utilisés pour noter les plans candidats (grands toits)


def _ransac_meilleur_plan(pts, arbre, rng, seuil, n_essais=600, rayon=2.5):
    """Échantillonnage local : 3 points voisins, on garde le plan avec le plus d'inliers.
    Sur un grand toit, les candidats sont notés sur un échantillon de 20 000 points
    (le nombre d'inliers est extrapolé)."""
    n = len(pts)
    if n > ECHANTILLON_MAX:
        ech = pts[rng.choice(n, ECHANTILLON_MAX, replace=False)]
        facteur = n / ECHANTILLON_MAX
    else:
        ech, facteur = pts, 1.0
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
        d = np.abs(nk @ ech.T - np.einsum("kj,kj->k", nk, pk)[:, None])
        cpt = (d < seuil).sum(axis=1)
        i = int(cpt.argmax())
        if cpt[i] > score:
            score, meilleur = int(cpt[i]), (nrm[k + i], p0[k + i])
    return meilleur, int(score * facteur)


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
    idx = np.concatenate([p.indices for p in pans])
    lab = np.concatenate([np.full(len(p.indices), k) for k, p in enumerate(pans)])
    xy, z = pts[idx, :2], pts[idx, 2]
    d, v = cKDTree(xy).query(xy, k=min(16, len(xy)), distance_upper_bound=rayon)
    ok = np.isfinite(d)
    v = np.where(ok, v, 0)
    autre = ok & (lab[v] != lab[:, None])
    dessous = (autre & (z[v] < z[:, None] - dz)).any(axis=1)
    dessus = (autre & (z[v] > z[:, None] + dz)).any(axis=1)
    n = np.bincount(lab, minlength=len(pans))
    f_dessous = np.bincount(lab, weights=dessous, minlength=len(pans)) / n
    f_dessus = np.bincount(lab, weights=dessus, minlength=len(pans)) / n
    return [p for k, p in enumerate(pans) if f_dessous[k] <= part_max and f_dessus[k] <= part_max]


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
        pp = pts[p.indices, :2]
        mn, mx = pp.min(axis=0) - 1.0, pp.max(axis=0) + 1.0
        zone = np.where((pts[:, 0] >= mn[0]) & (pts[:, 0] <= mx[0]) & (pts[:, 1] >= mn[1]) & (pts[:, 1] <= mx[1]))[0]
        d = np.abs(distances(pts[zone], p.normale, p.centre))
        proche = d < seuil
        zone, d = zone[proche], d[proche]
        dxy, _ = cKDTree(pp).query(pts[zone, :2], distance_upper_bound=1.0)
        zone, d = zone[dxy < np.inf], d[dxy < np.inf]
        compatible[k, zone] = True
        ok = d < best_d[zone]
        best_d[zone[ok]], best_k[zone[ok]] = d[ok], k
    # Lissage : près de la ligne où deux plans se croisent, un point est compatible
    # avec les deux. Il rejoint alors le pan majoritaire parmi ses 10 voisins.
    ambigus = np.where(compatible.sum(axis=0) >= 2)[0]
    if len(pans) > 1 and len(ambigus):
        _, vois = cKDTree(pts[:, :2]).query(pts[ambigus, :2], k=min(11, len(pts)))
        vois = vois[:, 1:]
        for _ in range(3):
            lab_v = best_k[vois]
            actuel = best_k[ambigus]
            autre = np.where(actuel >= 0, (lab_v == actuel[:, None]).sum(axis=1), 0)
            change = 0
            for k in np.unique(np.nonzero(compatible[:, ambigus])[0]):
                votes = (lab_v == k).sum(axis=1)
                bascule = compatible[k, ambigus] & (actuel != k) & (votes > autre) & (votes >= 4)
                if bascule.any():
                    actuel = np.where(bascule, k, actuel)
                    autre = np.where(bascule, votes, autre)
                    change += int(bascule.sum())
            best_k[ambigus] = actuel
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


def _cellules(pts, p: Pan, taille=GRILLE_CONNEXITE):
    return set(map(tuple, np.unique(np.floor(pts[p.indices, :2] / taille).astype(np.int64), axis=0)))


def _sont_voisins(ca: set, cb: set) -> bool:
    """Deux pans sont voisins si des cellules de 0,5 m sont à moins de ~1 m (2 cellules)."""
    if len(ca) > len(cb):
        ca, cb = cb, ca
    for (i, j) in ca:
        for di in range(-2, 3):
            for dj in range(-2, 3):
                if (i + di, j + dj) in cb:
                    return True
    return False


def _fusionner(pts, pans: list[Pan]) -> list[Pan]:
    cos_lim = np.cos(np.radians(FUSION_ANGLE))
    cell = [_cellules(pts, p) for p in pans]
    vivants = list(range(len(pans)))
    pans = list(pans)

    def fusionnables(a, b):
        A, B = pans[a], pans[b]
        if A.normale @ B.normale < cos_lim:
            return False
        dec = 0.5 * (abs(distances(B.centre[None], A.normale, A.centre)[0])
                     + abs(distances(A.centre[None], B.normale, B.centre)[0]))
        return dec < FUSION_DECALAGE and _sont_voisins(cell[a], cell[b])

    change = True
    while change:
        change = False
        for x in range(len(vivants)):
            for y in range(x + 1, len(vivants)):
                a, b = vivants[x], vivants[y]
                if fusionnables(a, b):
                    pans.append(_faire_pan(pts, np.concatenate([pans[a].indices, pans[b].indices])))
                    cell.append(cell[a] | cell[b])
                    vivants = [v for v in vivants if v not in (a, b)] + [len(pans) - 1]
                    change = True
                    break
            if change:
                break
    return [pans[v] for v in vivants]
