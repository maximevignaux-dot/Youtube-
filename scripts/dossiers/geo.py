"""Petit dictionnaire géographique pour les cartes (noms français → coordonnées / pays)."""
from .script_md import normaliser

# villes et lieux : (longitude, latitude)
LIEUX = {
    "paris": (2.35, 48.86), "bordeaux": (-0.58, 44.84), "berson": (-0.58, 45.10), "blaye": (-0.66, 45.13),
    "gironde": (-0.60, 44.90), "lyon": (4.84, 45.76), "marseille": (5.37, 43.30), "geneve": (6.14, 46.20),
    "lausanne": (6.63, 46.52), "zurich": (8.54, 47.37), "berne": (7.45, 46.95), "vaduz": (9.52, 47.14),
    "liechtenstein": (9.52, 47.14), "luxembourg": (6.13, 49.61), "monaco": (7.42, 43.73),
    "bruxelles": (4.35, 50.85), "londres": (-0.13, 51.51), "gibraltar": (-5.35, 36.14),
    "madrid": (-3.70, 40.42), "singapour": (103.82, 1.35), "hongkong": (114.17, 22.32),
    "dubai": (55.27, 25.20), "telaviv": (34.78, 32.08), "newyork": (-74.00, 40.71), "bangui": (18.56, 4.36),
    "abidjan": (-4.03, 5.36), "dakar": (-17.47, 14.72), "douala": (9.70, 4.05), "yaounde": (11.52, 3.85),
    "libreville": (9.45, 0.39), "kinshasa": (15.27, -4.33), "lagos": (3.38, 6.52), "casablanca": (-7.59, 33.57),
    "alger": (3.06, 36.75), "tunis": (10.18, 36.81), "ouagadougou": (-1.53, 12.37), "niamey": (2.11, 13.51),
    "nouakchott": (-15.98, 18.08), "cotonou": (2.42, 6.37), "antananarivo": (47.52, -18.88),
    "luanda": (13.23, -8.84), "addisabeba": (38.75, 9.03), "brazzaville": (15.28, -4.27), "ndjamena": (15.04, 12.13),
}

# pays : nom français normalisé → nom dans world-atlas
PAYS = {
    "france": "France", "suisse": "Switzerland", "liechtenstein": "Liechtenstein", "espagne": "Spain",
    "belgique": "Belgium", "luxembourg": "Luxembourg", "italie": "Italy", "allemagne": "Germany",
    "royaumeuni": "United Kingdom", "singapour": "Singapore", "israel": "Israel", "etatsunis": "United States of America",
    "cameroun": "Cameroon", "senegal": "Senegal", "cotedivoire": "Côte d'Ivoire", "burkinafaso": "Burkina Faso",
    "burkina": "Burkina Faso", "niger": "Niger", "nigeria": "Nigeria", "mauritanie": "Mauritania", "benin": "Benin",
    "algerie": "Algeria", "maroc": "Morocco", "tunisie": "Tunisia", "madagascar": "Madagascar", "rdc": "Dem. Rep. Congo",
    "angola": "Angola", "ethiopie": "Ethiopia", "gabon": "Gabon", "congo": "Congo", "tchad": "Chad",
    "centrafrique": "Central African Rep.", "mali": "Mali", "guinee": "Guinea", "togo": "Togo", "ghana": "Ghana",
    "kenya": "Kenya", "egypte": "Egypt", "afriquedusud": "South Africa", "chine": "China", "russie": "Russia",
}
# expressions en plusieurs mots
PAYS_COMPOSES = {("cote", "divoire"): "cotedivoire", ("burkina", "faso"): "burkinafaso", ("etats", "unis"): "etatsunis",
                 ("royaume", "uni"): "royaumeuni", ("afrique", "du", "sud"): "afriquedusud",
                 ("new", "york"): "newyork", ("tel", "aviv"): "telaviv", ("hong", "kong"): "hongkong",
                 ("addis", "abeba"): "addisabeba"}

# régions : (ouest, sud, est, nord)
REGIONS = {
    "afrique": (-20, -36, 53, 38), "europe": (-12, 35, 30, 60), "france": (-5.5, 41.2, 9.8, 51.3),
    "monde": (-170, -58, 180, 80), "suisse": (5.8, 45.7, 10.6, 47.9),
}
CENTRE_AFRIQUE = ["dakar", "abidjan", "douala", "libreville"]


def chercher(texte: str):
    """Renvoie la liste ordonnée [(cle, genre)] des lieux / pays / régions cités dans un texte."""
    mots = [normaliser(m) for m in texte.replace("→", " → ").replace("-", " ").replace("'", " ").split()]
    mots = [m for m in mots if m]
    trouves, k = [], 0
    while k < len(mots):
        pris = False
        for seq, cle in PAYS_COMPOSES.items():
            if tuple(mots[k:k + len(seq)]) == seq:
                trouves.append((cle, "pays" if cle in PAYS else "lieu"))
                k += len(seq)
                pris = True
                break
        if pris:
            continue
        m = mots[k]
        if m in LIEUX and m not in PAYS:
            trouves.append((m, "lieu"))
        elif m in PAYS:
            trouves.append((m, "pays"))
        elif m in REGIONS:
            trouves.append((m, "region"))
        k += 1
    return trouves
