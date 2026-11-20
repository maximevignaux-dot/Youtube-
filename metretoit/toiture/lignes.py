"""Mètres linéaires d'une toiture (pour le devis) : égouts, faîtages, rives, arêtiers,
noues, solins, raccords — longueurs réelles en 3D (le long de la pente quand la ligne
est inclinée).

Principe :
- entre deux pans voisins, la ligne commune est l'intersection des deux plans :
  horizontale et en haut des deux pans = faîtage ; inclinée et en haut des deux = arêtier ;
  en bas des deux = noue ; sinon = raccord (changement de pente) ;
  si les deux pans ne se touchent pas en hauteur (marche > 30 cm), le pan du dessous
  bute contre un mur = solin ;
- sur le pourtour : bord horizontal en bas du pan = égout ; en haut = haut de pan
  (solin ou faîtage d'appentis) ; bord dans le sens de la pente = rive.
"""
from __future__ import annotations

import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import linemerge

from .export import _contour_cellules

TYPES = ["égout", "faîtage", "rive", "arêtier", "noue", "solin", "haut de pan", "raccord", "bord de toit plat"]
MARCHE = 0.30          # m : au-delà, deux pans voisins ne se touchent pas (mur entre les deux)
LONGUEUR_MIN = 0.4     # m : on ignore les bouts de lignes plus courts


def _z(pan, x, y):
    nx, ny, nz = pan.normale
    cx, cy, cz = pan.centre
    return cz - (nx * (x - cx) + ny * (y - cy)) / nz


def _descente(pan):
    v = np.array(pan.normale[:2], float)
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else None


def _morceaux(geom):
    """Lignes contenues dans une géométrie quelconque, fusionnées bout à bout."""
    lignes = [g for g in getattr(geom, "geoms", [geom]) if g.geom_type in ("LineString", "MultiLineString")]
    if not lignes:
        return []
    m = linemerge(shapely.union_all(lignes)) if len(lignes) > 1 or lignes[0].geom_type == "MultiLineString" else lignes[0]
    return [g for g in getattr(m, "geoms", [m]) if g.length > 0]


def _cote_du_pan(poly, m, u):
    """>0 si le pan s'étend dans le sens de la descente u à partir du point m
    (la ligne est alors en HAUT du pan)."""
    morceau = poly.intersection(Point(m).buffer(1.2))
    if morceau.is_empty:
        return 0.0
    c = np.array(morceau.centroid.coords[0])
    return float((c - np.asarray(m)) @ u)


def _long3d(seg_xy, pan):
    """Longueur réelle d'un segment posé sur le plan du pan."""
    s = np.asarray(seg_xy[1]) - np.asarray(seg_xy[0])
    u = _descente(pan)
    dz = 0.0 if u is None else np.tan(np.radians(pan.pente_deg)) * float(s @ u)
    return float(np.hypot(np.linalg.norm(s), dz))


def _intervalles(pts, direction, ecart_max=0.5, origine=None):
    """Projette des points sur une direction et renvoie les intervalles couverts
    (morceaux séparés de moins de ecart_max recollés)."""
    o = pts.mean(0) if origine is None else origine
    t = np.sort((pts - o) @ direction)
    if len(t) == 0:
        return []
    out, deb, fin = [], t[0], t[0]
    for v in t[1:]:
        if v - fin > ecart_max:
            out.append((float(deb), float(fin)))
            deb = v
        fin = v
    out.append((float(deb), float(fin)))
    return out


def _prolonger(seg, d2, bord, maxi=0.75):
    """Une ligne entre deux pans (arêtier, noue, faîtage) qui s'arrête à quelques
    centimètres du bord du toit est prolongée jusqu'au bord."""
    seg = seg.copy()
    for i, sens in ((0, -1), (1, 1)):
        rayon = LineString([seg[i], seg[i] + sens * d2 * maxi])
        x = rayon.intersection(bord)
        if not x.is_empty:
            pts = np.array([q.coords[0] for q in getattr(x, "geoms", [x]) if q.geom_type == "Point"])
            if len(pts):
                seg[i] = pts[np.argmin(np.linalg.norm(pts - seg[i], axis=1))]
    return seg


def _segment_axe(pts, direction):
    o = pts.mean(0)
    t = (pts - o) @ direction
    return np.array([o + direction * t.min(), o + direction * t.max()])


