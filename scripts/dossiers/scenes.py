"""Fabrique scenes.json : le plan de montage complet, calé au mot près sur la voix.

Deux pistes :
- « fond »   : ce qui remplit l'écran (photo/vidéo, fiche, carte, tableau, compteur…), sans trou ;
- « calques »: ce qui se pose PAR-DESSUS au mot exact (mot-clé, tampon, chiffre incrusté).

Chaque scène garde son ancre (numéro du mot dans le script) : pour passer à la vraie voix, on
recalcule seulement les temps, les choix visuels ne bougent pas.
"""
import json
import os
import re

from . import geo
from .script_md import normaliser, sans_accents

# ---------------------------------------------------------------- réglages de rythme (secondes)
MIN = {  # temps minimum à l'écran pour avoir le temps de lire
    "Media": 1.6, "FichePersonnage": 5.0, "DocumentCaviarde": 5.0, "CarteFlux": 4.0, "TableauEnquete": 4.0,
    "GraphiqueAnime": 4.0, "CompteurBillets": 3.6, "ChiffreCle": 2.8, "TimelineMachine": 2.2, "Citation": 4.0,
    "Schema": 4.5, "Teaser": 4.0,
}
MAX = {  # au-delà, on enchaîne sur un autre visuel (jamais d'image fixe > 5 s)
    "Media": 4.8, "FichePersonnage": 7.5, "DocumentCaviarde": 7.5, "CarteFlux": 10.0, "TableauEnquete": 8.0,
    "GraphiqueAnime": 6.5, "CompteurBillets": 5.5, "ChiffreCle": 5.0, "TimelineMachine": 2.8, "Citation": 6.5,
    "Schema": 8.0, "Teaser": 60.0,
}
HOOK_MAX_MEDIA = 2.4      # dans le hook : un visuel toutes les 1,5–2,5 s
CALQUE_MIN, CALQUE_MAX = 1.5, 2.6
BROLL_CIBLE = 3.8         # durée visée d'un plan de remplissage

MOTS_VIDES = set("""a au aux avec ce ces cet cette c ca d de des du elle elles en et est etre il ils j je l la le les
leur leurs lui m ma mais me meme mes mon n ne ni nos notre nous on ou par pas plus pour qu que qui s sa sans se ses
si son sont sur t ta te tes ton tu un une vos votre vous y la tout tous toute toutes alors donc bon bref oui non
tres bien deja aussi comme quand puis la-bas voila c'est cest dun dune quil quelle quon""".split())

UNITES_ARGENT = {"€": "€", "eur": "€", "euro": "€", "euros": "€", "chf": "CHF", "franc": "CHF", "francs": "CHF",
                 "$": "$", "dollar": "$", "dollars": "$"}
MULT = {"mille": 1e3, "k": 1e3, "million": 1e6, "millions": 1e6, "m": 1e6, "milliard": 1e9, "milliards": 1e9,
        "md": 1e9, "mds": 1e9, "mrd": 1e9}
UNITES_AUTO = {"km": "KM", "kilometres": "KM", "kilometre": "KM", "ans": "ANS", "salaries": "SALARIÉS",
               "pays": "PAYS", "bouteilles": "BOUTEILLES", "enfants": "ENFANTS", "marques": "MARQUES",
               "millions": "MILLIONS", "milliards": "MILLIARDS", "euros": "€", "%": "%", "pour": "%"}


# ================================================================ utilitaires
def lire_nombre(s: str):
    """« 410 millions de francs suisses » → (410000000, 'CHF', reste) ; « 6,9 Md€ » → (6.9e9, '€')."""
    t = s.replace(" ", " ").replace("\xa0", " ")
    m = re.search(r"(\d{1,3}(?:[ .]\d{3})+|\d+(?:,\d+)?)", t)
    if not m:
        return None, None, s
    v = float(m.group(1).replace(" ", "").replace(".", "").replace(",", "."))
    apres = t[m.end():].strip()
    mots = re.findall(r"[A-Za-zÀ-ÿ€$%]+", apres)
    k = 0
    if mots and sans_accents(mots[0]).lower().rstrip("€") in MULT:
        brut = sans_accents(mots[0]).lower()
        v *= MULT[brut.rstrip("€")]
        if brut.endswith("€"):
            return v, "€", ""
        k = 1
    devise = None
    for mot in mots[k:k + 3]:
        cle = sans_accents(mot).lower()
        if cle in UNITES_ARGENT:
            devise = UNITES_ARGENT[cle]
            break
    if "€" in apres[:6]:
        devise = "€"
    reste = " ".join(w for w in mots[k:] if sans_accents(w).lower() not in ("de", "d", "francs", "suisses", "euros", "chf", "€", "rouge", "vert"))
    return v, devise, reste


