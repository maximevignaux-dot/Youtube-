"""shotlist.html (liste des visuels à fournir, lisible sur téléphone) + chapitres.txt + credits.txt."""
import html
import json
import os
import re
import urllib.parse

from .assets_auto import fichier_existant


def tc(ms):
    s = int(ms // 1000)
    return f"{s // 60}:{s % 60:02d}"


def phrase(tokens, k):
    a = k
    while a > 0 and not re.search(r"[.?!]\W*$", tokens[a - 1]["brut"]):
        a -= 1
    b = k
    while b < len(tokens) - 1 and not re.search(r"[.?!]\W*$", tokens[b]["brut"]):
        b += 1
    return " ".join(t["brut"] for t in tokens[a:b + 1])


def liens(asset):
    brut = asset.get("requetes") or ""
    fr, _, en = brut.partition("/")
    fr, en = fr.strip(), (en.strip() or fr.strip())
    q = urllib.parse.quote
    l = []
    if asset["genre"] == "video":
        l.append(("Pexels vidéos", f"https://www.pexels.com/fr-fr/chercher/videos/{q(en)}/"))
        l.append(("Pixabay vidéos", f"https://pixabay.com/fr/videos/search/{q(en)}/"))
        l.append(("Storyblocks", f"https://www.storyblocks.com/video/search/{q(en)}"))
    elif asset["genre"] == "ia":
        pass
    else:
        l.append(("Wikimedia", f"https://commons.wikimedia.org/w/index.php?search={q(en)}&title=Special:MediaSearch&type=image"))
        l.append(("Pexels", f"https://www.pexels.com/fr-fr/chercher/{q(en)}/"))
        l.append(("Pixabay", f"https://pixabay.com/fr/images/search/{q(en)}/"))
    return l


def generer(plan, script, dossier, slug):
    tokens = script["tokens"]
    assets_dir = os.path.join(dossier, "assets")
    credits_auto = {}
    p = os.path.join(assets_dir, "auto", "credits.json")
    if os.path.exists(p):
        credits_auto = json.load(open(p, encoding="utf-8"))

    # regroupe les apparitions de chaque visuel
    visuels = {}
    for e in plan["fond"]:
        a = e.get("asset")
        if not a:
            continue
        v = visuels.setdefault(a["id"], {"asset": a, "apparitions": [], "duree": 0, "composant": e["composant"]})
        v["apparitions"].append(e)
        v["duree"] += e["finMs"] - e["debutMs"]

    a_fournir, auto, fournis = [], [], []
    for ident, v in visuels.items():
        f = fichier_existant(assets_dir, ident)
        if not f:
            a_fournir.append(v)
        elif os.sep + "auto" + os.sep in f:
            v["fichier"] = os.path.relpath(f, dossier)
            auto.append(v)
        else:
            fournis.append(v)
    ordre = lambda v: v["apparitions"][0]["debutMs"]  # noqa: E731
    a_fournir.sort(key=ordre)
    auto.sort(key=ordre)

    def ext(a):
        return "mp4" if a["genre"] == "video" else "png" if a["genre"] == "ia" else "jpg"

    def carte(v, statut):
        a = v["asset"]
        prem = v["apparitions"][0]
        genre = {"video": "VIDÉO", "ia": "IMAGE IA", "photo": "PHOTO"}[a["genre"]]
        if v["composant"] == "FichePersonnage":
            genre = "PHOTO (fiche)"
        temps = ", ".join(tc(e["debutMs"]) for e in v["apparitions"][:4])
        nom = f"{a['id']}.{ext(a)}"
        pistes = "".join(f'<a href="{html.escape(u)}" target="_blank">{html.escape(t)}</a>' for t, u in liens(a))
        ia = ""
        if a["genre"] == "ia":
            ia = ('<p class="note">Image IA : génère-la avec ton outil (Midjourney, DALL·E, Ideogram…). '
                  'Jamais de visage réaliste d\'une vraie personne.</p>')
        apercu = ""
        if statut == "auto":
            cr = credits_auto.get(a["id"], {})
            media = (f'<video src="{html.escape(v["fichier"])}" muted loop playsinline preload="metadata"></video>'
                     if v["fichier"].endswith(("mp4", "webm", "mov")) else f'<img src="{html.escape(v["fichier"])}" loading="lazy">')
            apercu = (f'<div class="apercu">{media}</div><p class="note">Trouvé sur {html.escape(cr.get("source", "?"))} — '
                      f'{html.escape(cr.get("auteur", ""))} — {html.escape(cr.get("licence", ""))}. '
                      f'Pas bon ? Dépose ton propre fichier <b>{nom}</b> dans assets/ : il passera devant.</p>')
        else:
            apercu = (f'<div class="placeholder"><span class="pid">{a["id"]}</span><span class="pg">{genre} À FOURNIR</span>'
                      f'<span class="pd">{html.escape(a["description"][:140])}</span></div>')
        return f"""
<article class="item" data-id="{a['id']}">
  <label class="tete"><input type="checkbox" data-id="{a['id']}"><span class="id">{a['id']}</span><span class="genre">{genre}</span><span class="tc">{temps}</span></label>
  {apercu}
  <p class="phrase">« {html.escape(phrase(tokens, prem['ancre']))} »</p>
  <p class="desc">{html.escape(a['description'])}</p>
  <p class="meta">À l'écran : {v['duree'] / 1000:.1f} s · Mots-clés : <i>{html.escape(a.get('requetes') or '')}</i>{(' · Où : ' + html.escape(a['ou'])) if a.get('ou') else ''}</p>
  <p class="liens">{pistes}</p>{ia}
  <p class="fichier">Nom du fichier : <code>{nom}</code></p>
</article>"""

    total = len(visuels)
    AUCUN_AUTO = "<p>Aucun pour l'instant (clés API manquantes ou pas d'internet).</p>"
    page = f"""<!doctype html>
<html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Shotlist — {html.escape(plan.get('titre') or slug)}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Anton&family=Special+Elite&family=Inter:wght@400;600&display=swap" rel="stylesheet">
<style>
:root {{ --noir:#0D0D0D; --papier:#EFE6D2; --vert:#1F8A5B; --rouge:#C8102E; --jaune:#F2D023; }}
* {{ box-sizing:border-box; }}
body {{ margin:0; background:var(--noir); color:var(--papier); font:16px/1.45 Inter, system-ui, sans-serif; padding:16px; max-width:820px; margin:auto; }}
h1 {{ font-family:Anton, Impact, sans-serif; font-weight:400; font-size:34px; margin:8px 0 4px; letter-spacing:1px; }}
h2 {{ font-family:Anton, Impact, sans-serif; font-weight:400; font-size:24px; margin:32px 0 8px; color:var(--jaune); }}
.resume {{ font-family:"Special Elite", monospace; opacity:.85; }}
.barre {{ height:10px; background:#222; border-radius:5px; overflow:hidden; margin:10px 0 4px; }}
.barre i {{ display:block; height:100%; background:var(--vert); }}
.item {{ background:#171513; border:1px solid #2b2722; border-radius:10px; padding:14px; margin:12px 0; }}
.item.fait {{ opacity:.45; }}
.tete {{ display:flex; gap:10px; align-items:center; flex-wrap:wrap; cursor:pointer; }}
.tete input {{ width:24px; height:24px; accent-color:var(--vert); }}
.id {{ font-family:Anton, Impact, sans-serif; font-size:26px; }}
.genre {{ background:var(--rouge); color:#fff; font-size:12px; font-weight:600; padding:2px 8px; border-radius:4px; letter-spacing:1px; }}
.tc {{ margin-left:auto; font-family:"Special Elite", monospace; opacity:.8; }}
.phrase {{ font-style:italic; opacity:.8; margin:10px 0 6px; }}
.desc {{ font-weight:600; margin:6px 0; }}
.meta, .note {{ font-size:14px; opacity:.75; margin:4px 0; }}
.liens a {{ display:inline-block; margin:4px 6px 0 0; padding:6px 10px; border-radius:6px; background:#2b2722; color:var(--papier); text-decoration:none; font-size:14px; }}
.fichier code {{ background:var(--papier); color:var(--noir); padding:2px 8px; border-radius:4px; font-size:15px; }}
.placeholder {{ background:linear-gradient(160deg,#EFE6D2,#D9CDB2); color:#1A1712; border:2px dashed #8E7446; padding:14px 16px; margin-top:10px;
  font-family:"Special Elite", monospace; display:grid; grid-template-columns:auto 1fr; gap:4px 12px; transform:rotate(-.6deg); }}
.pid {{ font-family:Anton, Impact, sans-serif; font-size:28px; }} .pg {{ color:var(--rouge); align-self:center; font-size:13px; letter-spacing:2px; }}
.pd {{ grid-column:1 / -1; font-size:15px; }}
.apercu img, .apercu video {{ width:100%; border-radius:6px; margin-top:10px; display:block; }}
.aide {{ background:#171513; border-left:4px solid var(--jaune); padding:10px 14px; font-size:15px; }}
</style></head><body>
<h1>SHOTLIST — {html.escape(plan.get('titre') or slug)}</h1>
<p class="resume">{len(a_fournir)} à fournir · {len(auto)} trouvés automatiquement · {len(fournis)} déjà fournis par toi · {total} visuels au total</p>
<div class="barre"><i style="width:{(len(auto) + len(fournis)) * 100 // max(total, 1)}%"></i></div>
<p class="aide">Dépose chaque fichier dans <code>videos/{slug}/assets/</code> avec le nom indiqué, puis dis à Claude Code :
« J'ai ajouté des images pour {slug}, relance l'aperçu. » Coche les cases au fur et à mesure (mémorisé sur cet appareil).</p>
<h2>À FOURNIR ({len(a_fournir)})</h2>
{''.join(carte(v, 'manque') for v in a_fournir) or '<p>Rien ! Tout est là.</p>'}
<h2>TROUVÉS AUTOMATIQUEMENT — À VÉRIFIER ({len(auto)})</h2>
{''.join(carte(v, 'auto') for v in auto) or AUCUN_AUTO}
<script>
const cle = 'shotlist-{slug}';
let fait = {{}};
try {{ fait = JSON.parse(localStorage.getItem(cle) || '{{}}'); }} catch (e) {{}}
document.querySelectorAll('input[type=checkbox]').forEach((c) => {{
  const art = c.closest('.item');
  c.checked = !!fait[c.dataset.id]; art.classList.toggle('fait', c.checked);
  c.addEventListener('change', () => {{
    fait[c.dataset.id] = c.checked; art.classList.toggle('fait', c.checked);
    try {{ localStorage.setItem(cle, JSON.stringify(fait)); }} catch (e) {{}}
  }});
}});
</script>
</body></html>"""
    with open(os.path.join(dossier, "shotlist.html"), "w", encoding="utf-8") as f:
        f.write(page)

    # chapitres YouTube (le premier doit être à 0:00)
    lignes = []
    for n, s in enumerate(plan["sections"]):
        nom = re.sub(r"^PI[EÈ]CE\s*N°\s*(\d+)\s*[—-]\s*", r"Pièce n°\1 — ", s["nom"])
        nom = {"HOOK": "Introduction", "PROMESSE": "Ce que vous allez découvrir", "CONCLUSION": "Conclusion"}.get(nom.upper(), nom)
        lignes.append(f"{'0:00' if n == 0 else tc(s['debutMs'])} {nom}")
    with open(os.path.join(dossier, "chapitres.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lignes) + "\n")

    # crédits (à coller dans la description YouTube)
    cr = ["Crédits images et vidéos :"]
    for ident in sorted(credits_auto):
        c = credits_auto[ident]
        cr.append(f"- {c.get('source')} — {c.get('auteur') or 'auteur inconnu'} — {c.get('licence')} — {c.get('page')}")
    if len(cr) == 1:
        cr.append("- (aucune image automatique pour l'instant)")
    cr.append("Musique et sons : YouTube Audio Library / bibliothèque sous licence.")
    with open(os.path.join(dossier, "credits.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(cr) + "\n")
    return {"aFournir": len(a_fournir), "auto": len(auto), "fournis": len(fournis), "total": total}
