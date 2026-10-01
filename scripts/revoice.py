"""npm run revoice <slug> : recale tout le montage sur TA voix (videos/<slug>/voix.mp3).

Option : --apercu (refait aussi l'aperçu 720p avec ta voix).
"""
import json
import os
import shutil
import subprocess
import sys
import wave

RACINE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RACINE)

from scripts.dossiers import revoix, scenes, script_md, voix  # noqa: E402


def etape(n, texte):
    print(f"\n━━ {n}. {texte}", flush=True)


def trouver_voix(dossier):
    for nom in ("voix.mp3", "voix.wav", "voix.m4a", "voix.aac", "voix.ogg"):
        p = os.path.join(dossier, nom)
        if os.path.exists(p):
            return p
    return None


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    options = {a for a in sys.argv[1:] if a.startswith("--")}
    if not args:
        sys.exit("Indique le dossier, par exemple : npm run revoice castel")
    slug = args[0]
    dossier = os.path.join(RACINE, "videos", slug)
    src = trouver_voix(dossier)
    if not src:
        sys.exit(f"Je ne trouve pas ta voix : dépose ton enregistrement sous le nom voix.mp3 dans videos/{slug}/")

    etape(1, "Lecture du script")
    s = script_md.lire(os.path.join(dossier, "script.md"))
    tokens = s["tokens"]

    etape(2, "Nettoyage de ta voix (volume, bruit de fond)")
    propre = os.path.join(dossier, "voix-propre.wav")
    revoix.nettoyer(src, propre)

    etape(3, "Transcription (Whisper)")
    entendus = revoix.transcrire(propre, os.path.join(dossier, "voix.transcription.json"))
    print(f"{len(entendus)} mots entendus pour {len(tokens)} mots dans le script.")

    etape(4, "Ratés, blancs et silences des cartons")
    jetes = revoix.reperer_rates(entendus, tokens)
    if jetes:
        print(f"{len(jetes)} mots retirés (prises ratées, on garde la dernière) :")
        bloc = []
        for k in sorted(jetes):
            bloc.append(entendus[k]["mot"])
            if k + 1 not in jetes:
                print(f"   ✂️  « {' '.join(bloc)} »")
                bloc = []
    gardes = [k for k in range(len(entendus)) if k not in jetes]
    entendus_gardes = [entendus[k] for k in gardes]
    lien, sm = revoix.aligner(tokens, entendus_gardes)
    # silences imposés par le script → avant quel mot entendu ?
    imposees = {}
    for i_tok, sec in s["pausesImposees"].items():
        i_tok = int(i_tok)
        if i_tok >= len(tokens):
            continue
        suivant = next((t for t in range(i_tok, len(tokens)) if t in lien), None)
        if suivant is not None:
            k = gardes[lien[suivant]]
            imposees[k] = max(imposees.get(k, 0), sec * 1000)
    fin = s["pausesImposees"].get(len(tokens), 3.0) * 1000
    ops, nouveaux = revoix.plan_de_montage(entendus, jetes, imposees, fin)
    pcm = revoix.lire_pcm(propre)
    sortie_pcm = revoix.assembler(pcm, ops)
    wav = os.path.join(dossier, "voix-calee.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(revoix.TAUX)
        w.writeframes(sortie_pcm)
    mp3 = os.path.join(dossier, "voix-calee.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-ar", "48000", "-b:a", "192k", mp3], check=True)
    os.remove(wav)
    duree = len(sortie_pcm) / 2 / revoix.TAUX * 1000
    print(f"Voix calée : {duree / 60000:.1f} min.")

    etape(5, "Ce qui diffère du script")
    lignes = revoix.rapport(tokens, entendus_gardes, lien, sm, s)
    with open(os.path.join(dossier, "rapport-voix.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n" if lignes else "Tout le script a été retrouvé dans ta voix.\n")
    if lignes:
        for l in lignes[:30]:
            print("   " + l)
        if len(lignes) > 30:
            print(f"   … et {len(lignes) - 30} autres (voir rapport-voix.txt)")
    else:
        print("Tout le script a été retrouvé dans ta voix. 👌")

    # horodatage de chaque mot du script sur la voix calée
    temps = [None] * len(tokens)
    for i_tok, i_ent in lien.items():
        temps[i_tok] = nouveaux[gardes[i_ent]]
    temps = voix._interpoler(tokens, temps, duree)
    mots = [{"i": t["i"], "mot": t["brut"], "debut": round(a), "fin": round(b)} for t, (a, b) in zip(tokens, temps)]
    nouvelle = {"moteur": "ta voix", "dureeMs": round(duree), "mots": mots}
    with open(os.path.join(dossier, "voix.mots.json"), "w", encoding="utf-8") as f:
        json.dump(nouvelle, f, ensure_ascii=False)

    etape(6, "Recalage du montage")
    chemin_plan = os.path.join(dossier, "scenes.json")
    if os.path.exists(chemin_plan):
        plan = json.load(open(chemin_plan, encoding="utf-8"))
        ancien_fichier = plan["voix"].get("motsFichier", "voix-test.mots.json")
        if ancien_fichier == "voix.mots.json":
            ancien_fichier = "voix.mots.precedent.json"
        anciens = json.load(open(os.path.join(dossier, ancien_fichier), encoding="utf-8"))["mots"]
        shutil.copy(chemin_plan, os.path.join(dossier, "scenes.avant-revoice.json"))
        plan = revoix.recaler(plan, anciens, mots)
        print("Mêmes visuels, mêmes animations : seuls les temps ont bougé.")
    else:
        plan = scenes.construire(s, nouvelle, dossier, slug, voix_test=False, fichier_voix="voix-calee.mp3")
    plan["voix"] = {"fichier": "voix-calee.mp3", "test": False, "moteur": "ta voix", "motsFichier": "voix.mots.json"}
    plan["dureeMs"] = round(duree)
    plan["parole"], plan["silences"] = revoix.parole_et_silences(mots)
    # la dernière scène va jusqu'au bout
    if plan["fond"]:
        plan["fond"][-1]["finMs"] = round(duree)
    with open(chemin_plan, "w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=1)
    shutil.copy(os.path.join(dossier, "voix.mots.json"), os.path.join(dossier, "voix.mots.precedent.json"))

    if "--apercu" in options:
        etape(7, "Aperçu avec ta voix")
        subprocess.run(["node", os.path.join(RACINE, "scripts", "preparer-public.mjs")], check=True, cwd=RACINE)
        props = json.dumps({"slug": slug, "apercu": True, "plan": None})
        npx = shutil.which("npx") or "npx"
        from scripts.video import navigateur
        subprocess.run([npx, "remotion", "render", "src/index.ts", "Video", os.path.join(dossier, "apercu.mp4"),
                        f"--props={props}", "--log=error"] + navigateur(), cwd=RACINE, check=True)
        print(f"Aperçu : videos/{slug}/apercu.mp4")

    print(f"\n✅ Montage recalé sur ta voix. Prochaine étape : npm run final {slug}")


if __name__ == "__main__":
    main()
