#!/usr/bin/env python3
"""Test de précision de MétréToit sur des toits dont on connaît les vraies mesures.

Usage : python test_precision.py toits_reference.csv

CSV (séparateur « ; ») :
  nom;adresse;surface_reelle_m2;pente_reelle_deg;nb_pans;debords_inclus;source_mesure;notes
Colonnes facultatives en plus : x_l93;y_l93 (pour forcer la position si le géocodage tombe à côté).

Verdict GO si l'écart de surface est < 5 % sur au moins 8 toits sur 10 (80 %).
"""
from __future__ import annotations

import csv
import json
import sys
import traceback
from pathlib import Path

RACINE = Path(__file__).resolve().parent
sys.path.insert(0, str(RACINE))

from metretoit import calculer, slug  # noqa: E402

SEUIL_ECART = 5.0      # %
PART_GO = 0.8          # 8 toits sur 10


def _nombre(v):
    v = (v or "").strip().replace(",", ".").replace(" ", "")
    return float(v) if v else None


def lire_csv(fichier):
    with open(fichier, encoding="utf-8-sig", newline="") as f:
        lignes = [l for l in csv.DictReader(f, delimiter=";") if any((v or "").strip() for v in l.values())]
    out = []
    for l in lignes:
        l = {k.strip(): (v or "").strip() for k, v in l.items() if k}
        out.append({
            "nom": l.get("nom") or l.get("adresse"),
            "adresse": l.get("adresse"),
            "surface_reelle_m2": _nombre(l.get("surface_reelle_m2")),
            "pente_reelle_deg": _nombre(l.get("pente_reelle_deg")),
            "nb_pans": int(_nombre(l.get("nb_pans"))) if _nombre(l.get("nb_pans")) is not None else None,
            "debords_inclus": l.get("debords_inclus", "").lower().startswith("o"),
            "source_mesure": l.get("source_mesure", ""),
            "notes": l.get("notes", ""),
            "xy": (_nombre(l.get("x_l93")), _nombre(l.get("y_l93"))) if l.get("x_l93") and l.get("y_l93") else None,
        })
    return out


def pente_principale(rapport):
    """Pente du plus grand pan incliné (sinon du plus grand pan)."""
    pans = sorted(rapport["pans"], key=lambda p: -p["surface_reelle_m2"])
    inclines = [p for p in pans if p["type"] != "toit plat"]
    return (inclines or pans or [{"pente_deg": None}])[0]["pente_deg"]


