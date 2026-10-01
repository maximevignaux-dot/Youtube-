"""Passage à la vraie voix : voix.mp3 → voix-calee.mp3 + montage recalé.

1. Nettoyage : volume normalisé, bruit de fond grave coupé.
2. Transcription Whisper avec l'heure de chaque mot (mise en cache : on ne la refait pas).
3. Ratés : quand Maxime marque une pause et reprend la même phrase, on garde la DERNIÈRE prise.
4. Blancs trop longs raccourcis ; silences imposés par le script ajoutés (cartons de pièce, [PAUSE]).
5. Chaque mot du script est retrouvé dans la voix → le montage existant est recalé
   (mêmes visuels, mêmes animations, seuls les temps bougent).
6. Rapport : phrases sautées / changées / ajoutées.
"""
import difflib
import hashlib
import json
import os
import re
import subprocess
import wave

from .script_md import normaliser

TAUX = 48000
PAUSE_RATE = 650          # ms : une pause au moins aussi longue peut annoncer une reprise
BLANC_MAX = 1300          # ms : au-delà, un blanc est raccourci…
BLANC_CIBLE = 650         # … à cette durée
MARGE = 60                # ms gardées autour des mots coupés


# ---------------------------------------------------------------- audio
def nettoyer(src, dst):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-af",
                    "highpass=f=70,afftdn=nf=-25,loudnorm=I=-16:TP=-1.5:LRA=11",
                    "-ar", str(TAUX), "-ac", "1", "-sample_fmt", "s16", dst], check=True)


def lire_pcm(chemin):
    with wave.open(chemin) as w:
        return w.readframes(w.getnframes())


def octets(ms):
    return int(ms * TAUX / 1000) * 2


# ---------------------------------------------------------------- transcription
def empreinte(chemin):
    h = hashlib.sha1()
    with open(chemin, "rb") as f:
        for bloc in iter(lambda: f.read(1 << 20), b""):
            h.update(bloc)
    return h.hexdigest()[:16]


def transcrire(wav, cache, journal=print):
    cle = empreinte(wav)
    if os.path.exists(cache):
        d = json.load(open(cache, encoding="utf-8"))
        if d.get("empreinte") == cle:
            journal("Transcription déjà faite (cache).")
            return d["mots"]
    modele = os.environ.get("WHISPER_MODELE", "small")
    mots = []
    try:
        from faster_whisper import WhisperModel
        journal(f"Transcription avec faster-whisper ({modele}) : quelques minutes…")
        m = WhisperModel(modele, device="cpu", compute_type="int8")
        segments, _ = m.transcribe(wav, language="fr", word_timestamps=True, vad_filter=False)
        for seg in segments:
            for w in seg.words or []:
                mots.append({"mot": w.word.strip(), "debut": round(w.start * 1000), "fin": round(w.end * 1000)})
    except ImportError:
        try:
            import whisper
        except ImportError:
            raise SystemExit("Whisper n'est pas installé. Tape : pip install faster-whisper")
        journal(f"Transcription avec whisper ({modele}) : quelques minutes…")
        r = whisper.load_model(modele).transcribe(wav, language="fr", word_timestamps=True)
        for seg in r["segments"]:
            for w in seg.get("words", []):
                mots.append({"mot": w["word"].strip(), "debut": round(w["start"] * 1000), "fin": round(w["end"] * 1000)})
    mots = [m for m in mots if normaliser(m["mot"])]
    with open(cache, "w", encoding="utf-8") as f:
        json.dump({"empreinte": cle, "modele": modele, "mots": mots}, f, ensure_ascii=False)
    return mots


# ---------------------------------------------------------------- ratés et blancs
def reperer_rates(mots, tokens_script=None):
    """Renvoie les indices des mots à jeter : une prise abandonnée puis reprise après une pause.
    Une répétition voulue (présente deux fois dans le script) n'est pas un raté."""
    norm = [normaliser(m["mot"]) for m in mots]
    script = [t["mot"] for t in tokens_script] if tokens_script else []

    def compte(seq, motif):
        return sum(1 for k in range(len(seq) - 2) if seq[k:k + 3] == motif)

    jetes = set()
    for i in range(1, len(mots) - 2):
        if mots[i]["debut"] - mots[i - 1]["fin"] < PAUSE_RATE:
            continue
        motif = norm[i:i + 3]
        # la phrase reprise commence-t-elle comme un bout de ce qui vient d'être dit ?
        for j in range(i - 1, max(-1, i - 40), -1):
            if j in jetes:
                break
            if norm[j:j + 3] == motif:
                entendu = compte([w for k, w in enumerate(norm[:i + 3]) if k not in jetes], motif)
                if script and entendu <= compte(script, motif):
                    break  # répétition écrite dans le script : on garde
                jetes.update(range(j, i))
                break
    return jetes


