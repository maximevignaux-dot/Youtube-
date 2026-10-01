"""Voix test : fabrique voix-test.mp3 + l'horodatage de CHAQUE mot du script.

Moteurs, dans l'ordre :
  1. edge-tts (voix Microsoft « Henri », naturelle, gratuite, besoin d'internet)
  2. MBROLA fr1 via espeak-ng (hors-ligne, voix masculine correcte)
  3. espeak-ng (hors-ligne, robotique)
"""
import asyncio
import difflib
import hashlib
import json
import os
import re
import shutil
import ssl
import subprocess
import tempfile
import wave

from .script_md import normaliser

VOIX_EDGE = "fr-FR-HenriNeural"
DEBIT_EDGE = "+8%"
DEBIT_ESPEAK = 150          # mots / minute (175 par défaut : trop rapide)
TAUX = 24000                # échantillonnage de travail
PAUSE_PHRASE = 0.30         # silence ajouté après . ? ! (moteurs hors-ligne)
PAUSE_VIRGULE = 0.12


def _moteurs_dispo():
    m = []
    try:
        import edge_tts  # noqa: F401
        m.append("edge-tts")
    except ImportError:
        pass
    if shutil.which("espeak-ng"):
        if os.path.exists("/usr/share/mbrola/fr1") or os.path.exists("/usr/share/mbrola/fr1/fr1"):
            m.append("mbrola")
        m.append("espeak-ng")
    return m


# ---------------------------------------------------------------- moteurs
async def _edge(texte, chemin_mp3):
    import edge_tts
    import edge_tts.communicate as comm
    ca = os.environ.get("SSL_CERT_FILE")
    if ca and os.path.exists(ca):
        comm._SSL_CTX = ssl.create_default_context(cafile=ca)
    c = edge_tts.Communicate(texte, VOIX_EDGE, rate=DEBIT_EDGE, boundary="WordBoundary")
    limites = []
    with open(chemin_mp3, "wb") as f:
        async for b in c.stream():
            if b["type"] == "audio":
                f.write(b["data"])
            elif b["type"] == "WordBoundary":
                d = b["offset"] / 10_000
                limites.append((b["text"], d, d + b["duration"] / 10_000))
    return limites


def _vers_pcm(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-ar", str(TAUX), "-ac", "1", "-sample_fmt", "s16", dst],
                   check=True)


def _espeak(texte, chemin_wav, voix):
    brut = chemin_wav + ".brut.wav"
    subprocess.run(["espeak-ng", "-v", voix, "-s", str(DEBIT_ESPEAK), "-w", brut, texte], check=True,
                   stderr=subprocess.DEVNULL)
    # retire les silences de début/fin pour des horodatages plus justes
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", brut, "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
                    "-ar", str(TAUX), "-ac", "1", "-sample_fmt", "s16", chemin_wav], check=True)


def _lire_pcm(chemin):
    with wave.open(chemin) as w:
        return w.readframes(w.getnframes())


# ---------------------------------------------------------------- découpage
def _blocs(tokens, pauses, fin_phrase_separee):
    """Coupe le texte en blocs lus d'une traite. Renvoie [(silence_avant_s, [tokens])]."""
    blocs, courant, silence = [], [], 0.0
    for t in tokens:
        p = pauses.get(str(t["i"]), pauses.get(t["i"], 0))
        if p and courant:
            blocs.append((silence, courant))
            courant, silence = [], 0.0
        silence += p
        courant.append(t)
        if fin_phrase_separee:
            if re.search(r"[.?!]\W*$", t["brut"]):
                blocs.append((silence, courant))
                courant, silence = [], PAUSE_PHRASE
            elif re.search(r"[,;:]\W*$", t["brut"]):
                blocs.append((silence, courant))
                courant, silence = [], PAUSE_VIRGULE
    if courant:
        blocs.append((silence, courant))
    return blocs


def _texte_tts(toks):
    t = " ".join(x["brut"] for x in toks)
    return re.sub(r"[«»“”—]", " ", t).replace("…", "").strip()


def _caler(toks, limites, duree_ms):
    """Associe chaque mot du script à un mot entendu (edge-tts) ; les autres sont interpolés."""
    a = [t["mot"] for t in toks]
    b = [normaliser(x[0]) for x in limites]
    temps = [None] * len(toks)
    for bloc in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(bloc.size):
            temps[bloc.a + k] = (limites[bloc.b + k][1], limites[bloc.b + k][2])
    return _interpoler(toks, temps, duree_ms)


def _estimer(toks, duree_ms):
    poids = [len(t["mot"]) + 2 for t in toks]
    total, acc, temps = sum(poids), 0.0, []
    for w in poids:
        d = duree_ms * w / total
        temps.append((acc, acc + d * 0.9))
        acc += d
    return temps