def causes_probables(ref, rap, ecart):
    c = []
    loc = rap.get("localisation", {})
    if loc.get("score") is not None and loc["score"] < 0.7:
        c.append(f"adresse peut-être mal géocodée (score {loc['score']:.2f} → « {loc.get('adresse_trouvee')} »)")
    if rap.get("emprise", {}).get("distance_au_point_m", 0) > 0:
        c.append(f"le point de l'adresse n'est dans aucun bâtiment (bâtiment pris à {rap['emprise']['distance_au_point_m']} m)")
    if abs(ecart) > 25:
        c.append("écart énorme : probablement le mauvais bâtiment, ou bâtiment groupé (mitoyen, dépendances) dans l'emprise BD TOPO")
    se, sn = rap["surface_emprise_m2"], rap["surface_nuage_m2"]
    if se and abs(sn - se) / se > 0.06:
        c.append(f"débords : surfaces emprise ({se:.0f} m²) et nuage ({sn:.0f} m²) très différentes")
    if rap.get("non_mesure_pct", 0) > 5:
        c.append(f"{rap['non_mesure_pct']:.0f} % de l'emprise sans point de toit : végétation, ombre ou toit en verrière")
    ecarts_pans = [p["ecart_moyen_cm"] for p in rap["pans"]]
    if ecarts_pans and max(ecarts_pans) > 5:
        c.append("points dispersés autour des plans (> 5 cm) : végétation sur le toit ou toit courbe/irrégulier")
    if ref["nb_pans"] is not None and ref["nb_pans"] != len(rap["pans"]):
        c.append(f"toit complexe : {len(rap['pans'])} pans détectés au lieu de {ref['nb_pans']}")
    if any(m in ref["notes"].lower() for m in ("travaux", "extension", "véranda", "veranda", "agrandi", "rénov", "renov", "neuf")):
        c.append(f"toit peut-être modifié depuis le relevé LiDAR du {rap['lidar']['date_releve']} (voir notes)")
    return c or ["cause non identifiée automatiquement : comparer toit.png avec une vue aérienne"]


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    refs = lire_csv(sys.argv[1])
    dossier = RACINE / "resultats"
    dossier.mkdir(exist_ok=True)
    md = dossier / "test_precision.md"
    if not refs:
        md.write_text("# Test de précision MétréToit\n\nLe fichier de référence ne contient aucun toit. "
                      "Remplissez `toits_reference.csv` puis relancez :\n\n"
                      "    python test_precision.py toits_reference.csv\n")
        print("Le fichier de référence ne contient aucun toit : remplissez-le puis relancez.")
        return

    lignes = []
    for i, ref in enumerate(refs, 1):
        print(f"\n=== [{i}/{len(refs)}] {ref['nom']} — {ref['adresse']} ===")
        nom = f"{i:02d}-{slug(ref['nom'])}"
        try:
            rap = calculer(ref["adresse"], xy=ref["xy"], nom=nom, bavard=False)
        except Exception as e:  # noqa: BLE001
            traceback.print_exc()
            lignes.append({"ref": ref, "nom_dossier": nom, "erreur": str(e)})
            print(f"  ÉCHEC : {e}")
            continue
        variante = "nuage" if ref["debords_inclus"] else "emprise"
        s_calc = rap["surface_nuage_m2"] if ref["debords_inclus"] else rap["surface_emprise_m2"]
        s_autre = rap["surface_emprise_m2"] if ref["debords_inclus"] else rap["surface_nuage_m2"]
        ecart = 100 * (s_calc - ref["surface_reelle_m2"]) / ref["surface_reelle_m2"] if ref["surface_reelle_m2"] else None
        ecart_autre = 100 * (s_autre - ref["surface_reelle_m2"]) / ref["surface_reelle_m2"] if ref["surface_reelle_m2"] else None
        pente = pente_principale(rap)
        l = {"ref": ref, "nom_dossier": nom, "rapport": rap, "variante": variante, "surface_calculee": s_calc,
             "ecart_pct": ecart, "ecart_autre_variante_pct": ecart_autre, "pente_calculee": pente,
             "ecart_pente": (pente - ref["pente_reelle_deg"]) if (pente is not None and ref["pente_reelle_deg"] is not None) else None,
             "nb_pans_calcule": len(rap["pans"])}
        l["ok"] = ecart is not None and abs(ecart) < SEUIL_ECART
        if not l["ok"]:
            l["causes"] = causes_probables(ref, rap, ecart or 0)
        lignes.append(l)
        print(f"  surface {variante} : {s_calc:.1f} m² (réel {ref['surface_reelle_m2']} m²) → écart {ecart:+.1f} %"
              f" | pente {pente}° | {len(rap['pans'])} pans")

    ecrire_rapport(lignes, md)
    (dossier / "test_precision.json").write_text(json.dumps(
        [{k: v for k, v in l.items() if k != "rapport"} for l in lignes], ensure_ascii=False, indent=2, default=str))
    print(f"\nRapport : {md}")


def _f(v, fmt="{:.1f}", vide="—"):
    return vide if v is None else fmt.format(v)