def guillemets(s: str):
    return re.findall(r"[\"“«]\s*([^\"”»]+?)\s*[\"”»]", s)


def formater(v: float) -> str:
    if v == int(v):
        return f"{int(v):,}".replace(",", " ")
    return f"{v:.1f}".replace(".", ",")


class Chrono:
    """Temps (ms) de chaque mot du script dans la voix."""

    def __init__(self, mots, nb_tokens, duree_ms):
        self.debut = [0] * nb_tokens
        self.fin = [0] * nb_tokens
        for m in mots:
            self.debut[m["i"]] = m["debut"]
            self.fin[m["i"]] = m["fin"]
        self.duree = duree_ms

    def t(self, i):
        return self.debut[i] if i < len(self.debut) else self.duree


# ================================================================ a-chercher.md
def lire_a_chercher(chemin):
    if not os.path.exists(chemin):
        return []
    lignes = [l for l in open(chemin, encoding="utf-8").read().splitlines() if l.startswith("|")]
    items = []
    for l in lignes[2:]:
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) < 5 or not re.match(r"^[A-Z]+\d+$", c[0]):
            continue
        genre = sans_accents(c[1]).lower()
        items.append({
            "id": c[0], "genre": "video" if "vid" in genre else "ia" if "ia" in genre else "photo",
            "moment": c[2], "description": c[3], "motsCles": c[4], "ou": c[5] if len(c) > 5 else "",
        })
    return items


def placer_item(item, tokens):
    """Retrouve dans le script la phrase citée dans « Moment ». Renvoie l'index du premier mot ou None."""
    cites = re.findall(r"«\s*(.+?)\s*»", item["moment"])
    for cite in cites:
        cible = [normaliser(w) for w in cite.replace("…", " ").split()]
        cible = [w for w in cible if w]
        if not cible:
            continue
        mots = [t["mot"] for t in tokens]
        n = len(cible)
        meilleur, score = None, 0
        for k in range(len(mots) - n + 1):
            s = sum(1 for a, b in zip(mots[k:k + n], cible) if a == b)
            if s > score:
                meilleur, score = k, s
        if meilleur is not None and score >= max(1, int(n * 0.7)):
            return meilleur
    return None


# ================================================================ recherche de mots dans un morceau
def trouver_mot(tokens, m, aiguille, apres=None):
    """Index du mot du morceau m qui correspond le mieux à « aiguille » (nombre, puis suite de mots)."""
    debut = m["debut"] if apres is None else max(m["debut"], apres)
    zone = tokens[debut:m["fin"]]
    mots = [t["mot"] for t in zone]
    cible = [normaliser(w) for w in aiguille.replace("→", " ").split()]
    cible = [w for w in cible if w]
    if not cible:
        return None
    # 1) la suite complète
    for k in range(len(mots) - len(cible) + 1):
        if mots[k:k + len(cible)] == cible:
            return debut + k
    # 2) le premier nombre
    for w in cible:
        if w.isdigit():
            for k, x in enumerate(mots):
                if x == w or (len(w) >= 4 and x.startswith(w[:4]) and x.isdigit()):
                    return debut + k
    # 3) le mot le plus long
    for w in sorted(cible, key=len, reverse=True):
        if len(w) < 3:
            break
        for k, x in enumerate(mots):
            if x == w or (len(w) > 4 and x.startswith(w[:-1])):
                return debut + k
    return None


def mots_cles(texte, n=5):
    vus, res = set(), []
    for w in re.findall(r"[A-Za-zÀ-ÿ0-9'’-]+", texte):
        cle = normaliser(w)
        if len(cle) < 3 or cle in MOTS_VIDES or cle in vus:
            continue
        vus.add(cle)
        res.append(w.strip("'’").lower())
    return res[:n]


