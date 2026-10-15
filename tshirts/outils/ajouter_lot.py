#!/usr/bin/env python3
"""Ajoute un lot de designs (outils/lots/lotNN.py) : designs.json, fiches, vidéos, prompts, statut Excel.

Usage : python3 outils/ajouter_lot.py outils/lots/lot01.py
Puis : python3 generate.py   (ne fabrique que les nouveaux)

Format d'une entrée du lot (liste LOT) :
  n, id, tshirt, icone, arc (haut, bas), centre, lignes, chute, titre, desc (3 phrases), cadeau,
  tags (13), style, ill (sujet du dessin en anglais ou None), attendre_ill (True = pas de design sans dessin),
  perso (None = daron), vids : 3 x (décor, action, légende, post).
Lignes : (texte, niveau, options) — niveau p/g/a = petit/grand/accent ; options : "i" icône après,
"b" bandeau pinceau, "d" illustration après.
"""
import json, os, runpy, sys, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NIV = {"p": "petit", "g": "grand", "a": "accent"}
COUL = {"noir": "black", "blanc": "white", "kaki": "khaki olive green", "marine": "navy blue",
        "sable": "sand beige", "gris": "heather grey"}
PERSO = {
    None: "a grumpy-looking French man in his early sixties, grey hair, glasses, cargo shorts",
    "mamie": "a French woman in her sixties with short grey hair and a no-nonsense attitude",
    "chantier": "a French construction worker in his forties, dusty work trousers and safety boots",
    "femme": "a French woman in her forties, ponytail, jeans",
    "soignante": "a French nurse in her thirties, hair tied back, scrub trousers",
    "homme": "a French man in his forties, short beard, work jeans",
}
STYLE_ILL = ("T-shirt print illustration, vintage cartoon mascot style with thick black outlines and flat "
             "limited colors (cream, mustard yellow, brick red, dark brown): {}. Isolated on plain white "
             "background, centered, no text, no lettering, clean screen-print look.")
CTA = "👉 Dispo en t-shirt sur la boutique (lien en bio)."
ENTRETIEN = ("T-shirt 100 % coton peigné, coupe unisexe, impression directe sur textile faite en France à la "
             "commande. Lavage à 30 °C sur l'envers, pas de sèche-linge, repassage sur l'envers.")


def check(e):
    pb = []
    for t in e.get("arc", ()):
        if len(t) > 25: pb.append(f"arc trop long : {t}")
    if len(e["titre"]) > 60: pb.append(f"titre {len(e['titre'])} car.")
    if len(e["tags"]) != 13: pb.append(f"{len(e['tags'])} tags")
    pb += [f"tag trop long : {t}" for t in e["tags"] if len(t) > 20]
    return pb


def icone(nom):
    """Télécharge l'icône si besoin ; renvoie False si elle n'existe pas chez Tabler."""
    p = os.path.join(ROOT, "icons", nom + ".svg")
    if not os.path.exists(p):
        url = f"https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/{nom}.svg"
        try:
            urllib.request.urlretrieve(url, p)
        except Exception:
            print(f"  icône introuvable : {nom} (design fait sans icône)")
            return False
    return True


def design(e):
    d = {"id": e["id"], "tshirt": e["tshirt"]}
    if e.get("icone") and icone(e["icone"]):
        d["icone"] = e["icone"]
    if e.get("arc"):
        d["arc_haut"], d["arc_bas"] = e["arc"]
    if e.get("centre"):
        d["centre"] = e["centre"]
    if e.get("titre_fiche"):
        d["titre"], d["liste"] = e["titre_fiche"], e["liste"]
    d["lignes"] = []
    for ln in e["lignes"]:
        txt, niv, opt = (ln + ("",))[:3]
        l = {"txt": txt, "niveau": NIV[niv]}
        if "i" in opt and "icone" in d: l["icone_apres"] = True
        if "b" in opt: l["bandeau"] = True
        if "d" in opt: l["illustration_apres"] = True
        d["lignes"].append(l)
    if e.get("chute"):
        d["chute"] = e["chute"]
    if e.get("styles"):
        d["styles"] = e["styles"]
    ill = os.path.join(ROOT, "illustrations", e["id"] + ".png")
    if e.get("ill") and os.path.exists(ill):
        d["illustration"] = e["id"] + ".png"
    return d


