"""Détourage des photos (rembg) : assets/decoupes/<ID>.png, utilisé pour l'effet 2,5D et les miniatures."""
import os

from .assets_auto import fichier_existant

PHOTOS = (".jpg", ".jpeg", ".png", ".webp")


def detourer(plan, dossier, journal=print):
    try:
        from rembg import new_session, remove
    except ImportError:
        journal("ℹ️  rembg n'est pas installé : pas d'effet 2,5D ni de sujet détouré (pip install rembg).")
        return 0
    sortie_dir = os.path.join(dossier, "assets", "decoupes")
    os.makedirs(sortie_dir, exist_ok=True)
    ids = set()
    for e in plan["fond"]:
        a = e.get("asset")
        # 2,5D seulement sur les vraies photos (pas les vidéos ni les images IA d'ambiance)
        if a and a["genre"] == "photo" and e["composant"] in ("Media", "FichePersonnage"):
            ids.add(a["id"])
    if plan.get("miniature", {}).get("assetId"):
        ids.add(plan["miniature"]["assetId"])
    n = 0
    session = None
    for ident in sorted(ids):
        src = fichier_existant(os.path.join(dossier, "assets"), ident)
        if not src or not src.lower().endswith(PHOTOS):
            continue
        dst = os.path.join(sortie_dir, f"{ident}.png")
        if os.path.exists(dst) and os.path.getmtime(dst) >= os.path.getmtime(src):
            continue
        try:
            session = session or new_session(os.environ.get("REMBG_MODELE", "u2net"))
            with open(src, "rb") as f:
                donnees = remove(f.read(), session=session)
            with open(dst, "wb") as f:
                f.write(donnees)
            n += 1
            journal(f"   ✓ {ident} détouré")
        except Exception as err:
            journal(f"   ⚠️  détourage raté pour {ident} ({type(err).__name__})")
    return n
