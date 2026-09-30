"""Génère des sons de base PROVISOIRES dans /sfx (synthétisés avec ffmpeg, libres de droits).

À remplacer au fil de l'eau par de vrais sons de la YouTube Audio Library / Epidemic / Artlist,
en gardant exactement les mêmes noms de fichiers.
Usage : python3 scripts/generer_sfx.py
"""
import os
import subprocess

DOSSIER = os.path.join(os.path.dirname(__file__), "..", "sfx")
BRUIT = "(random(0)*2-1)"

SONS = {
    # nom: (expression audio, durée en s, filtre optionnel)
    "tampon": (f"0.9*exp(-t*22)*sin(2*PI*62*t)+0.5*exp(-t*70)*{BRUIT}", 0.5, "lowpass=f=1800"),
    "frappe": (f"0.8*exp(-t*140)*{BRUIT}+0.3*exp(-t*90)*sin(2*PI*1900*t)", 0.08, "highpass=f=600"),
    "machine-a-ecrire": (f"0.7*exp(-mod(t,0.105)*130)*{BRUIT}*(0.7+0.3*sin(t*37))", 1.4, "highpass=f=700"),
    "flash": (f"0.7*exp(-t*9)*{BRUIT}+0.4*exp(-t*50)*sin(2*PI*3200*t)", 0.6, "highpass=f=1500"),
    "liasse": (f"0.55*{BRUIT}*(0.5+0.5*sin(2*PI*38*t))*min(1,t*20)*min(1,(1.6-t)*6)", 1.6, "bandpass=f=2600:w=1800"),
    "feuille": (f"0.6*{BRUIT}*sin(PI*t/0.55)", 0.55, "bandpass=f=3500:w=3000"),
    "nappe": ("0.25*sin(2*PI*55*t)+0.18*sin(2*PI*55.4*t)+0.12*sin(2*PI*82.5*t)*(0.6+0.4*sin(2*PI*0.07*t))"
              "+0.05*sin(2*PI*110.3*t)", 60, "lowpass=f=400,afade=t=in:d=2"),
}

os.makedirs(DOSSIER, exist_ok=True)
for nom, (expr, duree, filtre) in SONS.items():
    sortie = os.path.join(DOSSIER, f"{nom}.wav")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "lavfi",
           "-i", f"aevalsrc='{expr}':s=44100:d={duree}"]
    if filtre:
        cmd += ["-af", filtre]
    subprocess.run(cmd + [sortie], check=True)
    print("✓", os.path.relpath(sortie))
