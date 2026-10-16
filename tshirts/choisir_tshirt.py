#!/usr/bin/env python3
"""Choisir le t-shirt de base Printful et fixer le prix.

  python3 choisir_tshirt.py                  liste les t-shirts unisexes en coton du catalogue Printful
  python3 choisir_tshirt.py --comparer 71 586 438
                                             prix de revient livré en France + prix de vente calculé, pour chacun
  python3 choisir_tshirt.py --choisir 71     enregistre ce t-shirt dans config_printful.json
                                             (variantes par couleur et taille, guide des tailles, prix validé)
"""
import json, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "outils"))
from printful import COULEURS, TAILLES, ErreurPrintful, appel, prix_vente

ROOT = os.path.dirname(os.path.abspath(__file__))
B = json.load(open(os.path.join(ROOT, "boutique.json"), encoding="utf-8"))


def lister():
    prods = appel("GET", "/products")
    ok = [p for p in prods if p.get("type") == "T-SHIRT" and not p.get("is_discontinued")
          and "unisex" in (p.get("title", "") + p.get("model", "")).lower()]
    print(f"{len(ok)} t-shirts unisexes :")
    for p in ok:
        coton = "100% coton" if "100%" in (p.get("description") or "") and "cotton" in (p.get("description") or "").lower() else ""
        print(f"  {p['id']:>5}  {p.get('brand', '')} {p.get('model', '')} — {p.get('title', '')}  {coton}  "
              f"(fabrication ~{p.get('avg_fulfillment_time', '?')} j)")


def variantes(pid):
    """Variantes du catalogue, triées par nos couleurs et tailles."""
    d = appel("GET", f"/products/{pid}")
    par_couleur = {}
    for v in d["variants"]:
        par_couleur.setdefault(v["color"], {})[v["size"]] = v
    choix = {}
    for nous, noms in COULEURS.items():
        nom = next((n for n in noms if n in par_couleur), None)
        if nom:
            choix[nous] = {"printful": nom, "tailles": {t: par_couleur[nom][t]["id"] for t in TAILLES if t in par_couleur[nom]}}
    return d["product"], choix


def couts(pid, vid):
    """Prix du t-shirt (EUR, hors TVA) et livraison standard vers la France pour 1 article."""
    prix = None
    try:
        r = appel("GET", f"/v2/catalog-variants/{vid}/prices?currency=EUR&selling_region_name=europe")
        tech = (r.get("data") or r).get("variant", {}).get("techniques", [])
        prix = float(next(t for t in tech if t.get("technique_key") == "dtg")["price"])
    except (ErreurPrintful, StopIteration, KeyError, TypeError, ValueError):
        pass
    liv = appel("POST", "/shipping/rates", json={"recipient": {"country_code": "FR", "zip": "75001"},
                                                  "items": [{"variant_id": vid, "quantity": 1}], "currency": "EUR"})
    std = next((x for x in liv if x["id"] == "STANDARD"), liv[0])
    return prix, float(std["rate"])


def comparer(ids):
    tva = B["societe"].get("tva_taux", 0.2)
    liv = B["livraison"]
    for pid in ids:
        prod, choix = variantes(pid)
        noir = choix.get("noir") or next(iter(choix.values()))
        vid = noir["tailles"].get("M") or next(iter(noir["tailles"].values()))
        p_tshirt, p_liv = couts(pid, vid)
        print(f"\n{prod['brand']} {prod['model']} (id {pid}) — couleurs trouvées : {', '.join(choix)}")
        if p_tshirt is None:
            print("  Prix du t-shirt introuvable via l'API : regarde-le sur printful.com, puis choisis avec --choisir ID --prix XX,90.")
            continue
        p, d = prix_vente(p_tshirt, p_liv, liv["mode"], liv["forfait"], tva)
        print(f"  T-shirt (impression dos incluse) : {p_tshirt:.2f} € HT · livraison France : {p_liv:.2f} €")
        print(f"  → Prix de vente : {p:.2f} € TTC"
              + (f" + {liv['forfait']:.2f} € de livraison" if liv["mode"] == "forfait" else " livraison offerte"))
        print(f"    encaissé {d['encaisse']} − TVA {d['tva']} − Stripe {d['stripe']} − t-shirt {d['tshirt']} "
              f"− livraison {d['livraison']} = marge {d['marge']} €")


def choisir(pid, prix_force=None):
    prod, choix = variantes(pid)
    noir = choix.get("noir") or next(iter(choix.values()))
    vid = noir["tailles"].get("M") or next(iter(noir["tailles"].values()))
    p_tshirt, p_liv = couts(pid, vid)
    liv = B["livraison"]
    p, d = prix_vente(p_tshirt or 0, p_liv, liv["mode"], liv["forfait"], B["societe"].get("tva_taux", 0.2))
    guide = None
    try:
        tables = appel("GET", f"/products/{pid}/sizes")["size_tables"]
        t = next(x for x in tables if x["type"] == "product_measure")
        unite = "cm" if "cm" in t.get("unit", "") else t.get("unit", "")
        lignes = []
        for s in TAILLES:
            l = [s]
            for m in t["measurements"]:
                val = next((x.get("value") or f"{x.get('min_value')}–{x.get('max_value')}" for x in m["values"] if x["size"] == s), None)
                l.append(val or "")
            if any(l[1:]):
                lignes.append(l)
        guide = {"colonnes": ["Taille"] + [f"{m['type_label']} ({unite})" for m in t["measurements"]], "lignes": lignes,
                 "note": "Mesures du t-shirt à plat. Compare avec un t-shirt que tu portes déjà."}
    except Exception:
        pass
    cfg = {"produit_id": pid, "nom": f"{prod['brand']} {prod['model']}", "couleurs": choix,
           "cout_tshirt_ht": p_tshirt, "cout_livraison_fr": p_liv, "prix_vente": prix_force or p, "detail_prix": d,
           "guide_tailles": guide}
    json.dump(cfg, open(os.path.join(ROOT, "config_printful.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    print(f"Enregistré : {cfg['nom']} à {cfg['prix_vente']:.2f} € — couleurs : {', '.join(choix)}")
    manquantes = [c for c in COULEURS if c not in choix]
    if manquantes:
        print("Couleurs absentes chez ce modèle (les designs concernés prendront noir) : " + ", ".join(manquantes))


if __name__ == "__main__":
    a = sys.argv[1:]
    try:
        if "--comparer" in a:
            comparer([int(x) for x in a[a.index("--comparer") + 1:] if x.isdigit()])
        elif "--choisir" in a:
            pf = float(a[a.index("--prix") + 1].replace(",", ".")) if "--prix" in a else None
            choisir(int(a[a.index("--choisir") + 1]), pf)
        else:
            lister()
    except ErreurPrintful as e:
        sys.exit(f"Printful : {e}")