def calculer_lignes(res: dict) -> list[dict]:
    g = res.get("grille_emprise")
    pans_obj = res.get("objets_pans") or []
    infos = res.get("pans") or []
    if g is None or not pans_obj:
        return []
    polys = [_contour_cellules(g, g.etiquettes == k, 0) for k in range(len(pans_obj))]
    lignes = []
    tol = g.cellule * 0.3
    communs = [[] for _ in pans_obj]      # lignes partagées (à retirer du pourtour)
    solins = [[] for _ in pans_obj]       # lignes où ce pan bute contre un mur plus haut

    bord_emprise = res["emprise_locale"].boundary
    arbre = shapely.STRtree(polys)
    for a, pa in enumerate(polys):
        if pa.is_empty:
            continue
        for b in arbre.query(pa):
            b = int(b)
            if b <= a or polys[b].is_empty:
                continue
            commun = pa.intersection(polys[b])
            pieces = _morceaux(commun)
            if not pieces:
                continue
            communs[a] += pieces
            communs[b] += pieces
            A, B = pans_obj[a], pans_obj[b]
            # 1) Morceaux où les deux pans ne se touchent pas en hauteur (marche > 30 cm) :
            #    le pan du dessous bute contre un mur (solin) ; le pan du dessus garde son
            #    bord (égout ou rive). On suit alors la ligne réelle, segment par segment.
            pts_joint = []
            for piece in pieces:
                c = np.asarray(piece.simplify(0.3).coords)[:, :2]
                for i in range(len(c) - 1):
                    s0, s1 = c[i], c[i + 1]
                    l2 = float(np.linalg.norm(s1 - s0))
                    if l2 < 1e-6:
                        continue
                    m = (s0 + s1) / 2
                    za, zb = _z(A, *m), _z(B, *m)
                    if abs(za - zb) <= MARCHE:
                        pts_joint.append(np.asarray(shapely.segmentize(LineString([s0, s1]), 0.1).coords)[:, :2])
                        continue
                    if l2 < 0.05:
                        continue
                    seg = np.array([s0, s1])
                    bas, haut = (a, b) if za < zb else (b, a)
                    solins[bas].append(LineString(seg))
                    lignes.append({"type": "solin", "longueur_m": round(_long3d(seg, pans_obj[bas]), 2),
                                   "longueur_plan_m": round(l2, 2), "pans": [infos[bas]["numero"]],
                                   "coords": seg.round(3).tolist()})
                    P, u = pans_obj[haut], _descente(pans_obj[haut])
                    ds = (s1 - s0) / l2
                    if P.plat or u is None:
                        typ = "bord de toit plat"
                    elif abs(ds @ u) < np.sin(np.radians(30)):
                        typ = "haut de pan" if _cote_du_pan(polys[haut], m, u) > 0 else "égout"
                    else:
                        typ = "rive"
                    lignes.append({"type": typ, "longueur_m": round(_long3d(seg, P) if typ == "rive" else l2, 2),
                                   "longueur_plan_m": round(l2, 2), "pans": [infos[haut]["numero"]],
                                   "coords": seg.round(3).tolist()})
            if not pts_joint:
                continue
            # 2) Morceaux où les pans se rejoignent : la ligne est l'intersection des deux plans.
            pts = np.concatenate(pts_joint)
            d = np.cross(A.normale, B.normale)
            if np.linalg.norm(d) < np.sin(np.radians(3)):
                _, _, vt = np.linalg.svd(pts - pts.mean(0), full_matrices=False)
                d2, pente_ligne = vt[0], 0.0
            else:
                d = d / np.linalg.norm(d)
                h = np.hypot(d[0], d[1])
                d2 = d[:2] / h if h > 1e-9 else np.array([1.0, 0.0])
                pente_ligne = abs(d[2]) / max(h, 1e-9)
            # Vue sur la grille, une ligne en diagonale est un escalier, parfois coupé en
            # morceaux : on mesure sa longueur le long de la vraie direction (intersection
            # des deux plans), en recollant les morceaux séparés de moins de 0,5 m.
            for (t0, t1) in _intervalles(pts, d2, ecart_max=0.5):
                l2 = t1 - t0
                if l2 < LONGUEUR_MIN:
                    continue
                t = (pts - pts.mean(0)) @ d2
                sel = pts[(t >= t0 - 1e-6) & (t <= t1 + 1e-6)]
                m = sel.mean(0)
                seg = _prolonger(_segment_axe(sel, d2), d2, bord_emprise)
                l2 = float(np.linalg.norm(seg[1] - seg[0]))
                ua, ub = _descente(A), _descente(B)
                if ua is None or ub is None:
                    typ = "raccord"
                else:
                    haut_a = _cote_du_pan(pa, m, ua) > 0
                    haut_b = _cote_du_pan(polys[b], m, ub) > 0
                    if haut_a and haut_b:
                        typ = "faîtage" if pente_ligne < np.tan(np.radians(10)) else "arêtier"
                    elif not haut_a and not haut_b:
                        typ = "noue"
                    else:
                        typ = "raccord"
                lignes.append({"type": typ, "longueur_m": round(l2 * float(np.hypot(1.0, pente_ligne)), 2),
                               "longueur_plan_m": round(l2, 2),
                               "pans": [infos[a]["numero"], infos[b]["numero"]],
                               "coords": seg.round(3).tolist()})

    # pourtour de chaque pan
    sur_cotes = []
    emp = res["emprise_locale"]
    cotes = []
    for p in getattr(emp, "geoms", [emp]):
        for r in [p.exterior, *p.interiors]:
            c = np.asarray(r.simplify(0.05).coords)[:, :2]
            cotes += [(c[i], c[i + 1]) for i in range(len(c) - 1) if np.linalg.norm(c[i + 1] - c[i]) > 0.05]
    for k, (poly, pan) in enumerate(zip(polys, pans_obj)):
        if poly.is_empty:
            continue
        exterieurs = [LineString(p.exterior.coords) for p in getattr(poly, "geoms", [poly])]
        bord = shapely.union_all(exterieurs)
        if communs[k]:
            bord = bord.difference(shapely.union_all(communs[k]).buffer(tol))
        zone_solin = shapely.union_all(solins[k]).buffer(tol * 2) if solins[k] else None
        u = _descente(pan)
        # 1) parties du pourtour posées sur un côté droit de l'emprise : on prend la
        #    direction exacte de ce côté (pas l'escalier de la grille)
        for ic, (c0, c1) in enumerate(cotes):
            e = c1 - c0
            le = float(np.linalg.norm(e))
            dir_e = e / le
            sur = bord.intersection(LineString([c0, c1]).buffer(g.cellule * 0.75, cap_style="flat"))
            pts_e = [np.asarray(shapely.segmentize(p, 0.1).coords)[:, :2] for p in _morceaux(sur)]
            if not pts_e:
                continue
            pts_e = np.concatenate(pts_e)
            for (t0, t1) in _intervalles(pts_e, dir_e, ecart_max=0.3, origine=c0):
                t0, t1 = max(t0, 0.0), min(t1, le)
                if t1 - t0 < 0.05:
                    continue
                seg = np.array([c0 + dir_e * t0, c0 + dir_e * t1])
                m = seg.mean(0)
                if pan.plat or u is None:
                    typ = "bord de toit plat"
                elif abs(dir_e @ u) < np.sin(np.radians(30)):
                    typ = "haut de pan" if _cote_du_pan(poly, m, u) > 0 else "égout"
                else:
                    typ = "rive"
                sur_cotes.append({"cote": ic, "k": k, "seg": seg, "typ": typ, "l2": t1 - t0})
        if cotes:
            bord = bord.difference(shapely.union_all([LineString([c0, c1]) for c0, c1 in cotes]).buffer(g.cellule * 0.75, cap_style="flat"))
        # 2) le reste (bord le long d'une zone non mesurée, contre un mur…)
        for piece in _morceaux(bord):
            if piece.length < 0.3:
                continue
            c = np.asarray(piece.simplify(0.2).coords)
            for i in range(len(c) - 1):
                s = c[i + 1] - c[i]
                l2 = float(np.linalg.norm(s))
                if l2 < 1e-6:
                    continue
                m = (c[i] + c[i + 1]) / 2
                if pan.plat or u is None:
                    typ = "bord de toit plat"
                elif zone_solin is not None and zone_solin.contains(LineString([c[i], c[i + 1]])):
                    typ = "solin"
                elif abs(s @ u) / l2 < np.sin(np.radians(30)):      # bord horizontal
                    typ = "haut de pan" if _cote_du_pan(poly, m, u) > 0 else "égout"
                else:
                    typ = "rive"
                lignes.append({"type": typ, "longueur_m": round(_long3d((c[i], c[i + 1]), pan), 2),
                               "longueur_plan_m": round(l2, 2), "pans": [infos[k]["numero"]],
                               "coords": [c[i].round(3).tolist(), c[i + 1].round(3).tolist()]})
    # Un côté droit du bâtiment a un seul rôle (égout, rive…) : celui qui est majoritaire
    # sur sa longueur. Évite qu'un bout d'égout pris par le pan voisin, dans un angle,
    # soit compté comme rive.
    for ic in {p["cote"] for p in sur_cotes}:
        ps = [p for p in sur_cotes if p["cote"] == ic]
        poids = {}
        for p in ps:
            if p["typ"] != "bord de toit plat":
                poids[p["typ"]] = poids.get(p["typ"], 0.0) + p["l2"]
        majo = max(poids, key=poids.get) if poids else None
        for p in ps:
            typ = p["typ"] if p["typ"] == "bord de toit plat" or majo is None else majo
            pan = pans_obj[p["k"]]
            l3 = _long3d(p["seg"], pan) if typ == "rive" else p["l2"]
            lignes.append({"type": typ, "longueur_m": round(l3, 2), "longueur_plan_m": round(p["l2"], 2),
                           "pans": [infos[p["k"]]["numero"]], "coords": p["seg"].round(3).tolist()})
    return [l for l in lignes if l["longueur_m"] > 0.05]


def totaux(lignes: list[dict], pans: set | None = None) -> dict:
    """Mètres linéaires par type (option : seulement les lignes touchant ces pans)."""
    t = {}
    for l in lignes:
        if pans is not None and not set(l["pans"]) & pans:
            continue
        t[l["type"]] = t.get(l["type"], 0.0) + l["longueur_m"]
    return {k: round(t[k], 2) for k in TYPES if k in t}
