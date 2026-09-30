"""Voix test : transforme un texte en voix-test.mp3 + horodatages au mot (edge-tts).

Usage : python3 scripts/voix_test.py <script.md | texte.txt> <dossier_sortie> [--section HOOK]

- Les « … » deviennent un silence de 0,6 s, [PAUSE 1s] un silence de la durée indiquée.
- Sortie : voix-test.mp3 et voix-test.mots.json ([{mot, debut, fin}] en millisecondes).
"""
import asyncio
import json
import os
import re
import ssl
import subprocess
import sys
import tempfile

import edge_tts
import edge_tts.communicate as _comm

VOIX = "fr-FR-HenriNeural"
DEBIT = "+8%"
SILENCE_POINTS = 0.6  # secondes pour « … »

# Certains réseaux (proxy d'entreprise, conteneur cloud) utilisent leur propre certificat.
_ca = os.environ.get("SSL_CERT_FILE")
if _ca and os.path.exists(_ca):
    _comm._SSL_CTX = ssl.create_default_context(cafile=_ca)


def texte_a_lire(brut: str, section: str | None = None) -> str:
    """Garde seulement ce qui doit être lu à voix haute.
    Retire titres (#), consignes (> et ⚠️), et toutes les balises [ … ] sauf [PAUSE …]."""
    lignes, dedans = [], section is None
    for ligne in brut.splitlines():
        l = ligne.strip()
        if l.startswith("#"):
            if section is not None:
                dedans = section.lower() in l.lower()
            continue
        if not dedans or not l or l.startswith(">") or l.startswith("⚠️") or l.startswith("("):
            continue
        l = re.sub(r"\[(?!PAUSE)[^\]]*\]", "", l, flags=re.IGNORECASE)
        lignes.append(re.sub(r"\s+", " ", l).strip())
    return "\n".join(x for x in lignes if x)


def decouper(texte: str):
    """Renvoie une liste de ('texte', str) et ('silence', secondes)."""
    morceaux = []
    motif = re.compile(r"\[PAUSE\s*([\d.,]+)\s*s\]|…|\.\.\.", re.IGNORECASE)
    pos = 0
    for m in motif.finditer(texte):
        avant = texte[pos:m.start()].strip()
        if avant:
            morceaux.append(("texte", avant))
        duree = float(m.group(1).replace(",", ".")) if m.group(1) else SILENCE_POINTS
        morceaux.append(("silence", duree))
        pos = m.end()
    reste = texte[pos:].strip()
    if reste:
        morceaux.append(("texte", reste))
    return morceaux


def synthese_secours(texte: str, chemin: str):
    """Voix de secours hors-ligne (espeak-ng) si edge-tts est injoignable.
    Horodatages estimés au prorata des lettres : suffisant pour un aperçu."""
    wav = chemin + ".wav"
    subprocess.run(["espeak-ng", "-v", "fr-fr", "-s", "175", "-w", wav, texte], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, chemin], check=True)
    total = duree_ms(chemin)
    brut = [m for m in texte.split() if re.search(r"\w", m)]
    poids = [len(m) + 2 for m in brut]
    somme, t, mots = sum(poids), 0.0, []
    for mot, w in zip(brut, poids):
        d = total * w / somme
        mots.append({"mot": mot.strip(".,;:!?«»\"()"), "debut": t, "fin": t + d * 0.85})
        t += d
    return mots


MOTEUR = {"nom": "edge-tts"}


async def synthese(texte: str, chemin: str):
    if MOTEUR["nom"] == "espeak-ng":
        return synthese_secours(texte, chemin)
    try:
        return await synthese_edge(texte, chemin)
    except Exception as err:  # réseau coupé, Microsoft refuse, etc.
        print(f"⚠️  edge-tts indisponible ({type(err).__name__}) → voix de secours espeak-ng (robotique).")
        MOTEUR["nom"] = "espeak-ng"
        return synthese_secours(texte, chemin)


async def synthese_edge(texte: str, chemin: str):
    com = edge_tts.Communicate(texte, VOIX, rate=DEBIT, boundary="WordBoundary")
    mots = []
    with open(chemin, "wb") as f:
        async for bloc in com.stream():
            if bloc["type"] == "audio":
                f.write(bloc["data"])
            elif bloc["type"] == "WordBoundary":
                debut = bloc["offset"] / 10_000  # unités de 100 ns → ms
                mots.append({"mot": bloc["text"], "debut": debut, "fin": debut + bloc["duration"] / 10_000})
    return mots


def duree_ms(chemin: str) -> float:
    sortie = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", chemin,
    ])
    return float(sortie.strip()) * 1000


async def main(fichier_texte: str, dossier: str, section: str | None = None):
    texte = texte_a_lire(open(fichier_texte, encoding="utf-8").read(), section)
    os.makedirs(dossier, exist_ok=True)
    tmp = tempfile.mkdtemp()
    pistes, mots, t = [], [], 0.0
    for i, (genre, valeur) in enumerate(decouper(texte)):
        chemin = os.path.join(tmp, f"{i:04d}.wav")
        if genre == "silence":
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
                            "-t", str(valeur), chemin], check=True)
        else:
            mp3 = chemin.replace(".wav", ".mp3")
            for m in await synthese(valeur, mp3):
                mots.append({"mot": m["mot"], "debut": round(t + m["debut"]), "fin": round(t + m["fin"])})
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", mp3, "-ar", "24000", "-ac", "1", chemin], check=True)
        t += duree_ms(chemin)
        pistes.append(chemin)
    liste = os.path.join(tmp, "liste.txt")
    with open(liste, "w") as f:
        f.writelines(f"file '{p}'\n" for p in pistes)
    sortie = os.path.join(dossier, "voix-test.mp3")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", liste,
                    "-ar", "44100", "-b:a", "192k", sortie], check=True)
    with open(os.path.join(dossier, "voix-test.mots.json"), "w", encoding="utf-8") as f:
        json.dump({"moteur": MOTEUR["nom"], "dureeMs": round(t), "mots": mots}, f, ensure_ascii=False, indent=1)
    print(f"OK : {sortie} ({t/1000:.1f} s, {len(mots)} mots)")


if __name__ == "__main__":
    args = sys.argv[1:]
    section = None
    if "--section" in args:
        i = args.index("--section")
        section = args[i + 1]
        del args[i:i + 2]
    if len(args) != 2:
        sys.exit(__doc__)
    asyncio.run(main(args[0], args[1], section))
