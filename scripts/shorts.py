"""npm run shorts <slug> : un Short vertical (1080×1920) par passage entre [SHORT début] et [SHORT fin].

Pour chaque Short : shorts/short-N.mp4 + shorts/short-N.txt (titre et description proposés).
"""
import json
import os
import re
import shutil
import subprocess
import sys

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from scripts.dossiers import script_md  # noqa: E402
from scripts.dossiers.scenes import MOTS_VIDES  # noqa: E402
from scripts.dossiers.script_md import normaliser  # noqa: E402
from scripts.video import navigateur  # noqa: E402

DUREE_MAX = 60_000


def segments(s):
    """[(premier mot, dernier mot + 1, morceaux)] pour chaque passage [SHORT début] … [SHORT fin]."""
    res, debut, dedans = [], None, []
    for m in s["morceaux"]:
        for b in m["balises"]:
            if b["type"] != "SHORT":
                continue
            if "deb" in normaliser(b["texte"]):
                debut = m["fin"] if b.get("apres") else m["debut"]
                dedans = []
            elif debut is not None:
                fin = m["fin"] if b.get("apres") else m["debut"]
                res.append((debut, fin, dedans + ([m] if b.get("apres") else [])))
                debut = None
        if debut is not None and m["debut"] >= debut:
            dedans.append(m)
    return res


def mot_cle(morceaux, tokens, debut):
    for m in morceaux:
        for b in m["balises"]:
            if b["type"] == "MOT":
                q = re.findall(r"[\"“«]\s*([^\"”»]+?)\s*[\"”»]", b["texte"])
                return (q[0] if q else b["texte"]).upper()
    mots = [t["brut"].strip(".,;:!?«»…") for t in tokens[debut:debut + 25]]
    pleins = [w for w in mots if normaliser(w) not in MOTS_VIDES and len(w) > 3]
    return (max(pleins, key=len) if pleins else mots[0]).upper()


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if not args:
        sys.exit("Indique le dossier, par exemple : npm run shorts castel")
    slug = args[0]
    dossier = os.path.join(RACINE, "videos", slug)
    s = script_md.lire(os.path.join(dossier, "script.md"))
    segs = segments(s)
    if not segs:
        sys.exit("Aucune balise [SHORT début] / [SHORT fin] dans le script : rien à faire.")
    plan_path = os.path.join(dossier, "scenes.json")
    if not os.path.exists(plan_path):
        sys.exit(f"Lance d'abord npm run video {slug}")
    plan = json.load(open(plan_path, encoding="utf-8"))
    fichier = plan["voix"].get("motsFichier") or ("voix-test.mots.json" if plan["voix"].get("test", True) else "voix.mots.json")
    mots = json.load(open(os.path.join(dossier, fichier), encoding="utf-8"))["mots"]
    sortie = os.path.join(dossier, "shorts")
    os.makedirs(sortie, exist_ok=True)
    subprocess.run(["node", os.path.join(RACINE, "scripts", "preparer-public.mjs")], check=True, cwd=RACINE)
    npx = shutil.which("npx") or "npx"
    if plan["voix"].get("test", True):
        print("ℹ️  Shorts en voix test (filigrane). Après « Ma voix est prête », relance-les pour la version finale.")

    for n, (a, b, morceaux) in enumerate(segs, 1):
        debut = max(0, mots[a]["debut"] - 250)
        fin = mots[b - 1]["fin"] + 700
        if fin - debut > DUREE_MAX:
            print(f"⚠️  Short {n} : {(fin - debut) / 1000:.0f} s, coupé à 60 s (raccourcis le passage dans le script).")
            fin = debut + DUREE_MAX
        cle = mot_cle(morceaux, s["tokens"], a)
        texte = " ".join(t["brut"] for t in s["tokens"][a:b])
        phrases = re.split(r"(?<=[.?!])\s", texte)
        premiere = next((p for p in phrases if len(p.split()) >= 5), phrases[0])
        titre = f"{cle.capitalize()} : {premiere}"[:95]
        with open(os.path.join(sortie, f"short-{n}.txt"), "w", encoding="utf-8") as f:
            f.write(f"TITRE PROPOSÉ :\n{titre} #shorts\n\nDESCRIPTION PROPOSÉE :\n{texte[:300]}…\n\n"
                    f"Le dossier complet est sur la chaîne DOSSIERS. #argent #enquete #business\n")
        props = json.dumps({"slug": slug, "debutMs": debut, "finMs": fin, "motCle": cle, "plan": None, "mots": None})
        print(f"\n━━ Short {n}/{len(segs)} : « {cle} » ({(fin - debut) / 1000:.0f} s)", flush=True)
        res = subprocess.run([npx, "remotion", "render", "src/index.ts", "Short", os.path.join(sortie, f"short-{n}.mp4"),
                              f"--props={props}", "--log=error"] + navigateur(), cwd=RACINE)
        if res.returncode:
            sys.exit("Le rendu du Short a échoué : copie le message d'erreur à Claude Code.")
    print(f"\n✅ {len(segs)} Short(s) dans videos/{slug}/shorts/ (avec titre et description dans les .txt)")


if __name__ == "__main__":
    main()
