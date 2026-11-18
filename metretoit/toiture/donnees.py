"""Accès aux données de la Géoplateforme IGN (géocodage, BD TOPO, LiDAR HD).

Tout est mis en cache dans cache/ pour ne pas retélécharger à chaque essai.
Les dalles LiDAR ne sont JAMAIS téléchargées entières : on lit seulement la zone
du bâtiment dans le fichier COPC (requêtes HTTP Range).
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path

import numpy as np
import requests
import shapely
from pyproj import Transformer
from shapely.geometry import Point, shape

RACINE = Path(__file__).resolve().parents[1]
CACHE = RACINE / "cache"
GEOCODAGE = "https://data.geopf.fr/geocodage/search"
WFS = "https://data.geopf.fr/wfs/ows"
COUCHE_BATI = "BDTOPO_V3:batiment"
COUCHE_DALLES = "IGNF_LIDAR-HD_METADONNEE:metadata"   # attribut url_npl = fichier .copc.laz
VERS_L93 = Transformer.from_crs("EPSG:4326", "EPSG:2154", always_xy=True)
VERS_WGS84 = Transformer.from_crs("EPSG:2154", "EPSG:4326", always_xy=True)
SESSION = requests.Session()
SESSION.headers["User-Agent"] = "metretoit-prototype/0.1"


class ErreurDonnees(RuntimeError):
    pass


def _cle(*parts) -> str:
    return hashlib.sha1("|".join(map(str, parts)).encode()).hexdigest()[:16]


def _get_json(url, params, sous_dossier):
    f = CACHE / sous_dossier / f"{_cle(url, sorted(params.items()))}.json"
    if f.exists():
        return json.loads(f.read_text())
    for essai in range(3):
        try:
            r = SESSION.get(url, params=params, timeout=60)
            r.raise_for_status()
            data = r.json()
            break
        except (requests.RequestException, ValueError) as e:
            if essai == 2:
                raise ErreurDonnees(f"Échec de la requête {url} : {e}") from e
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(json.dumps(data))
    return data


# ---------------- Étape 1 : géocodage ----------------

def geocoder(adresse: str) -> dict:
    data = _get_json(GEOCODAGE, {"q": adresse, "limit": 1}, "geocodage")
    if not data.get("features"):
        raise ErreurDonnees(f"Adresse introuvable : {adresse}")
    f = data["features"][0]
    lon, lat = f["geometry"]["coordinates"]
    x, y = VERS_L93.transform(lon, lat)
    p = f["properties"]
    return {"adresse_trouvee": p.get("label"), "score": p.get("score"), "type": p.get("type"),
            "lon": lon, "lat": lat, "x": x, "y": y}


# ---------------- Étape 2 : emprise du bâtiment ----------------

def _wfs(couche, xmin, ymin, xmax, ymax, sous_dossier, nb=500):
    params = {"SERVICE": "WFS", "VERSION": "2.0.0", "REQUEST": "GetFeature", "TYPENAMES": couche,
              "OUTPUTFORMAT": "application/json", "SRSNAME": "EPSG:2154", "COUNT": nb,
              "BBOX": f"{xmin:.2f},{ymin:.2f},{xmax:.2f},{ymax:.2f},EPSG:2154"}
    return _get_json(WFS, params, sous_dossier).get("features", [])


def batiments_autour(x, y, rayon=60.0):
    feats = _wfs(COUCHE_BATI, x - rayon, y - rayon, x + rayon, y + rayon, "bdtopo")
    out = []
    for f in feats:
        g = shape(f["geometry"])
        g = shapely.force_2d(g)
        if not g.is_valid:
            g = g.buffer(0)
        out.append((g, f.get("properties", {})))
    return out


def choisir_batiment(x, y, batiments, dist_max=15.0):
    """Le bâtiment qui contient le point, sinon le plus proche à moins de 15 m."""
    p = Point(x, y)
    if not batiments:
        raise ErreurDonnees("Aucun bâtiment BD TOPO à proximité.")
    contient = [b for b in batiments if b[0].contains(p)]
    if contient:
        g, props = min(contient, key=lambda b: b[0].area)
        return g, props, 0.0
    d = [b[0].distance(p) for b in batiments]
    i = int(np.argmin(d))
    if d[i] > dist_max:
        raise ErreurDonnees(f"Aucun bâtiment à moins de {dist_max:.0f} m (le plus proche : {d[i]:.0f} m). "
                            "Utilisez --xy ou --emprise.")
    return batiments[i][0], batiments[i][1], float(d[i])


def lire_emprise(fichier) -> shapely.Geometry:
    data = json.loads(Path(fichier).read_text())
    if data.get("type") == "FeatureCollection":
        geoms = [shape(f["geometry"]) for f in data["features"]]
    elif data.get("type") == "Feature":
        geoms = [shape(data["geometry"])]
    else:
        geoms = [shape(data)]
    g = shapely.force_2d(shapely.union_all(geoms))
    x0 = g.bounds[0]
    if abs(x0) <= 180:   # coordonnées en degrés (WGS84) -> Lambert-93
        g = shapely.transform(g, lambda c: np.c_[VERS_L93.transform(c[:, 0], c[:, 1])])
    return g


# ---------------- Étape 3 : nuage de points LiDAR HD ----------------

def dalles_lidar(xmin, ymin, xmax, ymax):
    feats = _wfs(COUCHE_DALLES, xmin, ymin, xmax, ymax, "dalles")
    par_dalle = {}
    for f in feats:
        p = f["properties"]
        if not p.get("url_npl"):
            continue
        k = p.get("coordonnees_nw") or p["url_npl"]
        if k not in par_dalle or (p.get("date_edition") or "") > (par_dalle[k].get("date_edition") or ""):
            par_dalle[k] = p
    if not par_dalle:
        raise ErreurDonnees("Aucune dalle LiDAR HD ne couvre ce bâtiment (zone pas encore diffusée ?). "
                            "Vous pouvez fournir un fichier avec --laz.")
    return list(par_dalle.values())


def _lire_copc(source, xmin, ymin, xmax, ymax):
    import laspy
    from laspy.copc import Bounds
    with laspy.CopcReader.open(str(source)) as r:
        pts = r.query(Bounds(mins=np.array([xmin, ymin]), maxs=np.array([xmax, ymax])))
        hdr = r.header
    x, y, z = np.asarray(pts.x), np.asarray(pts.y), np.asarray(pts.z)
    cls = np.asarray(pts.classification)
    t = np.asarray(pts.gps_time) if "gps_time" in pts.point_format.dimension_names else np.array([])
    m = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax)
    return np.c_[x[m], y[m], z[m]], cls[m], (t[m] if len(t) else t), hdr


def _lire_las_local(chemin, xmin, ymin, xmax, ymax):
    import laspy
    try:
        return _lire_copc(chemin, xmin, ymin, xmax, ymax)
    except Exception:
        pass
    las = laspy.read(str(chemin))
    x, y, z = np.asarray(las.x), np.asarray(las.y), np.asarray(las.z)
    m = (x >= xmin) & (x <= xmax) & (y >= ymin) & (y <= ymax)
    t = np.asarray(las.gps_time)[m] if "gps_time" in las.point_format.dimension_names else np.array([])
    return np.c_[x[m], y[m], z[m]], np.asarray(las.classification)[m], t, las.header


def _date_gps(t):
    """Temps GPS « ajusté » (standard LAS 1.4) -> date du relevé."""
    if len(t) == 0:
        return None
    s = float(np.median(t)) + 1e9
    return (dt.datetime(1980, 1, 6) + dt.timedelta(seconds=s)).date().isoformat()


def points_lidar(emprise, marge=2.0, fichiers_laz=None):
    """Points LiDAR autour de l'emprise (+ marge). Renvoie (xyz, classes, infos)."""
    xmin, ymin, xmax, ymax = emprise.bounds
    xmin, ymin, xmax, ymax = xmin - marge, ymin - marge, xmax + marge, ymax + marge
    blocs, infos = [], {"sources": []}
    if fichiers_laz:
        for f in fichiers_laz:
            xyz, cls, t, hdr = _lire_las_local(f, xmin, ymin, xmax, ymax)
            blocs.append((xyz, cls))
            infos["sources"].append({"fichier": str(f), "date_releve": _date_gps(t),
                                     "date_creation_fichier": str(getattr(hdr, "creation_date", ""))})
    else:
        for d in dalles_lidar(xmin, ymin, xmax, ymax):
            url = d["url_npl"]
            f = CACHE / "lidar" / f"{_cle(url, round(xmin, 1), round(ymin, 1), round(xmax, 1), round(ymax, 1))}.npz"
            if f.exists():
                z = np.load(f)
                xyz, cls, t = z["xyz"], z["cls"], z["t"]
            else:
                try:
                    xyz, cls, t, _ = _lire_copc(url, xmin, ymin, xmax, ymax)
                except Exception as e:
                    raise ErreurDonnees(f"Lecture LiDAR impossible ({url}) : {e}. "
                                        "Téléchargez la dalle à la main et utilisez --laz.") from e
                f.parent.mkdir(parents=True, exist_ok=True)
                np.savez_compressed(f, xyz=xyz, cls=cls, t=t)
            blocs.append((xyz, cls))
            infos["sources"].append({
                "dalle": d.get("coordonnees_nw"), "url": url,
                "date_releve": (d.get("date_debut_acquisition") or "").rstrip("Z"),
                "date_fin_releve": (d.get("date_fin_acquisition") or "").rstrip("Z"),
                "date_releve_points": _date_gps(t),
                "date_edition": (d.get("date_edition") or "").rstrip("Z"),
                "mission": d.get("code_mission"), "classement": d.get("procede_classement"),
            })
    xyz = np.concatenate([b[0] for b in blocs]) if blocs else np.zeros((0, 3))
    cls = np.concatenate([b[1] for b in blocs]) if blocs else np.zeros(0, int)
    dates = sorted({s.get("date_releve") or s.get("date_releve_points") for s in infos["sources"]} - {None, ""})
    infos["date_releve"] = " / ".join(dates) if dates else "inconnue"
    infos["nb_dalles"] = len(blocs)
    return xyz, cls, infos
