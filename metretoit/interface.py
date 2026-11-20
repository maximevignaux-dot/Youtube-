#!/usr/bin/env python3
"""Interface de test MétréToit (dans le navigateur).

Lancement : .venv/bin/python interface.py      puis ouvrir http://localhost:5000
"""
from __future__ import annotations

import csv
import io
import json
import os
import sys
import threading
import traceback
from contextlib import redirect_stdout
from pathlib import Path

import numpy as np
import shapely
from flask import Flask, abort, jsonify, request, send_from_directory
from shapely.geometry import shape

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

import test_precision  # noqa: E402
from metretoit import _json, calculer, slug  # noqa: E402
from toiture import donnees  # noqa: E402

app = Flask(__name__, static_folder=None)
VERROU = threading.Lock()      # un calcul à la fois (matplotlib, cache)
RESULTATS = RACINE / "resultats"
CSV_REF = RACINE / "toits_reference.csv"
COLONNES = ["nom", "adresse", "surface_reelle_m2", "pente_reelle_deg", "nb_pans", "debords_inclus",
            "source_mesure", "notes", "x_l93", "y_l93"]


def _repondre(obj, code=200):
    return app.response_class(json.dumps(obj, ensure_ascii=False, default=_json), status=code,
                              mimetype="application/json")


@app.get("/")
def accueil():
    return send_from_directory(RACINE / "interface", "index.html")


@app.get("/static/<path:chemin>")
def fichiers_statiques(chemin):
    return send_from_directory(RACINE / "interface" / "vendor", chemin)


@app.get("/resultats/<path:chemin>")
def fichiers_resultats(chemin):
    return send_from_directory(RESULTATS, chemin)


@app.get("/api/suggestions")
def suggestions():
    q = request.args.get("q", "").strip()
    if len(q) < 3:
        return _repondre([])
    try:
        data = donnees._get_json("https://data.geopf.fr/geocodage/completion",
                                 {"text": q, "type": "StreetAddress", "maximumResponses": 7}, "completion")
    except donnees.ErreurDonnees:
        return _repondre([])
    return _repondre([{"texte": r["fulltext"], "lon": r["x"], "lat": r["y"], "type": r.get("kind")}
                      for r in data.get("results", [])])


@app.post("/api/calcul")
def api_calcul():
    d = request.get_json(force=True)
    adresse = (d.get("adresse") or "").strip() or None
    xy = emprise = None
    if d.get("lon") is not None and d.get("lat") is not None:
        xy = donnees.VERS_L93.transform(float(d["lon"]), float(d["lat"]))
    if d.get("emprise"):
        g = shape(d["emprise"])
        emprise = shapely.transform(g, lambda c: np.c_[donnees.VERS_L93.transform(c[:, 0], c[:, 1])])
        if not emprise.is_valid:
            emprise = emprise.buffer(0)
        if emprise.area < 5:
            return _repondre({"erreur": "Emprise dessinée trop petite."}, 400)
    if not (adresse or xy or emprise is not None):
        return _repondre({"erreur": "Donnez une adresse ou cliquez sur un bâtiment."}, 400)
    if xy is not None:
        nom = slug(f"{adresse or 'point'}-{xy[0]:.0f}-{xy[1]:.0f}")
    else:
        nom = slug(adresse or "emprise")
    if emprise is not None:
        nom += "-emprise-" + str(abs(hash(emprise.wkt)) % 10000)
    journal = io.StringIO()
    try:
        with VERROU, redirect_stdout(journal):
            # si une adresse ET un point sont donnés, le point (clic) l'emporte
            rap = calculer(None if xy is not None else adresse, xy=xy, emprise_fichier=emprise, nom=nom)
    except donnees.ErreurDonnees as e:
        return _repondre({"erreur": str(e), "journal": journal.getvalue()}, 422)
    except Exception as e:  # noqa: BLE001
        traceback.print_exc()
        return _repondre({"erreur": f"Erreur inattendue : {e}", "journal": journal.getvalue()}, 500)
    if adresse and xy is not None:
        rap["adresse_demandee"] = adresse
    rap["image"] = f"/resultats/{nom}/toit.png?v={os.path.getmtime(RESULTATS / nom / 'toit.png'):.0f}"
    rap["json"] = f"/resultats/{nom}/rapport.json"
    rap["nom_dossier"] = nom
    rap["journal"] = journal.getvalue()
    x, y = rap.get("localisation", {}).get("x"), rap.get("localisation", {}).get("y")
    if x is None:
        c = shapely.from_wkt(rap["emprise"]["geometrie_wkt_l93"]).centroid
        x, y = c.x, c.y
    rap["x_l93"], rap["y_l93"] = round(x, 1), round(y, 1)
    return _repondre(rap)