def ecrire_rapport(lignes, md: Path):
    n = len(lignes)
    n_ok = sum(1 for l in lignes if l.get("ok"))
    besoin = int(-(-PART_GO * n // 1))   # arrondi supérieur : 8 sur 10
    go = n_ok >= besoin
    t = ["# Test de précision MétréToit", ""]
    t.append(f"**Verdict : {'GO ✅' if go else 'NO-GO ❌'}** — écart de surface < {SEUIL_ECART:.0f} % "
             f"sur **{n_ok} toit(s) sur {n}** (il en faut au moins {besoin}).")
    if n != 10:
        t.append(f"\n> Attention : le protocole prévoit 10 toits, le fichier en contient {n}. Verdict à confirmer.")
    t += ["", "## Tableau toit par toit", "",
          "| # | Toit | Surface réelle (m²) | Débords | Variante | Surface calculée (m²) | Écart | Autre variante | "
          "Pente réelle | Pente calculée | Pans réels | Pans calculés | Relevé LiDAR | OK |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for i, l in enumerate(lignes, 1):
        r = l["ref"]
        if "erreur" in l:
            t.append(f"| {i} | {r['nom']} | {_f(r['surface_reelle_m2'])} | {'oui' if r['debords_inclus'] else 'non'} | "
                     f"— | ÉCHEC | — | — | {_f(r['pente_reelle_deg'])} | — | {_f(r['nb_pans'], '{}')} | — | — | ❌ |")
            continue
        t.append(f"| {i} | {r['nom']} | {_f(r['surface_reelle_m2'])} | {'oui' if r['debords_inclus'] else 'non'} | "
                 f"{l['variante']} | {_f(l['surface_calculee'])} | **{_f(l['ecart_pct'], '{:+.1f} %')}** | "
                 f"{_f(l['ecart_autre_variante_pct'], '{:+.1f} %')} | {_f(r['pente_reelle_deg'], '{:.0f}°')} | "
                 f"{_f(l['pente_calculee'], '{:.1f}°')} | {_f(r['nb_pans'], '{}')} | {l['nb_pans_calcule']} | "
                 f"{l['rapport']['lidar']['date_releve']} | {'✅' if l['ok'] else '❌'} |")
    t += ["", "« Variante » : *nuage* si les débords sont inclus dans la mesure de référence, *emprise* sinon. "
          "« Autre variante » : l'écart qu'aurait donné l'autre méthode.", ""]

    ecarts = [abs(l["ecart_pct"]) for l in lignes if l.get("ecart_pct") is not None]
    if ecarts:
        ecarts.sort()
        t.append(f"Écart absolu médian : {ecarts[len(ecarts) // 2]:.1f} % — maximum : {max(ecarts):.1f} %.")
    pentes = [abs(l["ecart_pente"]) for l in lignes if l.get("ecart_pente") is not None]
    if pentes:
        t.append(f"Écart de pente moyen : {sum(pentes) / len(pentes):.1f}° sur {len(pentes)} toit(s).")
    t.append("")

    rates = [l for l in lignes if not l.get("ok")]
    t += ["## Analyse des écarts", ""]
    if not rates:
        t.append("Tous les toits sont à moins de 5 %.")
    for l in rates:
        r = l["ref"]
        t.append(f"### {r['nom']}")
        if "erreur" in l:
            t.append(f"- Le calcul a échoué : `{l['erreur']}`")
        else:
            for c in l["causes"]:
                t.append(f"- {c}")
        t.append("")
    if not go:
        t += ["**Pistes** : vérifier l'emprise retenue sur toit.png (bon bâtiment ?), corriger avec `--xy` ou "
              "`--emprise`, comparer la date du relevé LiDAR à la date des travaux, et vérifier si la mesure de "
              "référence inclut les débords.", ""]

    t += ["## Images", ""]
    for l in lignes:
        if "erreur" in l:
            continue
        rel = Path(l["rapport"]["dossier"]).relative_to(md.parent) / "toit.png"
        t += [f"### {l['ref']['nom']} — écart {_f(l['ecart_pct'], '{:+.1f} %')}", "", f"![{l['ref']['nom']}]({rel.as_posix()})", ""]
    md.write_text("\n".join(t))
    print(f"\nVERDICT : {'GO' if go else 'NO-GO'} ({n_ok}/{n} toits à moins de {SEUIL_ECART:.0f} %)")


if __name__ == "__main__":
    main()
