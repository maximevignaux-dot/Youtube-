"""npm run final <slug> : rendu 1080p sans filigrane + crédits + chapitres + 3 miniatures.

Bloque si un visuel manque ou si la licence d'un visuel est inconnue.
"""
import json
import os
import shutil
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from scripts.dossiers import decoupes, script_md, shotlist  # noqa: E402
from scripts.dossiers.assets_auto import fichier_existant  # noqa: E402
from scripts.video import navigateur  # noqa: E402

ENTETE_SOURCES = """# Sources de TES fichiers (ceux que tu as déposés toi-même dans assets/)
# Une ligne par fichier :  ID | où tu l'as eu | auteur | licence
# Exemples :
#   V01 | Pexels | Jean Dupont | Licence Pexels
#   P02 | Wikimedia Commons | Inconnu | CC BY-SA 4.0
#   V08 | Mes rushs (drone) | Maxime | personnel
#   I01 | Midjourney | Maxime | image IA générée
"""


def etape(n, texte):
    print(f"\n━━ {n}. {texte}", flush=True)


def lire_sources(chemin):
    sources = {}
    if os.path.exists(chemin):
        for l in open(chemin, encoding="utf-8"):
            if l.strip().startswith("#") or "|" not in l:
                continue
            c = [x.strip() for x in l.split("|")]
            if len(c) >= 4 and c[0]:
                sources[c[0]] = {"source": c[1], "auteur": c[2], "licence": c[3]}
    return sources


def controler(plan, dossier):
    """Renvoie (manquants, sans_licence)."""
    assets_dir = os.path.join(dossier, "assets")
    credits_auto = {}
    p = os.path.join(assets_dir, "auto", "credits.json")
    if os.path.exists(p):
        credits_auto = json.load(open(p, encoding="utf-8"))
    sources = lire_sources(os.path.join(assets_dir, "sources.txt"))
    manquants, sans_licence, vus = [], [], set()
    for e in plan["fond"]:
        a = e.get("asset")
        if not a or a["id"] in vus:
            continue
        vus.add(a["id"])
        f = fichier_existant(assets_dir, a["id"])
        if not f:
            manquants.append(a)
            continue
        if os.sep + "auto" + os.sep in f:
            ok = a["id"] in credits_auto
        else:
            src = sources.get(a["id"], {})
            ok = bool(src.get("licence")) and src["licence"] not in ("?", "inconnu", "inconnue")
        if not ok:
            sans_licence.append(a)
    return manquants, sans_licence, sources


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    options = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        sys.exit("Indique le dossier, par exemple : npm run final castel")
    slug = args[0]
    dossier = os.path.join(RACINE, "videos", slug)
    chemin_plan = os.path.join(dossier, "scenes.json")
    if not os.path.exists(chemin_plan):
        sys.exit(f"Pas encore de montage : lance d'abord npm run video {slug}")
    plan = json.load(open(chemin_plan, encoding="utf-8"))
    debut = time.time()

    etape(1, "Vérifications")
    if plan["voix"].get("test", True) and "--sans-controle" not in options:
        sys.exit("⛔ Le montage est encore sur la voix test. Dépose voix.mp3 dans le dossier puis : npm run revoice " + slug)
    manquants, sans_licence, sources = controler(plan, dossier)
    chemin_sources = os.path.join(dossier, "assets", "sources.txt")
    if sans_licence:
        # prépare les lignes à compléter dans sources.txt
        existant = open(chemin_sources, encoding="utf-8").read() if os.path.exists(chemin_sources) else ENTETE_SOURCES
        ajout = "".join(f"{a['id']} | ? | ? | ?\n" for a in sans_licence if a["id"] not in sources)
        with open(chemin_sources, "w", encoding="utf-8") as f:
            f.write(existant + ajout)
    if manquants or sans_licence:
        if manquants:
            print(f"⛔ {len(manquants)} visuels manquent encore (voir shotlist.html) : "
                  + ", ".join(a["id"] for a in manquants[:25]) + (" …" if len(manquants) > 25 else ""))
        if sans_licence:
            print(f"⛔ {len(sans_licence)} fichiers sans licence connue : " + ", ".join(a["id"] for a in sans_licence[:25]))
            print(f"   → complète videos/{slug}/assets/sources.txt (une ligne par fichier, les « ? » sont à remplacer).")
        if "--sans-controle" not in options:
            sys.exit("Rendu final bloqué tant que ce n'est pas réglé (l'aperçu, lui, marche toujours).")
        print("⚠️  --sans-controle : rendu forcé malgré tout (À NE PAS PUBLIER).")
    else:
        print("Tous les visuels sont là et leurs licences sont connues. ✔")

    etape(2, "Détourage des photos (effet 2,5D, miniatures)")
    decoupes.detourer(plan, dossier)

    etape(3, "Crédits, chapitres")
    s = script_md.lire(os.path.join(dossier, "script.md"))
    shotlist.generer(plan, s, dossier, slug)
    # crédits : fichiers auto + tes sources
    with open(os.path.join(dossier, "credits.txt"), "a", encoding="utf-8") as f:
        for ident, c in sorted(lire_sources(chemin_sources).items()):
            if c["licence"] not in ("?", "personnel") and "IA" not in c["licence"]:
                f.write(f"- {c['source']} — {c['auteur']} — {c['licence']}\n")
    print(open(os.path.join(dossier, "chapitres.txt"), encoding="utf-8").read().strip())

    subprocess.run(["node", os.path.join(RACINE, "scripts", "preparer-public.mjs")], check=True, cwd=RACINE)
    npx = shutil.which("npx") or "npx"
    etape(4, "Miniatures (3 variantes)")
    for v in (1, 2, 3):
        props = json.dumps({"slug": slug, "variante": v, "infos": None})
        subprocess.run([npx, "remotion", "still", "src/index.ts", "Miniature", os.path.join(dossier, f"miniature-{v}.jpg"),
                        f"--props={props}", "--log=error", "--jpeg-quality=92"] + navigateur(), cwd=RACINE, check=True)
    print("miniature-1.jpg, miniature-2.jpg, miniature-3.jpg")

    etape(5, "Rendu final 1080p (compte 20 à 40 min)")
    sortie = os.path.join(dossier, "sortie.mp4")
    props = json.dumps({"slug": slug, "apercu": False, "plan": None})
    extrait = [f"--frames={o.split('=', 1)[1]}" for o in options if o.startswith("--extrait=")]  # pour les tests
    res = subprocess.run([npx, "remotion", "render", "src/index.ts", "Video", sortie, f"--props={props}", "--log=error",
                          "--crf=18", "--audio-bitrate=320k"] + extrait + navigateur(), cwd=RACINE)
    if res.returncode:
        sys.exit("Le rendu a échoué : copie le message d'erreur à Claude Code.")
    print(f"\n✅ Vidéo finale : videos/{slug}/sortie.mp4  ({(time.time() - debut) / 60:.0f} min)")
    print(f"   À coller sur YouTube : videos/{slug}/chapitres.txt et videos/{slug}/credits.txt")
    print(f"   Miniatures à tester : videos/{slug}/miniature-1.jpg, -2, -3")


if __name__ == "__main__":
    main()
