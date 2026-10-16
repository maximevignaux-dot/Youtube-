"""Petit client Printful (API v1) + calcul du prix de vente. Partagé par choisir_tshirt.py et publish.py."""
import math, os, time
import requests
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(ROOT, ".env"))
API = "https://api.printful.com"
PAUSE = 6.5  # Printful : 10 requêtes par minute maximum

STRIPE_POURCENT, STRIPE_FIXE = 0.015, 0.25  # cartes européennes standard
MARGE_MIN = 10.0
TAILLES = ["S", "M", "L", "XL", "2XL", "3XL"]
COULEURS = {  # nos couleurs → noms Printful, par ordre de préférence
    "noir": ["Black"], "blanc": ["White"], "marine": ["Navy", "French Navy", "Navy Blazer"],
    "kaki": ["Military Green", "Olive", "Khaki", "Army"], "sable": ["Sand", "Natural", "Heather Dust", "Desert Dust"],
    "gris": ["Athletic Heather", "Sport Grey", "Heather Grey", "Heather Grey"],
}


class ErreurPrintful(Exception):
    pass


_dernier = [0.0]


def appel(methode, chemin, auth=True, **kw):
    attente = PAUSE - (time.time() - _dernier[0])
    if attente > 0:
        time.sleep(attente)
    h = kw.pop("headers", {})
    if auth:
        tok = os.getenv("PRINTFUL_TOKEN")
        if not tok:
            raise ErreurPrintful("PRINTFUL_TOKEN est vide dans le fichier .env")
        h["Authorization"] = f"Bearer {tok}"
        if os.getenv("PRINTFUL_STORE_ID"):
            h["X-PF-Store-Id"] = os.getenv("PRINTFUL_STORE_ID")
    r = requests.request(methode, API + chemin, headers=h, timeout=60, **kw)
    _dernier[0] = time.time()
    if r.status_code == 429:
        time.sleep(60)
        return appel(methode, chemin, auth, headers=h, **kw)
    data = r.json() if r.content else {}
    if r.status_code >= 400:
        msg = (data.get("error") or {}).get("message") or data.get("result") or r.text[:300]
        raise ErreurPrintful(f"{methode} {chemin} → {r.status_code} : {msg}")
    return data.get("result", data)


def arrondi_90(v):
    """Plus petit prix en ,90 supérieur ou égal à v (ex. 23,12 → 23,90 ; 23,95 → 24,90)."""
    return round(math.ceil(round(v - 0.90, 6)) + 0.90, 2)


def prix_vente(cout_tshirt, cout_livraison, mode_livraison, forfait, tva=0.20):
    """Prix TTC tel qu'il reste au moins 10 € de marge, une fois payés la TVA, Stripe, le t-shirt et la livraison.
    Coûts Printful hors TVA (la TVA qu'ils facturent est récupérable si la société est assujettie).
    tva = 0 si la société est en franchise de TVA."""
    # encaissé/(1+TVA) − encaissé × 1,5 % − 0,25 € − t-shirt − livraison ≥ 10 €, encaissé = prix (+ forfait de port)
    brut = (cout_tshirt + cout_livraison + MARGE_MIN + STRIPE_FIXE) / (1 / (1 + tva) - STRIPE_POURCENT)
    p = arrondi_90(brut - (0 if mode_livraison == "offerte" else forfait))
    encaisse = p + (0 if mode_livraison == "offerte" else forfait)
    frais = encaisse * STRIPE_POURCENT + STRIPE_FIXE
    tva_due = encaisse - encaisse / (1 + tva)
    marge = encaisse - tva_due - frais - cout_tshirt - cout_livraison
    return p, {"encaisse": round(encaisse, 2), "tva": round(tva_due, 2), "stripe": round(frais, 2),
               "tshirt": cout_tshirt, "livraison": cout_livraison, "marge": round(marge, 2)}