# ================================================================ construction
class Monteur:
    def __init__(self, script, chrono, items, slug):
        self.s, self.c, self.items, self.slug = script, chrono, items, slug
        self.tokens = script["tokens"]
        self.fond, self.calques = [], []
        self.n_auto = 0
        self.tableaux = []          # [{centre, elements}]
        self.pays_allumes = []      # pour « tous les pays allumés »
        self.dates = []             # frise chronologique
        self.timeline_de = {}       # morceau → mot de la date
        self.morceau_de = {}
        for idx, m in enumerate(script["morceaux"]):
            for k in range(m["debut"], m["fin"]):
                self.morceau_de[k] = idx

    # ---------- ids
    def nouvel_id(self):
        return "AUTO"  # numéroté S001, S002… dans l'ordre du film à la fin

    def ms(self, i):
        return self.c.t(i)

    def fin_morceau(self, m):
        return self.c.fin[m["fin"] - 1]

    def ajouter(self, composant, tok, props, **extra):
        # si la phrase contient une date [TIMELINE], la date passe en premier
        mi = self.morceau_de.get(tok)
        if composant != "TimelineMachine" and mi in self.timeline_de:
            tok = max(tok, self.timeline_de[mi])
        ev = {"composant": composant, "ancre": tok, "debutMs": self.ms(tok), "props": props}
        ev.update(extra)
        self.fond.append(ev)
        return ev

    def calque(self, composant, tok, props, fin_ms=None):
        d = self.ms(tok)
        f = fin_ms if fin_ms else d + CALQUE_MIN * 1000
        f = min(max(f, d + CALQUE_MIN * 1000), d + CALQUE_MAX * 1000)
        self.calques.append({"composant": composant, "ancre": tok, "debutMs": d, "finMs": f, "props": props})

    def media(self, tok, genre, description, requete=None, item=None, **props):
        asset = {
            "id": item["id"] if item else self.nouvel_id(), "genre": item["genre"] if item else genre,
            "description": item["description"] if item else description,
            "requetes": item["motsCles"] if item else requete or ", ".join(mots_cles(description)),
            "ou": item["ou"] if item else "", "source": "a-chercher" if item else "auto",
        }
        return self.ajouter("Media", tok, {"assetId": asset["id"], "genre": asset["genre"],
                                           "description": asset["description"], **props}, asset=asset)

    # ---------- balises
    def traiter(self):
        s, toks = self.s, self.tokens
        piece_courante = 0
        for m in s["morceaux"]:
            pos_chiffres = []
            for b in m["balises"]:
                t, x = b["type"], b["texte"]
                if t == "OUVERTURE_DOSSIER":
                    n = re.search(r"\d+", x)
                    self.ouverture = {"numero": int(n.group()) if n else (s["meta"]["numero"] or 1)}
                elif t == "PIECE":
                    n = re.search(r"\d+", x)
                    titre = (guillemets(x) or [re.sub(r"^\d+\s*", "", x)])[0]
                    piece_courante = int(n.group()) if n else piece_courante + 1
                    fin = self.ms(m["debut"])
                    self.fond.append({"composant": "CartonPiece", "ancre": m["debut"], "fixe": True,
                                      "debutMs": fin - 2700, "finMs": fin, "props": {"numero": piece_courante, "titre": titre}})
                elif t in ("PHOTO", "VIDEO", "IMAGE", "IMAGE_IA", "VIDEO_IA"):
                    genre = "video" if "VIDEO" in t else "ia" if "IA" in t or t == "IMAGE" else "photo"
                    ev = self.media(m["debut"], genre, x)
                    ev["depuis_balise"] = True
                elif t == "MOT":
                    mot = (guillemets(x) or [x])[0]
                    k = trouver_mot(toks, m, mot) or m["debut"]
                    self.calque("MotCle", k, {"texte": mot.upper(), "surligne": len(mot) > 10},
                                fin_ms=self.fin_morceau(m) + 300)
                elif t == "TAMPON":
                    self.calque("TamponCalque", m["debut"], {"texte": (guillemets(x) or [x])[0]},
                                fin_ms=self.fin_morceau(m) + 600)
                elif t == "TIMELINE":
                    k = trouver_mot(toks, m, x) or m["debut"]
                    self.dates.append(x)
                    self.timeline_de[self.morceau_de.get(m["debut"])] = k
                    self.ajouter("TimelineMachine", k, {"date": x, "precedentes": self.dates[-5:-1]})
                elif t in ("CHIFFRE", "COMPTEUR"):
                    self.chiffre(m, b, pos_chiffres)
                elif t == "FICHE":
                    self.fiche(m, x)
                elif t == "DOCUMENT":
                    self.document(m, x)
                elif t == "CARTE":
                    self.carte(m, x)
                elif t == "GRAPH":
                    self.graph(m, x)
                elif t == "TABLEAU":
                    self.tableau(m, x)
                elif t == "CITATION":
                    q = guillemets(x)
                    auteur = x.split("—")[-1].strip() if "—" in x else ""
                    self.ajouter("Citation", m["debut"], {"texte": q[0] if q else x, "auteur": auteur})
                elif t == "SCHEMA":
                    self.schema(m, x)
                elif t == "TEASER":
                    self.teaser = self.ajouter("Teaser", m["debut"], {
                        "numero": (s["meta"]["numero"] or 1) + 1, "titre": x.strip() or "Prochain dossier"})
        self.items_libres()
        self.chiffres_auto()

    def chiffre(self, m, b, deja):
        x = b["texte"]
        v, devise, reste = lire_nombre(x)
        contexte = sans_accents(x + " " + m["texte"]).lower()
        rouge = any(w in contexte for w in ("rouge", "perte", "facture", "redressement", "amende", "dette", "sanction"))
        k = trouver_mot(self.tokens, m, x, apres=deja[-1] + 1 if deja else None)
        if k is None:
            k = (deja[-1] + 2) if deja else m["debut"]
        deja.append(k)
        if b["type"] == "COMPTEUR" or devise:
            # compteuse de billets (argent)
            emballe = v is None
            prec = [e for e in self.fond if e["composant"] == "CompteurBillets" and e["props"].get("montant") == v and v]
            ev = self.ajouter("CompteurBillets", k if not emballe else m["debut"], {
                "montant": v or 9_999_999_999, "devise": devise or "€", "sens": "perte" if rouge else "gain",
                "emballe": emballe, "libelle": None if prec else None,
            })
            return ev
        # chiffre-clé (non monétaire) : on regroupe ceux d'un même morceau dans un seul panneau
        item = {"valeur": v, "texte": formater(v) if v is not None else x.split()[0],
                "unite": (reste or (x.split(" ", 1)[1] if " " in x else "")).upper(), "aMs": self.ms(k)}
        if v is None:  # « N°2 en Afrique »
            item = {"valeur": None, "texte": x.split()[0], "unite": " ".join(x.split()[1:]).upper(), "aMs": self.ms(k)}
        dernier = self.fond[-1] if self.fond else None
        if dernier and dernier["composant"] == "ChiffreCle" and dernier.get("morceau") == m["debut"]:
            dernier["props"]["items"].append(item)
        else:
            self.ajouter("ChiffreCle", k, {"items": [item]}, morceau=m["debut"])

    def fiche(self, m, x):
        parts = [p.strip() for p in x.split("|")]
        nom = parts[0]
        champs, tampon = [], None
        labels = ["RÔLE", "DÉTAIL", "NOTE"]
        for p in parts[1:]:
            if p == "???":
                champs.append({"label": "STATUT", "valeur": "???"})
            elif p.isupper() and len(p) > 3 and not re.search(r"\d", p):
                tampon = p
            else:
                champs.append({"label": labels[min(len(champs), 2)], "valeur": p})
        cle = normaliser(nom)
        item = next((i for i in self.items if "fiche" in i["moment"].lower()
                     and any(normaliser(q) == cle for q in re.findall(r"«\s*(.+?)\s*»", i["moment"]))), None)
        if item:
            item["utilise"] = True
        asset = {"id": item["id"] if item else self.nouvel_id(), "genre": item["genre"] if item else "photo",
                 "description": item["description"] if item else f"Portrait ou photo de : {nom}",
                 "requetes": item["motsCles"] if item else nom, "ou": item["ou"] if item else "Wikimedia Commons",
                 "source": "a-chercher" if item else "auto"}
        self.ajouter("FichePersonnage", m["debut"], {
            "assetId": asset["id"], "descriptionPhoto": asset["description"], "nom": nom, "champs": champs,
            "tampon": tampon}, asset=asset)

    def phrases(self, m):
        """Découpe un morceau en phrases avec le mot de début de chacune."""
        res, debut = [], m["debut"]
        for k in range(m["debut"], m["fin"]):
            if re.search(r"[.?!:]\W*$", self.tokens[k]["brut"]) or k == m["fin"] - 1:
                res.append((debut, " ".join(t["brut"] for t in self.tokens[debut:k + 1])))
                debut = k + 1
        return res

    def document(self, m, x):
        q = guillemets(x)
        bas = sans_accents(x).lower()
        style = "journal" if "presse" in bas or "journal" in bas else "rapport" if "rapport" in bas else "document"
        entete = q[0] if q else re.split(r",|\s+recr[ée]{2}e?s?\b", x)[0].strip()
        if style == "journal" and not q:
            entete = "LA PRESSE EN PARLE"
        caviarde = "caviard" in bas
        phrases = self.phrases(m)[:4]
        d0 = self.ms(m["debut"])
        lignes = []
        for n, (k, texte) in enumerate(phrases):
            cle = n == len(phrases) - 1 or bool(re.search(r"\d", texte))
            lignes.append({"texte": texte.replace("…", "…"), "caviarde": caviarde,
                           "revelerAMs": self.ms(k) if caviarde else None,
                           "surligner": ("surlign" in bas or "jaune" in bas or caviarde) and cle})
        if not any(l["surligner"] for l in lignes) and lignes:
            lignes[-1]["surligner"] = True
        self.ajouter("DocumentCaviarde", m["debut"], {"style": style, "entete": entete.upper(), "lignes": lignes,
                                                      "tampon": "CONFIDENTIEL" if caviarde else None})

    def carte(self, m, x):
        bas = sans_accents(x).lower()
        d0 = self.ms(m["debut"])
        trouves = geo.chercher(x)
        points, pays, regions = [], [], []
        for cle, genre in trouves:
            if genre == "region":
                regions.append(cle)
                if cle == "afrique" and "→" in x:
                    for v in geo.CENTRE_AFRIQUE:
                        points.append({"nom": "", "lon": geo.LIEUX[v][0], "lat": geo.LIEUX[v][1], "secondaire": True})
            if cle in geo.LIEUX:
                points.append({"nom": cle_affichee(cle, x), "lon": geo.LIEUX[cle][0], "lat": geo.LIEUX[cle][1]})
            if genre == "pays" and cle in geo.PAYS:
                pays.append({"nom": geo.PAYS[cle], "aMs": 0})
        # pays cités à voix haute pendant la carte : ils s'allument au mot exact (+ « clic »)
        k = m["debut"]
        mots = self.tokens
        idx = m["debut"]
        while idx < m["fin"]:
            seg = " ".join(t["brut"] for t in mots[idx:idx + 3])
            f = geo.chercher(seg)
            if f and f[0][1] == "pays" and f[0][0] in geo.PAYS:
                nom = geo.PAYS[f[0][0]]
                if all(p["nom"] != nom for p in pays):
                    pays.append({"nom": nom, "aMs": self.ms(idx), "clic": True})
                idx += 2 if f[0][0] in ("cotedivoire", "burkinafaso") else 1
            else:
                idx += 1
        tous = "tous les pays" in bas
        if "suite" in bas or tous:
            precedents = [{"nom": n, "aMs": 0} for n in self.pays_allumes if all(p["nom"] != n for p in pays)]
            pays = precedents + pays
        for p in pays:
            if p["nom"] not in self.pays_allumes:
                self.pays_allumes.append(p["nom"])
        if "afrique" in bas and "afrique" not in regions:
            regions.append("afrique")
        flux = []
        principaux = [i for i, p in enumerate(points) if not p.get("secondaire")]
        if "→" in x and points:
            src = principaux[0] if principaux else 0
            flux = [[src, j] for j in range(len(points)) if j != src]
        elif "reli" in bas and len(points) > 1:
            flux = [[j, j + 1] for j in range(len(points) - 1)] + [[len(points) - 1, 0]]
        zoom = None
        if "zoom" in bas:
            q = guillemets(x)
            cible = normaliser(q[-1]) if q else None
            zoom = next((p for p in points if normaliser(p["nom"]) == cible), points[-1] if points else None)
        dernier_pays = max([p["aMs"] - d0 for p in pays], default=0)
        self.ajouter("CarteFlux", m["debut"], {
            "points": points, "flux": flux, "pays": pays, "regions": regions, "zoom": zoom,
            "accent": "rouge" if any(w in bas for w in ("conflit", "guerre", "centrafrique")) else "vert",
            "acceleration": "acceler" in bas,
        }, minMs=max(MIN["CarteFlux"] * 1000, dernier_pays + 1500))

    def graph(self, m, x):
        q = guillemets(x)
        barres = []
        tailles = {"petite": 1, "minuscule": 0.6, "moyenne": 4, "grande": 7, "enorme": 10, "geante": 10}
        if q:
            for lab in q:
                apres = sans_accents(re.split(r'["“«]', x.split(lab, 1)[1].lstrip('"”» '))[0]).lower() if lab in x else ""
                mot = next((w for w in tailles if w in apres.split(",")[0]), "moyenne")
                barres.append({"label": lab.upper(), "valeur": tailles[mot], "texte": ""})
        else:
            valeurs = re.findall(r"(\d+(?:,\d+)?)\s*(M€|Md€|k€|€|%|M|Md)?", x)
            labels = ["AVANT", "APRÈS"] if len(valeurs) == 2 else [f"" for _ in valeurs]
            for (v, u), lab in zip(valeurs, labels):
                barres.append({"label": lab, "valeur": float(v.replace(",", ".")), "texte": f"{v} {u}".strip()})
        titre = mots_cles(m["texte"], 3)
        self.ajouter("GraphiqueAnime", m["debut"], {"barres": barres, "titre": ""})

    def tableau(self, m, x):
        bas = sans_accents(x).lower()
        q = guillemets(x)
        d0 = self.ms(m["debut"])
        if not self.tableaux or bas.startswith("nouveau") or "au centre" in bas:
            if "au centre" in bas:
                centres = [x.split("au centre")[0].strip()]
            elif q:
                centres = [q[0]]
            else:
                txt = re.sub(r"^nouveau\s*:?\s*", "", x, flags=re.I).split(",")[0]
                centres = [c.strip() for c in re.split(r"\bvs\b", txt)]
            self.tableaux.append({"centres": [c.upper() for c in centres], "elements": []})
            mode = "nouveau"
        else:
            mode = "ensemble" if "ensemble" in bas else "coupe" if "coupe" in bas else "ajout" if "ajout" in bas else "vue"
        tab = self.tableaux[-1]
        for e in tab["elements"]:
            e["nouveau"] = False
        if "ajout" in bas and q:
            tab["elements"].append({"label": q[0].upper(), "nouveau": True, "filRouge": "fil rouge" in bas})
        if mode == "ensemble" and "complete" in bas:
            # vue d'ensemble de toute l'enquête : tous les tableaux réunis
            tous = [{"label": c, "nouveau": False, "filRouge": True} for t in self.tableaux[:-1] for c in t["centres"]]
            tous += [e for t in self.tableaux for e in t["elements"]]
            props = {"centres": self.tableaux[0]["centres"], "elements": tous, "mode": "ensemble"}
        else:
            props = {"centres": tab["centres"], "elements": [dict(e) for e in tab["elements"]], "mode": mode}
        self.ajouter("TableauEnquete", m["debut"], props)

    def schema(self, m, x):
        etapes = []
        for p in x.split("→"):
            p = re.sub(r"^.*?:", "", p).strip()
            q = guillemets(p)
            if "fleche" in sans_accents(p).lower():
                continue
            if q:
                etapes.append(q[0].upper())
            elif "personnage" in p.lower():
                etapes.append("VOUS")
            elif p:
                etapes.append(p.upper())
        d0 = self.ms(m["debut"])
        self.ajouter("Schema", m["debut"], {"etapes": etapes or ["?"], "pas": 900})

    def items_libres(self):
        """Visuels de a-chercher.md : on les accroche à la balise photo/vidéo la plus proche, sinon on les pose."""
        medias = [e for e in self.fond if e["composant"] == "Media" and e.get("depuis_balise")]
        for item in self.items:
            if item.get("utilise"):
                continue
            if "teaser" in item["moment"].lower() and getattr(self, "teaser", None):
                self.teaser["props"]["fondAssetId"] = item["id"]
                self.teaser["asset"] = {"id": item["id"], "genre": item["genre"], "description": item["description"],
                                        "requetes": item["motsCles"], "ou": item["ou"], "source": "a-chercher"}
                item["utilise"] = True
                continue
            k = placer_item(item, self.tokens)
            if k is None:
                print(f"   ⚠️  {item['id']} : phrase introuvable dans le script ({item['moment'][:60]})")
                continue
            mi = self.morceau_de.get(k)
            cible = next((e for e in medias if not e.get("item") and self.morceau_de.get(e["ancre"]) == mi), None)
            if cible:
                cible["item"] = item["id"]
                cible["asset"].update({"id": item["id"], "genre": item["genre"], "description": item["description"],
                                       "requetes": item["motsCles"], "ou": item["ou"], "source": "a-chercher"})
                cible["props"].update({"assetId": item["id"], "genre": item["genre"], "description": item["description"]})
            else:
                ev = self.media(k, item["genre"], item["description"], item=item)
                ev["item"] = item["id"]
            item["utilise"] = True

    def chiffres_auto(self):
        """Nombres prononcés sans balise (« 5 000 kilomètres », « 70 % »…) → chiffre incrusté à l'écran."""
        deja = set()
        for e in self.fond:
            if e["composant"] in ("ChiffreCle", "CompteurBillets", "GraphiqueAnime", "TimelineMachine", "FichePersonnage"):
                deja.add(self.morceau_de.get(e["ancre"]))
        toks = self.tokens
        k = 0
        while k < len(toks):
            w = toks[k]["mot"]
            if not w.isdigit():
                k += 1
                continue
            j = k
            while j + 1 < len(toks) and toks[j + 1]["mot"].isdigit() and len(toks[j + 1]["mot"]) == 3:
                j += 1
            nombre = " ".join(t["brut"].strip(".,;:!?") for t in toks[k:j + 1])
            suivant = toks[j + 1]["mot"] if j + 1 < len(toks) else ""
            brut_suivant = toks[j + 1]["brut"] if j + 1 < len(toks) else ""
            unite = UNITES_AUTO.get(suivant) or ("%" if brut_suivant.startswith("%") else None)
            if "%" in toks[k]["brut"]:
                unite = "%"
            mi = self.morceau_de.get(k)
            annee = len(w) == 4 and 1800 <= int(w) <= 2100 and j == k
            if mi in deja or (not unite and not annee):
                k = j + 1
                continue
            if annee:
                # année citée sans [TIMELINE] : petite date tapée à la machine
                if any(sans_accents(d).find(w) >= 0 for d in self.dates):
                    k = j + 1
                    continue
                self.calque("DateIncruste", k, {"texte": w})
            else:
                self.calque("ChiffreIncruste", k, {"texte": nombre, "unite": unite})
            k = j + 1

    # ---------- mise en ordre de la piste de fond
    def assembler(self):
        fond = sorted(self.fond, key=lambda e: (e["debutMs"], 0 if e.get("fixe") else 1))
        hook_fin = 30_000 + (self.ms(0))
        res = []
        for e in fond:
            if res:
                p = res[-1]
                mini = p.get("minMs", MIN.get(p["composant"], 1.5) * 1000)
                if not e.get("fixe") and not p.get("fixe") and e["debutMs"] < p["debutMs"] + mini:
                    e["debutMs"] = p["debutMs"] + mini  # on laisse le temps de lire le précédent
            res.append(e)
        # retire les doublons qui se chevaucheraient complètement
        propre = []
        for e in res:
            if propre and e["debutMs"] <= propre[-1]["debutMs"] and not e.get("fixe"):
                e["debutMs"] = propre[-1]["debutMs"] + 1500
            propre.append(e)
        # un plan ne déborde jamais sur un carton de pièce : s'il a été poussé dedans, on le ramène juste avant
        fixes = [e for e in propre if e.get("fixe")]
        for e in propre:
            if e.get("fixe"):
                continue
            for f in fixes:
                if self.ms(e["ancre"]) < f["debutMs"] <= e["debutMs"] < f.get("finMs", f["debutMs"]) + 1:
                    e["debutMs"] = max(self.ms(e["ancre"]), f["debutMs"] - 1500)
        propre.sort(key=lambda e: e["debutMs"])
        # pas de trou noir après un carton : le plan suivant démarre dès la fin du carton
        for n in range(1, len(propre)):
            p = propre[n - 1]
            if p.get("fixe") and p.get("finMs") and propre[n]["debutMs"] > p["finMs"]:
                propre[n]["debutMs"] = p["finMs"]
        fin_totale = self.c.duree
        # ouverture du dossier
        if getattr(self, "ouverture", None):
            premier = self.ms(0)
            meta = self.s["meta"]
            propre.insert(0, {"composant": "OuvertureDossier", "ancre": 0, "fixe": True, "debutMs": 0, "finMs": premier,
                              "props": {"numero": self.ouverture["numero"], "titre": meta.get("sujet", ""),
                                        "sousTitre": meta.get("sousTitre", "")}})
        # durée de chaque scène = jusqu'à la suivante ; remplissage si trop long
        final = []
        for n, e in enumerate(propre):
            fin = propre[n + 1]["debutMs"] if n + 1 < len(propre) else fin_totale
            if e.get("fixe") and e.get("finMs"):
                fin = min(fin, e["finMs"]) if n + 1 < len(propre) else e["finMs"]
            e["finMs"] = fin
            final.append(e)
            limite = MAX.get(e["composant"], 6) * 1000
            if e["composant"] == "Media" and e["debutMs"] < hook_fin:
                limite = HOOK_MAX_MEDIA * 1000 if self.s["sections"] and e["ancre"] < self.s["sections"][min(1, len(self.s["sections"]) - 1)]["debut"] else limite
            if e.get("fixe") or e["composant"] in ("OuvertureDossier", "CartonPiece"):
                continue
            if e["composant"] == "CarteFlux":
                limite = max(limite, e.get("minMs", 0) + 2500)
            if fin - e["debutMs"] > limite + 400:
                e["finMs"] = e["debutMs"] + limite
                final.extend(self.remplir(e, e["finMs"], fin))
        # le trou éventuel avant la première scène
        return final

    def remplir(self, precedent, debut, fin):
        """Plans de B-roll pour couvrir [debut, fin] : d'abord un recadrage du même média, puis des plans auto."""
        res, t = [], debut
        recadre = precedent["composant"] == "Media" and not precedent.get("recadre")
        while fin - t > 400:
            d = min(BROLL_CIBLE * 1000, fin - t)
            if fin - t - d < 1200:
                d = fin - t
            tok = self.mot_a(t)
            if recadre:
                ev = {"composant": "Media", "ancre": tok, "debutMs": t, "finMs": t + d, "recadre": True,
                      "props": {**precedent["props"], "mouvement": "serre"}, "asset": precedent["asset"], "copie": True}
                recadre = False
            else:
                phrase = self.phrase_autour(tok)
                desc = f"Illustrer : « {phrase} »"
                ev = {"composant": "Media", "ancre": tok, "debutMs": t, "finMs": t + d,
                      "props": {"genre": "video", "description": desc, "mouvement": "auto"},
                      "asset": {"id": self.nouvel_id(), "genre": "video", "description": desc,
                                "requetes": ", ".join(mots_cles(phrase)), "ou": "Pexels, Pixabay", "source": "auto"}}
                ev["props"]["assetId"] = ev["asset"]["id"]
            res.append(ev)
            t += d
        return res

    def mot_a(self, ms):
        k = 0
        for k in range(len(self.c.debut)):
            if self.c.debut[k] >= ms:
                return k
        return k

    def phrase_autour(self, k):
        toks = self.tokens
        a = k
        while a > 0 and not re.search(r"[.?!]\W*$", toks[a - 1]["brut"]):
            a -= 1
        b = k
        while b < len(toks) - 1 and not re.search(r"[.?!]\W*$", toks[b]["brut"]):
            b += 1
        return " ".join(t["brut"] for t in toks[a:b + 1])[:160]