def plan_de_montage(mots, jetes, imposees_avant, silence_fin_ms):
    """
    Décide ce qu'on garde de l'enregistrement et où on ajoute du silence.
    imposees_avant : {indice du mot entendu: silence minimum (ms) juste avant lui}.
    Renvoie (operations, nouveaux_temps) ; operations = [("garder", debut_ms, fin_ms) | ("silence", ms)]
    sur la timeline d'origine ; nouveaux_temps = {indice: (debut, fin)} sur la timeline finale.
    """
    gardes = [k for k in range(len(mots)) if k not in jetes]
    if not gardes:
        return [], {}
    ops, nouveaux = [], {}
    premier = mots[gardes[0]]
    t_new = 0.0
    if imposees_avant.get(gardes[0]):
        ops.append(("silence", imposees_avant[gardes[0]]))
        t_new += imposees_avant[gardes[0]]
    seg_debut = max(0, premier["debut"] - MARGE)   # début du morceau gardé en cours (timeline d'origine)
    seg_debut_new = t_new                           # le même instant sur la timeline finale

    def placer(k):
        m = mots[k]
        nouveaux[k] = (seg_debut_new + m["debut"] - seg_debut, seg_debut_new + m["fin"] - seg_debut)

    placer(gardes[0])
    for n in range(1, len(gardes)):
        p, k = gardes[n - 1], gardes[n]
        blanc = mots[k]["debut"] - mots[p]["fin"]
        mini = imposees_avant.get(k, 0)
        rate = k - p > 1
        if rate:
            cible = max(350, mini)
        elif blanc > BLANC_MAX and mini < blanc:
            cible = max(BLANC_CIBLE, mini)
        elif blanc < mini:
            cible = mini
        else:
            placer(k)
            continue
        milieu = (mots[p]["fin"] + mots[k]["debut"]) / 2
        a = min(mots[p]["fin"] + MARGE, milieu) if not rate else mots[p]["fin"] + MARGE
        b = max(mots[k]["debut"] - MARGE, a) if not rate else max(mots[k]["debut"] - MARGE, a)
        ajout = max(0.0, cible - (a - mots[p]["fin"]) - (mots[k]["debut"] - b))
        ops.append(("garder", seg_debut, a))
        seg_debut_new += a - seg_debut
        if ajout:
            ops.append(("silence", ajout))
            seg_debut_new += ajout
        seg_debut = b
        placer(k)
    dernier = mots[gardes[-1]]
    ops.append(("garder", seg_debut, dernier["fin"] + 400))
    ops.append(("silence", silence_fin_ms))
    return ops, nouveaux


def assembler(pcm, ops):
    sortie = bytearray()
    for op in ops:
        if op[0] == "garder":
            sortie += pcm[octets(op[1]):octets(op[2])]
        else:
            sortie += b"\x00\x00" * int(op[1] * TAUX / 1000)
    return sortie


# ---------------------------------------------------------------- alignement script ↔ voix
def aligner(tokens, entendus):
    """Associe chaque mot du script à un mot entendu. Renvoie {i_script: i_entendu}."""
    a = [t["mot"] for t in tokens]
    b = [normaliser(m["mot"]) for m in entendus]
    lien = {}
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    for bloc in sm.get_matching_blocks():
        for k in range(bloc.size):
            lien[bloc.a + k] = bloc.b + k
    # deuxième passe : mots proches (fautes de transcription, nombres écrits autrement)
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op == "replace" and (a1 - a0) == (b1 - b0):
            for k in range(a1 - a0):
                if difflib.SequenceMatcher(None, a[a0 + k], b[b0 + k]).ratio() > 0.6:
                    lien[a0 + k] = b0 + k
    return lien, sm


def rapport(tokens, entendus, lien, sm, script):
    lignes = []
    # phrases du script mal retrouvées
    for m in script["morceaux"]:
        idx = range(m["debut"], m["fin"])
        trouves = sum(1 for k in idx if k in lien)
        taux = trouves / max(1, len(idx))
        if taux < 0.35:
            lignes.append(f"SAUTÉE    « {m['texte'][:110]} »")
        elif taux < 0.8:
            lignes.append(f"CHANGÉE   « {m['texte'][:110]} »  ({int(taux * 100)} % des mots retrouvés)")
    # passages dits mais absents du script
    for op, a0, a1, b0, b1 in sm.get_opcodes():
        if op in ("insert", "replace") and b1 - b0 >= 4:
            dit = " ".join(m["mot"] for m in entendus[b0:b1])
            lignes.append(f"AJOUTÉE   « {dit[:110]} »")
    return lignes


# ---------------------------------------------------------------- recalage du montage existant
def recaler(plan, anciens, nouveaux):
    """Déplace tous les temps du montage : interpolation entre anciens et nouveaux temps des mots."""
    paires = sorted({(a["debut"], n["debut"]) for a, n in zip(anciens, nouveaux)} |
                    {(a["fin"], n["fin"]) for a, n in zip(anciens, nouveaux)})
    xs, ys = [p[0] for p in paires], [p[1] for p in paires]
    for k in range(1, len(ys)):  # strictement croissant
        ys[k] = max(ys[k], ys[k - 1])
    import bisect

    def f(t):
        if t <= xs[0]:
            return max(0, ys[0] - (xs[0] - t))
        if t >= xs[-1]:
            return ys[-1] + (t - xs[-1])
        j = bisect.bisect_right(xs, t)
        x0, x1, y0, y1 = xs[j - 1], xs[j], ys[j - 1], ys[j]
        return y0 + (y1 - y0) * (t - x0) / max(1, x1 - x0)

    def bouger(obj):
        if isinstance(obj, dict):
            for k, v in obj.items():
                if k in ("debutMs", "finMs", "aMs", "revelerAMs") and isinstance(v, (int, float)):
                    obj[k] = round(f(v))
                else:
                    bouger(v)
        elif isinstance(obj, list):
            for v in obj:
                bouger(v)

    for cle in ("fond", "calques", "sections"):
        bouger(plan[cle])
    return plan


def parole_et_silences(mots):
    parole, silences = [], []
    for m in mots:
        if parole and m["debut"] - parole[-1][1] < 450:
            parole[-1][1] = m["fin"]
        else:
            if parole and m["debut"] - parole[-1][1] >= 900:
                silences.append([parole[-1][1], m["debut"]])
            parole.append([m["debut"], m["fin"]])
    return parole, silences