@app.post("/api/zone")
def api_zone():
    """Métré d'une partie du toit : zone dessinée sur un calcul déjà fait."""
    from toiture.partiel import metre_zone
    d = request.get_json(force=True)
    nom = d.get("nom_dossier", "")
    dossier = (RESULTATS / nom).resolve()
    if RESULTATS.resolve() not in dossier.parents or not (dossier / "grille.npz").exists():
        return _repondre({"erreur": "Calcul introuvable : relancez le calcul du toit."}, 404)
    g = shape(d["zone"])
    zone = shapely.transform(g, lambda c: np.c_[donnees.VERS_L93.transform(c[:, 0], c[:, 1])])
    if not zone.is_valid:
        zone = zone.buffer(0)
    return _repondre(metre_zone(dossier, zone))


# ---------- fichier de référence (pour le test de précision) ----------

def _lire_ref():
    if not CSV_REF.exists():
        return []
    with open(CSV_REF, encoding="utf-8-sig", newline="") as f:
        return [l for l in csv.DictReader(f, delimiter=";") if any((v or "").strip() for v in l.values() if v)]


def _ecrire_ref(lignes):
    with open(CSV_REF, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLONNES, delimiter=";", extrasaction="ignore")
        w.writeheader()
        for l in lignes:
            w.writerow({k: (l.get(k) or "") for k in COLONNES})


@app.get("/api/reference")
def ref_liste():
    return _repondre(_lire_ref())


@app.post("/api/reference")
def ref_ajouter():
    d = request.get_json(force=True)
    try:
        float(str(d.get("surface_reelle_m2", "")).replace(",", "."))
    except ValueError:
        return _repondre({"erreur": "Surface réelle manquante ou invalide."}, 400)
    lignes = _lire_ref()
    lignes.append({k: str(d.get(k, "") if d.get(k) is not None else "").replace(";", ",").strip() for k in COLONNES})
    _ecrire_ref(lignes)
    return _repondre({"ok": True, "nb": len(lignes)})


@app.delete("/api/reference/<int:i>")
def ref_supprimer(i):
    lignes = _lire_ref()
    if not 0 <= i < len(lignes):
        abort(404)
    del lignes[i]
    _ecrire_ref(lignes)
    return _repondre({"ok": True, "nb": len(lignes)})


@app.post("/api/test_precision")
def lancer_test():
    journal = io.StringIO()
    try:
        with VERROU, redirect_stdout(journal):
            sys.argv = ["test_precision.py", str(CSV_REF)]
            test_precision.main()
    except Exception as e:  # noqa: BLE001
        return _repondre({"erreur": str(e), "journal": journal.getvalue()}, 500)
    md = RESULTATS / "test_precision.md"
    return _repondre({"journal": journal.getvalue(),
                      "rapport": md.read_text() if md.exists() else ""})


@app.get("/api/historique")
def historique():
    out = []
    for f in sorted(RESULTATS.glob("*/rapport.json"), key=lambda p: -p.stat().st_mtime)[:30]:
        try:
            r = json.loads(f.read_text())
        except ValueError:
            continue
        loc = r.get("localisation", {})
        out.append({"nom": f.parent.name, "adresse": loc.get("adresse_trouvee") or r.get("adresse_demandee") or f.parent.name,
                    "surface_emprise_m2": r.get("surface_emprise_m2"), "surface_nuage_m2": r.get("surface_nuage_m2"),
                    "nb_pans": len(r.get("pans", [])), "lon": loc.get("lon"), "lat": loc.get("lat")})
    return _repondre(out)


@app.get("/api/rapport/<nom>")
def rapport(nom):
    f = RESULTATS / nom / "rapport.json"
    if not f.exists():
        abort(404)
    r = json.loads(f.read_text())
    r["image"] = f"/resultats/{nom}/toit.png?v={f.stat().st_mtime:.0f}"
    r["json"] = f"/resultats/{nom}/rapport.json"
    r["nom_dossier"] = nom
    return _repondre(r)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    print(f"\n  MétréToit — ouvrez http://localhost:{port} dans votre navigateur\n  (Ctrl+C pour arrêter)\n")
    app.run(host=os.environ.get("HOTE", "127.0.0.1"), port=port, debug=False, threaded=True)
