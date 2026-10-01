"""Lecture de script.md : texte à lire, balises, pauses, sections.

Modèle :
- tokens  : chaque mot prononcé, numéroté (i). Tout le reste du pipeline s'ancre sur ces numéros,
            ce qui permet de recaler le montage sur n'importe quelle voix (test ou vraie).
- morceaux: un bout de texte d'une ligne + les balises qui l'illustrent.
  Une balise placée APRÈS un texte illustre ce texte ; placée en début de ligne (ou seule sur sa
  ligne), elle illustre le texte qui suit.
"""
import re
import unicodedata

RE_BALISE = re.compile(r"\[([^\]]+)\]")
RE_PAUSE = re.compile(r"^PAUSE\s*([\d.,]+)\s*s$", re.IGNORECASE)

# Silences ajoutés au montage (en secondes)
SILENCE_POINTS = 0.55      # « … »
CARTON_PIECE = 2.8         # carton « PIÈCE N°X » : la voix s'arrête pendant le tampon
OUVERTURE = 3.4            # chemise « DOSSIER N°00X » avant la première phrase
FIN = 3.0                  # après la dernière phrase

RE_SECTION = re.compile(r"^(HOOK|PROMESSE|PIECE|CONCLUSION|INTRO|OUTRO|ACTE|PARTIE|CHAPITRE|SEGMENT|TEASER)")

TYPES = [  # du plus long au plus court pour reconnaître « IMAGE IA » avant « IMAGE »
    "OUVERTURE DOSSIER", "IMAGE IA", "VIDEO IA", "PHOTO", "VIDEO", "IMAGE", "MOT", "CHIFFRE", "COMPTEUR",
    "FICHE", "CARTE", "GRAPH", "DOCUMENT", "TABLEAU", "TIMELINE", "PIECE", "CITATION", "SCHEMA",
    "TAMPON", "TEASER", "SHORT",
]


def sans_accents(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def normaliser(mot: str) -> str:
    """« s'appelle » → « appelle » ; « Jésus-là » → « jesusla » ; garde chiffres et lettres."""
    m = mot.lower().replace("’", "'")
    return re.sub(r"[^a-z0-9]", "", sans_accents(m))


def lire_balise(brut: str) -> dict:
    s = brut.strip()
    cle = sans_accents(s).upper()
    for t in TYPES:
        if cle.startswith(t) and (len(cle) == len(t) or not cle[len(t)].isalpha()):
            reste = s[len(t):].strip(" :,-")
            return {"type": t.replace(" ", "_"), "texte": reste, "brut": s}
    return {"type": "INCONNU", "texte": s, "brut": s}


def lire(chemin: str) -> dict:
    lignes = open(chemin, encoding="utf-8").read().splitlines()
    tokens, morceaux, sections = [], [], []
    pauses = {}            # pauses[k] = secondes de silence AVANT le token k
    en_attente = []        # balises qui illustreront le prochain texte
    meta = {"numero": None, "titre": "", "sujet": "", "sousTitre": ""}
    section = None  # tout ce qui précède le premier « ## » (titres, miniature…) n'est pas lu

    def ajouter_pause(k, s):
        pauses[k] = round(pauses.get(k, 0) + s, 2)

    for ligne in lignes:
        l = ligne.strip()
        if l.startswith("# "):
            m = re.search(r"N°\s*(\d+)", l)
            if m:
                meta["numero"] = int(m.group(1))
            meta["titre"] = re.sub(r"^#\s*", "", l)
            meta["sujet"] = re.split(r"\s[—–-]\s", meta["titre"], maxsplit=1)[-1].strip()
            continue
        if l.startswith("## "):
            titre = re.sub(r"\(\d+:\d+.*?\)\s*$", "", l[3:]).strip()
            cle = sans_accents(titre).upper()
            if cle.startswith("SOURCES"):
                break
            if RE_SECTION.match(cle):
                section = titre
                sections.append({"nom": titre, "debut": len(tokens)})
            else:
                section = None  # sous-titre, notes… : pas lu
                if not sections and re.match(r"^[«\"“]", titre):
                    meta["sousTitre"] = titre.strip("«»\"“” ")
            continue
        if section is None or not l or l.startswith((">", "⚠", "**", "---", "(", "|", "- ")):
            continue

        # découpe la ligne en [texte, balise, texte, balise, ...]
        pos = 0
        elements = []
        for m in RE_BALISE.finditer(l):
            if m.start() > pos:
                elements.append(("texte", l[pos:m.start()]))
            elements.append(("balise", m.group(1)))
            pos = m.end()
        if pos < len(l):
            elements.append(("texte", l[pos:]))

        dernier = None  # dernier morceau de texte de la ligne
        for genre, valeur in elements:
            if genre == "balise":
                p = RE_PAUSE.match(valeur.strip())
                if p:
                    ajouter_pause(len(tokens), float(p.group(1).replace(",", ".")))
                    continue
                b = lire_balise(valeur)
                if b["type"] == "PIECE":
                    ajouter_pause(len(tokens), CARTON_PIECE)
                if b["type"] == "OUVERTURE_DOSSIER":
                    ajouter_pause(len(tokens), OUVERTURE)
                if dernier is not None and b["type"] not in ("PIECE", "OUVERTURE_DOSSIER"):
                    dernier["balises"].append(b)
                else:
                    en_attente.append(b)
                continue
            texte = valeur.strip()
            if not re.search(r"\w", texte):
                continue
            debut = len(tokens)
            for brut in texte.split():
                if "…" in brut or "..." in brut:
                    avant, _, apres = brut.replace("...", "…").partition("…")
                    if re.search(r"\w", avant):
                        tokens.append({"i": len(tokens), "brut": avant + "…", "mot": normaliser(avant)})
                    ajouter_pause(len(tokens), SILENCE_POINTS)
                    if re.search(r"\w", apres):
                        tokens.append({"i": len(tokens), "brut": apres, "mot": normaliser(apres)})
                    continue
                if not re.search(r"\w", brut):
                    if tokens:
                        tokens[-1]["brut"] += " " + brut  # « ? », « — » restent collés au mot précédent
                    continue
                tokens.append({"i": len(tokens), "brut": brut, "mot": normaliser(brut)})
            if len(tokens) == debut:
                continue
            dernier = {"debut": debut, "fin": len(tokens), "section": section, "balises": en_attente, "ligne": texte}
            en_attente = []
            morceaux.append(dernier)

    if en_attente and morceaux:
        morceaux[-1]["balises"].extend(en_attente)
    ajouter_pause(len(tokens), FIN)
    for m in morceaux:
        m["texte"] = " ".join(t["brut"] for t in tokens[m["debut"]:m["fin"]])
    return {"meta": meta, "tokens": tokens, "morceaux": morceaux, "pauses": pauses, "sections": sections}


if __name__ == "__main__":
    import json
    import sys
    d = lire(sys.argv[1])
    print(len(d["tokens"]), "mots,", len(d["morceaux"]), "morceaux,", len(d["sections"]), "sections")
    for m in d["morceaux"][:12]:
        print(m["debut"], m["texte"][:70], [b["type"] + ":" + b["texte"][:25] for b in m["balises"]])
    print(json.dumps({k: v for k, v in list(d["pauses"].items())[:10]}))