def ecrire(e):
    dos = os.path.join(ROOT, "sortie", e["id"]); os.makedirs(dos, exist_ok=True)
    tags = "\n".join(f"- {t}" for t in e["tags"])
    attente = "\n> ⚠️ Ce design attend son illustration (voir prompt-illustration.txt) : pas de version texte seul.\n" \
        if e.get("attendre_ill") else ""
    open(os.path.join(dos, "fiche-produit.md"), "w", encoding="utf-8").write(
        f"# {e['titre']}\n{attente}\n**Slogan n°{e['n']}** : {e['slogan']}\n\n## Description\n"
        f"{' '.join(e['desc'])}\n\nIdée cadeau pour {e['cadeau']}\n\n{ENTRETIEN}\n\n"
        f"## Tags Etsy (13)\n{tags}\n\n## Conseils\n- Couleur de t-shirt : **{e['tshirt']}**\n"
        f"- Style d'impression conseillé : **{e['style']}** (fichier `impression_{e['style']}.png`)\n"
        f"- Prix conseillé : **24,90 €** (29,90 € en sweat)\n")
    if e.get("ill") and not os.path.exists(os.path.join(ROOT, "illustrations", e["id"] + ".png")):
        open(os.path.join(dos, "prompt-illustration.txt"), "w", encoding="utf-8").write(
            STYLE_ILL.format(e["ill"]) + f"\n\n→ Dépose l'image dans illustrations/{e['id']}.png puis relance /tshirts.\n")
    who, col = PERSO[e.get("perso")], COUL[e["tshirt"]]
    out = [f"# Vidéos — {e['id']}\n\nT-shirt **{e['tshirt']}**, impression dans le dos. "
           f"Vidéos de 6 à 10 s, format vertical 9:16.\n"]
    for k, (decor, action, leg, post) in enumerate(e["vids"], 1):
        out.append(
            f"## Idée {k}\n\n**Prompt image**\n> Smartphone photo, natural daylight, vertical 9:16: {who}, seen from "
            f"behind (three-quarter back view), wearing a plain {col} t-shirt with the funny print clearly visible "
            f"on the back, {decor}. Everyday French setting, no logos, no brand names, no readable signs.\n\n"
            f"**Prompt vidéo**\n> Single slow movement, handheld camera: {action}. Natural light, realistic "
            f"smartphone footage, 8 seconds. The t-shirt print stays sharp and unchanged.\n\n"
            f"**Légende à incruster** : {leg}\n\n**Post Facebook**\n> {post}\n> {CTA}\n")
    open(os.path.join(dos, "video.md"), "w", encoding="utf-8").write("\n".join(out))


def statut(nums, valeur):
    from openpyxl import load_workbook
    p = os.path.join(ROOT, "banque-slogans.xlsx")
    wb = load_workbook(p); ws = wb["Slogans"]
    for row in ws.iter_rows(min_row=2):
        if row[0].value in nums:
            row[6].value = valeur
    wb.save(p)


def main():
    lot = runpy.run_path(sys.argv[1])["LOT"]
    pbs = {e["id"]: check(e) for e in lot}
    pbs = {k: v for k, v in pbs.items() if v}
    if pbs:
        sys.exit(f"À corriger : {pbs}")
    p = os.path.join(ROOT, "designs.json")
    designs = json.load(open(p, encoding="utf-8"))
    ids = {d["id"] for d in designs}
    for e in lot:
        ecrire(e)
        if e.get("existant"):
            continue  # déjà dans designs.json : on ne touche pas au design validé
        if e.get("attendre_ill") and not os.path.exists(os.path.join(ROOT, "illustrations", e["id"] + ".png")):
            continue  # pas de version texte seul
        d = design(e)
        if d["id"] in ids:
            designs = [d if x["id"] == d["id"] else x for x in designs]
        else:
            designs.append(d)
    json.dump(designs, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    statut({e["n"] for e in lot}, "Design fait")
    print(f"{len(lot)} designs ajoutés ({len(designs)} au total).")


if __name__ == "__main__":
    main()