def cle_affichee(cle, texte):
    noms = {"geneve": "Genève", "berson": "Berson", "bordeaux": "Bordeaux", "paris": "Paris", "singapour": "Singapour",
            "gibraltar": "Gibraltar", "liechtenstein": "Liechtenstein", "vaduz": "Vaduz", "telaviv": "Tel Aviv",
            "bangui": "Bangui", "lausanne": "Lausanne"}
    return noms.get(cle, cle.capitalize())


def miniature(script, fond):
    """Lit la ligne « **Miniature :** » du script : tampon, chiffre en vert, sujet détouré."""
    texte = script["meta"].get("miniature", "")
    q = re.findall(r"«\s*(.+?)\s*»", texte)
    chiffre = next((x for x in q if re.search(r"\d", x)), None)
    tampon = next((x for x in q if x != chiffre), None)
    sujet_nom = script["meta"].get("sujet", "")
    m = re.search(r"d[ée]tour[ée]e? de ([^(,]+)", texte)
    if m:
        sujet_nom = m.group(1).strip()
    cle = normaliser(sujet_nom)
    asset = next((e["asset"]["id"] for e in fond if e["composant"] == "FichePersonnage"
                  and normaliser(e["props"]["nom"]) == cle), None)
    return {"tampon": (tampon or "DOSSIER").upper(), "chiffre": chiffre, "sujet": sujet_nom, "assetId": asset,
            "numero": script["meta"].get("numero") or 1}