def _interpoler(toks, temps, duree_ms):
    connus = [k for k, x in enumerate(temps) if x]
    if not connus:
        return _estimer(toks, duree_ms)
    for k in range(len(temps)):
        if temps[k]:
            continue
        avant = max([c for c in connus if c < k], default=None)
        apres = min([c for c in connus if c > k], default=None)
        t0 = temps[avant][1] if avant is not None else 0
        t1 = temps[apres][0] if apres is not None else duree_ms
        a = avant if avant is not None else -1
        b = apres if apres is not None else len(temps)
        pas = (t1 - t0) / (b - a)
        temps[k] = (t0 + pas * (k - a - 1), t0 + pas * (k - a))
    return temps


# ---------------------------------------------------------------- principal
def signature(script, moteur):
    h = hashlib.sha1()
    h.update(json.dumps([[t["brut"] for t in script["tokens"]], script["pauses"], moteur, DEBIT_EDGE,
                         DEBIT_ESPEAK]).encode())
    return h.hexdigest()[:16]


def fabriquer(script, dossier, forcer=False, journal=print):
    os.makedirs(dossier, exist_ok=True)
    sortie_json = os.path.join(dossier, "voix-test.mots.json")
    sortie_mp3 = os.path.join(dossier, "voix-test.mp3")
    moteurs = _moteurs_dispo()
    if not moteurs:
        raise SystemExit("Aucun moteur de voix : installe edge-tts (pip install edge-tts).")

    # déjà fait avec le même texte ? on ne refait pas
    if not forcer and os.path.exists(sortie_json) and os.path.exists(sortie_mp3):
        ancien = json.load(open(sortie_json, encoding="utf-8"))
        if ancien.get("signature") == signature(script, ancien.get("moteur")):
            journal(f"Voix test déjà à jour ({ancien['moteur']}).")
            return ancien

    tmp = tempfile.mkdtemp()
    for moteur in moteurs:
        try:
            res = _generer(script, moteur, tmp, journal)
            break
        except Exception as err:  # réseau coupé, Microsoft refuse…
            journal(f"⚠️  {moteur} indisponible ({type(err).__name__}) → moteur suivant.")
    else:
        raise SystemExit("Impossible de fabriquer la voix test.")

    pcm, mots, moteur = res
    wav = os.path.join(tmp, "voix.wav")
    with wave.open(wav, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(TAUX)
        w.writeframes(pcm)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-af", "loudnorm=I=-16:TP=-1.5",
                    "-ar", "44100", "-b:a", "160k", sortie_mp3], check=True)
    duree = len(pcm) / 2 / TAUX * 1000
    donnees = {"moteur": moteur, "signature": signature(script, moteur), "dureeMs": round(duree), "mots": mots}
    with open(sortie_json, "w", encoding="utf-8") as f:
        json.dump(donnees, f, ensure_ascii=False)
    journal(f"Voix test : {duree / 60000:.1f} min, moteur {moteur}.")
    return donnees


def _generer(script, moteur, tmp, journal):
    hors_ligne = moteur != "edge-tts"
    blocs = _blocs(script["tokens"], script["pauses"], fin_phrase_separee=hors_ligne)
    pcm, mots, t_ms = bytearray(), [], 0.0
    for n, (silence, toks) in enumerate(blocs):
        if silence:
            nb = int(silence * TAUX)
            pcm += b"\x00\x00" * nb
            t_ms += nb / TAUX * 1000
        wav = os.path.join(tmp, f"{n:05d}.wav")
        texte = _texte_tts(toks)
        if moteur == "edge-tts":
            mp3 = wav.replace(".wav", ".mp3")
            limites = asyncio.run(_edge(texte, mp3))
            _vers_pcm(mp3, wav)
        else:
            _espeak(texte, wav, "mb-fr1" if moteur == "mbrola" else "fr-fr")
            limites = None
        donnees = _lire_pcm(wav)
        d_ms = len(donnees) / 2 / TAUX * 1000
        temps = _caler(toks, limites, d_ms) if limites else _estimer(toks, d_ms)
        for t, (a, b) in zip(toks, temps):
            mots.append({"i": t["i"], "mot": t["brut"], "debut": round(t_ms + a), "fin": round(t_ms + b)})
        pcm += donnees
        t_ms += d_ms
        if n % 50 == 0:
            journal(f"   voix : {n}/{len(blocs)} blocs")
    # silence final (pause « FIN » placée après le dernier mot)
    fin = script["pauses"].get(str(len(script["tokens"])), script["pauses"].get(len(script["tokens"]), 0))
    pcm += b"\x00\x00" * int(fin * TAUX)
    return pcm, mots, moteur
