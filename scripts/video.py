"""npm run video <slug> : script.md → voix test → scènes → visuels auto → shotlist → aperçu 720p.

Options : --sans-rendu (tout sauf la vidéo), --hd (aperçu en 1080p), --voix (refait la voix test).
"""
import json
import os
import shutil
import subprocess
import sys
import time

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from scripts.dossiers import assets_auto, scenes, script_md, shotlist, voix  # noqa: E402


def etape(n, texte):
    print(f"\n━━ {n}. {texte}", flush=True)


def navigateur():
    """Navigateur pour le rendu : celui de Remotion par défaut, ou REMOTION_BROWSER s'il est défini."""
    if os.environ.get("REMOTION_BROWSER"):
        return ["--browser-executable", os.environ["REMOTION_BROWSER"]]
    for p in ("/opt/pw-browsers/chromium_headless_shell-1194/chrome-linux/headless_shell",):
        if os.path.exists(p):
            return ["--browser-executable", p]
    return []


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    options = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        sys.exit("Indique le nom du dossier vidéo, par exemple : npm run video castel")
    slug = args[0]
    dossier = os.path.join(RACINE, "videos", slug)
    if not os.path.exists(os.path.join(dossier, "script.md")):
        sys.exit(f"Je ne trouve pas videos/{slug}/script.md")
    debut = time.time()

    etape(1, "Lecture du script")
    s = script_md.lire(os.path.join(dossier, "script.md"))
    print(f"{len(s['tokens'])} mots, {len(s['morceaux'])} passages, {len(s['sections'])} parties.")

    chemin_plan = os.path.join(dossier, "scenes.json")
    sources = [os.path.join(dossier, n) for n in ("script.md", "a-chercher.md") if os.path.exists(os.path.join(dossier, n))]
    plan = json.load(open(chemin_plan, encoding="utf-8")) if os.path.exists(chemin_plan) else None
    a_jour = plan is not None and all(os.path.getmtime(f) <= os.path.getmtime(chemin_plan) for f in sources)
    sur_ta_voix = plan is not None and not plan["voix"].get("test", True)

    if a_jour and "--refaire" not in options and "--voix" not in options:
        etape(2, "Voix")
        print("Script inchangé : je garde le montage actuel"
              + (" (calé sur TA voix)." if sur_ta_voix else " (voix test)."))
        print("(Pour tout refaire quand même : npm run video " + slug + " -- --refaire)")
    else:
        if sur_ta_voix:
            print("ℹ️  Ton script a changé depuis ton enregistrement : nouvel aperçu en voix test.")
            print("   Quand tu auras réenregistré : « Ma voix est prête pour " + slug + " ».")
        etape(2, "Voix test")
        v = voix.fabriquer(s, dossier, forcer="--voix" in options)
        if v["moteur"] != "edge-tts":
            print("⚠️  Voix de secours utilisée (edge-tts injoignable). Vérifie ta connexion internet.")
        etape(3, "Découpage en scènes")
        plan = scenes.construire(s, v, dossier, slug, voix_test=True)
        plan["voix"]["motsFichier"] = "voix-test.mots.json"
        with open(chemin_plan, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=1)
    print(f"{len(plan['fond'])} scènes + {len(plan['calques'])} incrustations, durée {plan['dureeMs'] / 60000:.1f} min.")

    etape(4, "Recherche automatique des images et vidéos")
    r = assets_auto.chercher_tout(plan, dossier, RACINE)
    print(f"{r['trouves']} visuels trouvés sur {r['cherches']} manquants.")
    for c in r["manqueCles"]:
        print(f"🔑 Clé à ajouter dans le fichier .env : {c}")

    etape(5, "Shotlist, chapitres, crédits")
    sl = shotlist.generer(plan, s, dossier, slug)
    print(f"shotlist.html : {sl['aFournir']} visuels à fournir, {sl['auto']} trouvés automatiquement.")

    if "--sans-rendu" in options:
        print(f"\nTerminé en {time.time() - debut:.0f} s (sans rendu vidéo).")
        return
    etape(6, "Rendu de l'aperçu (ça peut prendre un moment)")
    subprocess.run(["node", os.path.join(RACINE, "scripts", "preparer-public.mjs")], check=True, cwd=RACINE)
    sortie = os.path.join(dossier, "apercu.mp4")
    props = json.dumps({"slug": slug, "apercu": "--hd" not in options, "plan": None})
    npx = shutil.which("npx") or "npx"
    cmd = [npx, "remotion", "render", "src/index.ts", "Video", sortie, f"--props={props}", "--log=error",
           "--image-format=jpeg", "--jpeg-quality=85"] + navigateur()
    res = subprocess.run(cmd, cwd=RACINE)
    if res.returncode:
        sys.exit("Le rendu a échoué : copie le message d'erreur à Claude Code.")
    print(f"\n✅ Aperçu prêt : videos/{slug}/apercu.mp4  ({time.time() - debut:.0f} s)")
    print(f"   Shotlist   : videos/{slug}/shotlist.html")
    print("   Pour regarder et retoucher en direct : npm run studio")


if __name__ == "__main__":
    main()