# ================================================================ point d'entrée
def construire(script, voix, dossier, slug, voix_test=True, fichier_voix=None):
    chrono = Chrono(voix["mots"], len(script["tokens"]), voix["dureeMs"])
    items = lire_a_chercher(os.path.join(dossier, "a-chercher.md"))
    mt = Monteur(script, chrono, items, slug)
    mt.traiter()
    fond = mt.assembler()
    # numérotation des scènes et des visuels auto (S001…) dans l'ordre du film
    n_auto = 0
    for n, e in enumerate(fond):
        e["scene"] = f"#{n + 1:03d}"
        a = e.get("asset")
        if a and a["id"] == "AUTO":
            n_auto += 1
            a["id"] = f"S{n_auto:03d}"
        if a and "assetId" in e["props"]:
            e["props"]["assetId"] = a["id"]
    # parole (pour baisser la musique sous la voix) et grands silences (révélations)
    parole, silences = [], []
    for m in voix["mots"]:
        if parole and m["debut"] - parole[-1][1] < 450:
            parole[-1][1] = m["fin"]
        else:
            if parole and m["debut"] - parole[-1][1] >= 900:
                silences.append([parole[-1][1], m["debut"]])
            parole.append([m["debut"], m["fin"]])
    sections = []
    for sct in script["sections"]:
        nom = sct["nom"]
        piece = re.search(r"PI[EÈ]CE\s*N?°?\s*(\d+)", sans_accents(nom).upper())
        sections.append({"nom": nom, "debutMs": chrono.t(sct["debut"]), "piece": int(piece.group(1)) if piece else None})
    donnees = {
        "miniature": miniature(script, fond),
        "slug": slug, "numero": script["meta"]["numero"], "titre": script["meta"]["titre"],
        "voix": {"fichier": fichier_voix or ("voix-test.mp3" if voix_test else "voix.mp3"), "test": voix_test, "moteur": voix.get("moteur")},
        "dureeMs": voix["dureeMs"], "fond": fond, "calques": sorted(mt.calques, key=lambda c: c["debutMs"]),
        "parole": parole, "silences": silences, "sections": sections,
    }
    with open(os.path.join(dossier, "scenes.json"), "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False, indent=1)
    return donnees
