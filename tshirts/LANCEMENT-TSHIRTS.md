# Mission Claude Code — Boutique de t-shirts humour

> **Pour Maxime** : ouvre Claude Code dans un dossier vide (par exemple `Documents/tshirts`), glisse ce fichier dedans, et écris :
> **« Lis LANCEMENT-TSHIRTS.md et exécute toute la mission. »**
> C'est tout. Il te posera une question seulement s'il est bloqué.

---

## Ton rôle (Claude Code)
Tu montes et fais tourner l'atelier de designs d'une boutique de t-shirts humoristiques en impression à la demande (Printful). Maxime ne code pas : fais tout toi-même, explique en français simple, montre les résultats. Travaille dans le dossier courant.

Principe : **les designs sont fabriqués par `generate.py`** (texte parfait, fichiers prêts à imprimer, gratuit). **Canva sert aux illustrations** (personnages, objets drôles) que le script place ensuite dans les designs.

---

## Étape 1 — Installer
1. `pip install pillow cairosvg openpyxl` (Mac : `brew install cairo` si cairosvg échoue ; Windows : installer le runtime GTK3 si cairosvg échoue). Vérifie que `python3 -c "import cairosvg"` marche.
2. Crée les dossiers : `fonts/`, `icons/`, `illustrations/`, `sortie/`, `.claude/skills/tshirts/`.
3. Polices (Google Fonts, usage commercial autorisé) — télécharge dans `fonts/` depuis `https://raw.githubusercontent.com/google/fonts/main/<chemin>` (dans l'URL, `[wght]` s'écrit `%5Bwght%5D`) :
   - `ofl/anton/Anton-Regular.ttf`
   - `ofl/bebasneue/BebasNeue-Regular.ttf`
   - `ofl/oswald/Oswald[wght].ttf → renommer en Oswald.ttf`
   - `ofl/bowlbyonesc/BowlbyOneSC-Regular.ttf`
   - `ofl/alfaslabone/AlfaSlabOne-Regular.ttf`
   - `ofl/rye/Rye-Regular.ttf`
   - `ofl/archivoblack/ArchivoBlack-Regular.ttf`
   - `apache/permanentmarker/PermanentMarker-Regular.ttf`
   - `ofl/caveatbrush/CaveatBrush-Regular.ttf`
   - `ofl/shrikhand/Shrikhand-Regular.ttf`
   - `ofl/kaushanscript/KaushanScript-Regular.ttf`
   - `apache/yellowtail/Yellowtail-Regular.ttf`
   - `ofl/blackopsone/BlackOpsOne-Regular.ttf`
4. Icônes (Tabler, licence MIT) — dans `icons/` depuis `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<nom>.svg` : grill beer glass-full caravan fish bike motorbike plant coffee sofa shopping-cart device-gamepad-2 armchair ball-bowling tent glass-cocktail bottle chef-hat dog cat
5. Crée `icons/petanque.svg` avec ce contenu exact :
```svg
<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="10" cy="12" r="8"/><path d="M2.6 9.2c4.6 1.6 10.2 1.6 14.8 0"/><path d="M2.6 14.8c4.6 -1.6 10.2 -1.6 14.8 0"/><circle cx="20.5" cy="19.5" r="1.8"/></svg>
```

## Étape 2 — Créer `generate.py` (copie exacte)
```python
#!/usr/bin/env python3
"""Générateur de designs t-shirt — LM style "humour du quotidien".

Lit designs.json, sort pour chaque slogan et chaque style :
  - print/<id>__<style>.png   fichier d'impression 4500x5400 px, fond transparent, 300 dpi
  - apercus/<id>__<style>.jpg aperçu sur t-shirt
  - planche.jpg               toutes les variantes sur une seule image

Usage : python3 generate.py [designs.json]
"""
import json, math, os, random, re, sys
from io import BytesIO

import cairosvg
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageOps

ROOT = os.path.dirname(os.path.abspath(__file__))
F = lambda n: os.path.join(ROOT, "fonts", n)
FONTS = {
    "anton": F("Anton-Regular.ttf"),
    "bebas": F("BebasNeue-Regular.ttf"),
    "oswald": F("Oswald.ttf"),
    "bowlby": F("BowlbyOneSC-Regular.ttf"),
    "slab": F("AlfaSlabOne-Regular.ttf"),
    "western": F("Rye-Regular.ttf"),
    "archivo": F("ArchivoBlack-Regular.ttf"),
    "marker": F("PermanentMarker-Regular.ttf"),
    "brush": F("CaveatBrush-Regular.ttf"),
    "retro": F("Shrikhand-Regular.ttf"),
    "script": F("Yellowtail-Regular.ttf"),
    "script2": F("KaushanScript-Regular.ttf"),
    "stencil": F("BlackOpsOne-Regular.ttf"),
}

W, H = 4500, 5400          # zone d'impression standard (15 x 18 pouces à 300 dpi)
CW = 3900                  # largeur utile du texte

PALETTES = {
    # t-shirt noir
    "noir":  {"ink": "#F4F1EA", "accent": "#F2B705", "accent2": "#F26B1D", "tee": "#1C1C1E"},
    # t-shirt blanc
    "blanc": {"ink": "#1B2A41", "accent": "#C8102E", "accent2": "#E07A1F", "tee": "#F2F0EB"},
    # t-shirt kaki / vert
    "kaki":  {"ink": "#F4F1EA", "accent": "#F2B705", "accent2": "#F26B1D", "tee": "#4B5320"},
    # t-shirt bleu marine
    "marine": {"ink": "#F4F1EA", "accent": "#F2B705", "accent2": "#E8463A", "tee": "#1F2A44"},
    # t-shirt sable / vert de gris (encre noire)
    "sable": {"ink": "#1E1E1E", "accent": "#1E1E1E", "accent2": "#7A2E1F", "tee": "#A9A58E"},
    # t-shirt gris chiné (encre noire)
    "gris": {"ink": "#1E1E1E", "accent": "#B3261E", "accent2": "#B3261E", "tee": "#B8B8B5"},
}


# ---------------------------------------------------------------- outils texte
def _font(name, size):
    return ImageFont.truetype(FONTS[name], max(8, int(size)))


def render_text(txt, font, size, color, tracking=0.0):
    """Rend une ligne en RGBA recadrée au plus près de l'encre."""
    size = max(8, int(size))
    f = _font(font, size)
    track = int(size * tracking)
    widths = [f.getlength(c) for c in txt]
    total = int(sum(widths) + track * max(0, len(txt) - 1)) + size
    img = Image.new("RGBA", (total + size, int(size * 2.2)), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = size // 2
    for c, w in zip(txt, widths):
        d.text((x, int(size * 0.3)), c, font=f, fill=color)
        x += w + track
    bbox = img.getbbox()
    return img.crop(bbox) if bbox else img


def fit_text(txt, font, color, width, max_h, tracking=0.0):
    """Rend le texte en le faisant tenir dans `width`, sans dépasser `max_h` en hauteur."""
    probe = render_text(txt, font, 400, color, tracking)
    size = 400 * width / probe.width
    probe_h = probe.height * size / 400
    if probe_h > max_h:
        size *= max_h / probe_h
    img = render_text(txt, font, size, color, tracking)
    if img.width > width:  # sécurité
        img = img.resize((width, int(img.height * width / img.width)), Image.LANCZOS)
    return img


def icon(name, color, px, stroke=2.0):
    path = os.path.join(ROOT, "icons", f"{name}.svg")
    svg = open(path, encoding="utf-8").read()
    svg = svg.replace("currentColor", color)
    svg = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{stroke}"', svg)
    png = cairosvg.svg2png(bytestring=svg.encode(), output_width=px, output_height=px)
    im = Image.open(BytesIO(png)).convert("RGBA")
    return im.crop(im.getbbox())


def stack(parts, gap):
    """Empile verticalement des images centrées."""
    w = max(p.width for p in parts)
    h = sum(p.height for p in parts) + gap * (len(parts) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for p in parts:
        out.alpha_composite(p, ((w - p.width) // 2, y))
        y += p.height + gap
    return out


def place(design, top_margin=250):
    """Centre le design horizontalement dans la zone d'impression, collé en haut."""
    canvas = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = design
    if d.width > W - 300 or d.height > H - 2 * top_margin:
        r = min((W - 300) / d.width, (H - 2 * top_margin) / d.height)
        d = d.resize((int(d.width * r), int(d.height * r)), Image.LANCZOS)
    canvas.alpha_composite(d, ((W - d.width) // 2, top_margin))
    return canvas


def distress(img, seed, strength=0.35):
    """Effet usé/vintage : ronge l'encre de façon irrégulière."""
    rnd = random.Random(seed)
    w, h = img.size
    small = Image.new("L", (w // 24, h // 24))
    small.putdata([rnd.randint(0, 255) for _ in range(small.width * small.height)])
    blob = small.resize((w, h), Image.BICUBIC).filter(ImageFilter.GaussianBlur(18))
    thr = int(255 * (1 - strength * 0.55))
    blob = blob.point(lambda v: 0 if v > thr else 255)
    speck = Image.effect_noise((w // 3, h // 3), 90).resize((w, h)).point(lambda v: 0 if v > 205 else 255)
    mask = Image.composite(blob, Image.new("L", (w, h), 0), speck)
    a = img.getchannel("A")
    img.putalpha(Image.composite(a, Image.new("L", (w, h), 0), mask))
    return img


# ------------------------------------------------------------------ STYLE 1
def style_empile(d, pal):
    """Texte empilé, chaque ligne calée sur la même largeur (style affiche)."""
    parts = []
    for ln in d["lignes"]:
        lvl = ln.get("niveau", "grand")
        if lvl == "petit":
            parts.append(fit_text(ln["txt"].upper(), "bebas", pal["ink"], int(CW * 0.82), 330, 0.04))
        elif lvl == "accent":
            parts.append(fit_text(ln["txt"].upper(), "anton", pal["accent"], CW, 900))
        else:
            parts.append(fit_text(ln["txt"].upper(), "anton", pal["ink"], CW, 760))
        if d.get("icone") and ln.get("icone_apres"):
            parts.append(icon(d["icone"], pal["ink"], 900, 1.9))
    if d.get("icone") and not any(l.get("icone_apres") for l in d["lignes"]):
        parts.insert(len(parts) // 2, icon(d["icone"], pal["ink"], 900, 1.9))
    body = stack(parts, 70)
    if d.get("chute"):
        ch = fit_text(d["chute"], "marker", pal["accent2"], int(CW * 0.75), 300)
        ch = ch.rotate(4, resample=Image.BICUBIC, expand=True)
        body = stack([body, ch], 140)
    return body


# ------------------------------------------------------------------ STYLE 2
def arc_text(img, txt, font, size, color, cx, cy, r, top=True, tracking=0.06):
    f = _font(font, size)
    chars = list(txt)
    widths = [f.getlength(c) + size * tracking for c in chars]
    total = sum(widths)
    ang = (-90 if top else 90) - (math.degrees(total / r) / 2 if top else -math.degrees(total / r) / 2)
    for c, w in zip(chars, widths):
        a_mid = ang + (math.degrees(w / r) / 2) * (1 if top else -1)
        g = Image.new("RGBA", (int(size * 1.6), int(size * 1.6)), (0, 0, 0, 0))
        ImageDraw.Draw(g).text((g.width / 2, g.height / 2), c, font=f, fill=color, anchor="mm")
        rot = -(a_mid + 90) if top else -(a_mid - 90)
        g = g.rotate(rot, resample=Image.BICUBIC)
        x = cx + r * math.cos(math.radians(a_mid)) - g.width / 2
        y = cy + r * math.sin(math.radians(a_mid)) - g.height / 2
        img.alpha_composite(g, (int(x), int(y)))
        ang += math.degrees(w / r) * (1 if top else -1)


def style_badge(d, pal):
    """Écusson rond façon club, texte en arc, icône au centre."""
    S = 4000
    img = Image.new("RGBA", (S, S + 900), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    cx, cy, R = S // 2, S // 2, 1850
    dr.ellipse([cx - R, cy - R, cx + R, cy + R], outline=pal["ink"], width=70)
    dr.ellipse([cx - R + 420, cy - R + 420, cx + R - 420, cy + R - 420], outline=pal["ink"], width=28)
    petits = [l["txt"] for l in d["lignes"] if l.get("niveau") == "petit"]
    gros = [l["txt"] for l in d["lignes"] if l.get("niveau") != "petit"]
    top_txt = (d.get("arc_haut") or (petits[0] if petits else "")).upper()
    bot_txt = (d.get("arc_bas") or (petits[1] if len(petits) > 1 else d.get("marque", "VÉRIFIÉ ET APPROUVÉ"))).upper()
    for txt, top in ((top_txt, True), (bot_txt, False)):
        size = 300
        while size > 120 and _font("archivo", size).getlength(txt) * 1.1 > math.radians(118) * (R - 210):
            size -= 10
        arc_text(img, txt, "archivo", size, pal["ink"], cx, cy, R - 210 - (0 if top else 0), top)
    for sx in (-1, 1):  # petites étoiles de séparation
        x, y = cx + sx * (R - 210), cy
        dr.regular_polygon((x, y, 70), 5, rotation=0, fill=pal["accent"])
    # bandeau central
    lines = [t.upper() for t in (d.get("centre") or gros)][:3]
    max_h = {1: 700, 2: 440, 3: 300}[len(lines)]
    txts = [fit_text(t, "anton", pal["accent"] if i == len(lines) - 1 else pal["ink"], 3200, max_h)
            for i, t in enumerate(lines)]
    band = stack(txts, 50)
    bw, bh = 3800, band.height + 220
    by = cy + 120 - bh // 2
    if d.get("icone"):
        ic_px = min(900, max(450, by - (cy - R + 520) - 120))
        ic = icon(d["icone"], pal["ink"], ic_px, 1.8)
        img.alpha_composite(ic, (cx - ic.width // 2, (cy - R + 470 + by) // 2 - ic.height // 2))
    rib = Image.new("RGBA", img.size, (0, 0, 0, 0))
    rd = ImageDraw.Draw(rib)
    tee = pal["tee"]
    rd.polygon([(cx - bw // 2, by), (cx + bw // 2, by), (cx + bw // 2 - 120, by + bh // 2),
                (cx + bw // 2, by + bh), (cx - bw // 2, by + bh), (cx - bw // 2 + 120, by + bh // 2)],
               fill=tee, outline=pal["ink"], width=40)
    img.alpha_composite(rib)
    if band.width > bw - 400:
        band = band.resize((bw - 400, int(band.height * (bw - 400) / band.width)), Image.LANCZOS)
    img.alpha_composite(band, (cx - band.width // 2, by + (bh - band.height) // 2))
    if d.get("chute"):
        ch = fit_text(d["chute"], "marker", pal["accent2"], 3200, 300).rotate(3, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(ch, (cx - ch.width // 2, S + 150))
    img = img.crop(img.getbbox())
    return distress(img, d["id"] + "b", 0.22)


# ------------------------------------------------------------------ STYLE 3
def style_retro(d, pal):
    """Typo slab vintage avec étoiles, filets, effet usé."""
    parts = []
    rule_w = int(CW * 0.9)
    for i, ln in enumerate(d["lignes"]):
        lvl = ln.get("niveau", "grand")
        if lvl == "petit":
            t = fit_text(ln["txt"].upper(), "oswald", pal["ink"], int(CW * 0.6), 260, 0.08)
            star = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            ImageDraw.Draw(star).regular_polygon((80, 80, 70), 5, fill=pal["accent"])
            row = Image.new("RGBA", (t.width + 560, max(t.height, 160)), (0, 0, 0, 0))
            row.alpha_composite(star, (0, (row.height - 160) // 2))
            row.alpha_composite(t, (280, (row.height - t.height) // 2))
            row.alpha_composite(star, (row.width - 160, (row.height - 160) // 2))
            parts.append(row)
        elif lvl == "accent":
            parts.append(fit_text(ln["txt"].upper(), "retro" if len(ln["txt"]) < 16 else "slab",
                                  pal["accent"], CW, 1000))
        else:
            parts.append(fit_text(ln["txt"].upper(), "slab", pal["ink"], CW, 720))
    if d.get("icone"):
        parts.insert(0, icon(d["icone"], pal["accent"], 800, 1.8))
    rule = Image.new("RGBA", (rule_w, 34), pal["ink"])
    body = stack([rule] + parts + [rule], 90)
    if d.get("chute"):
        ch = fit_text(d["chute"], "brush", pal["ink"], int(CW * 0.7), 330)
        body = stack([body, ch], 120)
    return distress(body, d["id"] + "r", 0.4)


# ------------------------------------------------------------------ STYLE 4
def style_fiche(d, pal):
    """Fiche « état des lieux » avec cases cochées et jauges."""
    parts = [fit_text(d.get("titre", d["lignes"][0]["txt"]).upper(), "anton", pal["accent"], CW, 800)]
    rows = []
    for item in d["liste"]:
        lab = fit_text(item["label"].upper(), "anton", pal["ink"], 1700, 330)
        val_txt = item.get("valeur", "")
        etat = item.get("etat", "ok")  # ok | non | jauge
        row = Image.new("RGBA", (CW, 420), (0, 0, 0, 0))
        rd = ImageDraw.Draw(row)
        row.alpha_composite(lab, (0, (420 - lab.height) // 2))
        x0 = 1800
        if etat == "jauge":
            pct = item.get("pct", 15) / 100
            rd.rounded_rectangle([x0, 110, x0 + 1300, 310], radius=40, outline=pal["ink"], width=26)
            col = pal["accent2"] if pct < 0.3 else pal["accent"]
            rd.rounded_rectangle([x0 + 40, 150, x0 + 40 + int(1220 * pct), 270], radius=24, fill=col)
            if val_txt:
                v = fit_text(val_txt.upper(), "bebas", pal["ink"], 750, 200)
                row.alpha_composite(v, (CW - v.width, (420 - v.height) // 2))
        else:
            rd.rectangle([x0, 90, x0 + 240, 330], outline=pal["ink"], width=26)
            if etat == "ok":
                rd.line([(x0 + 40, 210), (x0 + 110, 300), (x0 + 290, 30)], fill=pal["accent"], width=60, joint="curve")
            else:
                rd.line([(x0 + 40, 130), (x0 + 200, 290)], fill=pal["accent2"], width=50)
                rd.line([(x0 + 200, 130), (x0 + 40, 290)], fill=pal["accent2"], width=50)
            if val_txt:
                v = fit_text(val_txt.upper(), "bebas", pal["ink"], 1500, 230)
                row.alpha_composite(v, (x0 + 380, (420 - v.height) // 2))
        rows.append(row)
    sep = Image.new("RGBA", (CW, 22), pal["ink"])
    parts.append(sep)
    parts += rows
    parts.append(sep)
    if d.get("chute"):
        parts.append(fit_text(d["chute"], "marker", pal["accent2"], int(CW * 0.8), 300)
                     .rotate(3, resample=Image.BICUBIC, expand=True))
    return stack(parts, 80)


# ------------------------------------------------------------------ STYLE 5
def brush_banner(txt, pal, width, seed):
    """Bandeau effet coup de pinceau, texte en réserve (on voit le t-shirt à travers)."""
    rnd = random.Random(seed)
    t = fit_text(txt.upper(), "slab", "#000000", int(width * 0.84), 380)
    h = t.height + 200
    ban = Image.new("L", (width, h), 0)
    dr = ImageDraw.Draw(ban)
    dr.rectangle([90, 30, width - 90, h - 30], fill=255)
    for _ in range(70):  # bords effilochés
        y = rnd.randint(20, h - 20)
        lg = rnd.randint(40, 220)
        th = rnd.randint(6, 26)
        dr.rectangle([90 - lg, y, 100, y + th], fill=255)
        lg = rnd.randint(40, 220)
        dr.rectangle([width - 100, y, width - 90 + lg, y + th], fill=255)
    knock = Image.new("L", (width, h), 0)
    knock.paste(t.getchannel("A"), ((width - t.width) // 2, (h - t.height) // 2))
    alpha = Image.composite(Image.new("L", (width, h), 0), ban, knock.point(lambda v: 255 if v > 100 else 0))
    out = Image.new("RGBA", (width, h), pal["ink"])
    out.putalpha(alpha)
    return out


def style_mix(d, pal):
    """Mélange slab + script + bandeau pinceau (style « je suis né pour… »)."""
    parts = []
    lignes = d["lignes"]
    last = len(lignes) - 1
    for i, ln in enumerate(lignes):
        lvl = ln.get("niveau", "grand")
        txt = ln["txt"]
        if ln.get("bandeau") or (i == last and not any(l.get("bandeau") for l in lignes)):
            parts.append(brush_banner(txt, pal, CW, d["id"]))
        elif lvl == "accent":
            parts.append(fit_text(txt, "script", pal["accent"], CW, 1000))
        elif lvl == "petit" and len(txt) <= 12:
            t = fit_text(txt.upper(), "slab", pal["ink"], 1500, 300)
            row = Image.new("RGBA", (CW, t.height), (0, 0, 0, 0))
            rd = ImageDraw.Draw(row)
            for k in range(3):  # triples traits de chaque côté
                y = t.height // 2 - 60 + k * 50
                rd.line([(120, y), ((CW - t.width) // 2 - 90, y)], fill=pal["ink"], width=26)
                rd.line([((CW + t.width) // 2 + 90, y), (CW - 120, y)], fill=pal["ink"], width=26)
            row.alpha_composite(t, ((CW - t.width) // 2, 0))
            parts.append(row)
        elif lvl == "petit":
            parts.append(fit_text(txt.upper(), "slab", pal["ink"], int(CW * 0.85), 380))
        else:
            parts.append(fit_text(txt.upper(), "slab", pal["ink"], CW, 650))
    body = stack(parts, 60)
    return distress(body, d["id"] + "m", 0.25)


def load_illustration(name, target_w):
    """Charge illustrations/<name> (png/jpg), enlève le fond blanc uni, redimensionne."""
    path = os.path.join(ROOT, "illustrations", name)
    im = Image.open(path).convert("RGB")
    if im.width < target_w:  # agrandissement doux (à éviter : préférer une source haute déf)
        im = im.resize((target_w, int(im.height * target_w / im.width)), Image.LANCZOS)
    key = (255, 0, 255)
    work = im.copy()
    for xy in [(0, 0), (work.width - 1, 0), (0, work.height - 1), (work.width - 1, work.height - 1)]:
        ImageDraw.floodfill(work, xy, key, thresh=60)
    mask = Image.new("L", im.size, 255)
    px_w, px_m = work.load(), mask.load()
    for y in range(im.height):
        for x in range(im.width):
            if px_w[x, y] == key:
                px_m[x, y] = 0
    mask = mask.filter(ImageFilter.GaussianBlur(1.2))
    out = im.convert("RGBA")
    out.putalpha(mask)
    out = out.crop(out.getbbox())
    if out.width > target_w:
        out = out.resize((target_w, int(out.height * target_w / out.width)), Image.LANCZOS)
    return out


# ------------------------------------------------------------------ STYLE 6
def style_illustre(d, pal):
    """Illustration au centre, texte au-dessus et en dessous."""
    ill = load_illustration(d["illustration"], 2600)
    haut, bas, seen = [], [], False
    for ln in d["lignes"]:
        lvl = ln.get("niveau", "grand")
        if lvl == "petit":
            im = fit_text(ln["txt"].upper(), "bebas", pal["ink"], int(CW * 0.8), 330, 0.04)
        elif lvl == "accent":
            im = fit_text(ln["txt"].upper(), "anton", pal["accent"], CW, 700)
        else:
            im = fit_text(ln["txt"].upper(), "anton", pal["ink"], CW, 620)
        (bas if seen else haut).append(im)
        if ln.get("illustration_apres"):
            seen = True
    if not seen:  # par défaut : moitié au-dessus, moitié en dessous
        allp = haut
        k = max(1, len(allp) // 2)
        haut, bas = allp[:k], allp[k:]
    parts = haut + [ill] + bas
    body = stack(parts, 70)
    if d.get("chute"):
        ch = fit_text(d["chute"], "marker", pal["accent2"], int(CW * 0.75), 300).rotate(4, resample=Image.BICUBIC, expand=True)
        body = stack([body, ch], 120)
    return body


STYLES = {"empile": style_empile, "mix": style_mix, "badge": style_badge, "retro": style_retro, "fiche": style_fiche, "illustre": style_illustre}


# ------------------------------------------------------------------ aperçu t-shirt
def tee_mockup(print_img, tee_color, size=900):
    s = size / 1000
    img = Image.new("RGB", (size, int(1100 * s)), "#E9E6E1")
    shape = [(300, 70), (390, 50), (430, 95), (500, 110), (570, 95), (610, 50), (700, 70), (930, 220),
             (850, 400), (770, 350), (770, 1060), (230, 1060), (230, 350), (150, 400), (70, 220)]
    shape = [(x * s, y * s) for x, y in shape]
    shadow = Image.new("L", img.size, 0)
    ImageDraw.Draw(shadow).polygon([(x + 8 * s, y + 14 * s) for x, y in shape], fill=90)
    img.paste(Image.new("RGB", img.size, "#B9B5AE"), mask=shadow.filter(ImageFilter.GaussianBlur(14 * s)))
    m = Image.new("L", img.size, 0)
    ImageDraw.Draw(m).polygon(shape, fill=255)
    img.paste(Image.new("RGB", img.size, tee_color), mask=m)
    dr = ImageDraw.Draw(img)
    dr.arc([395 * s, 30 * s, 605 * s, 150 * s], 15, 165, fill="#00000055", width=int(6 * s))
    pw = int(430 * s)
    p = print_img.resize((pw, int(pw * H / W)), Image.LANCZOS)
    img.paste(p, (int(285 * s), int(190 * s)), p)
    return img


def contact_sheet(thumbs, path):
    cols = 3 if len(thumbs) > 4 else max(1, len(thumbs))
    tw, th = 600, 733
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * tw, rows * (th + 70)), "#FFFFFF")
    sd = ImageDraw.Draw(sheet)
    lab = _font("oswald", 34)
    for i, (name, mk) in enumerate(thumbs):
        x, y = (i % cols) * tw, (i // cols) * (th + 70)
        sheet.paste(mk.resize((tw, th), Image.LANCZOS), (x, y))
        sd.text((x + tw // 2, y + th + 35), name, font=lab, fill="#222", anchor="mm")
    sheet.save(path, quality=85)


def main():
    """python3 generate.py [--force] [--only id1,id2]
    Ne régénère que les designs dont le dossier sortie/<id>/ n'existe pas encore."""
    args = sys.argv[1:]
    force = "--force" in args
    only = None
    if "--only" in args:
        only = set(args[args.index("--only") + 1].split(","))
    designs = json.load(open(os.path.join(ROOT, "designs.json"), encoding="utf-8"))
    out_root = os.path.join(ROOT, "sortie")
    os.makedirs(out_root, exist_ok=True)
    day = []
    for d in designs:
        if only and d["id"] not in only:
            continue
        folder = os.path.join(out_root, d["id"])
        if os.path.exists(os.path.join(folder, "planche.jpg")) and not force and not only:
            continue
        os.makedirs(folder, exist_ok=True)
        pal = dict(PALETTES[d.get("tshirt", "noir")])
        if d.get("accent"):
            pal["accent"] = d["accent"]
        styles = d.get("styles") or (["fiche"] if d.get("liste")
                                     else (["illustre", "empile"] if d.get("illustration")
                                           else ["empile", "mix", "badge", "retro"]))
        thumbs = []
        for st in styles:
            art = STYLES[st](d, pal)
            canvas = place(art)
            canvas.save(os.path.join(folder, f"impression_{st}.png"), dpi=(300, 300), optimize=True)
            mk = tee_mockup(canvas, pal["tee"])
            mk.save(os.path.join(folder, f"apercu_{st}.jpg"), quality=88)
            thumbs.append((f'{d["id"]} · {st}', mk))
            print("ok", d["id"], st)
        contact_sheet(thumbs, os.path.join(folder, "planche.jpg"))
        day += thumbs
    if day:
        contact_sheet(day, os.path.join(ROOT, "planche-du-jour.jpg"))
        print("planche-du-jour.jpg :", len(day), "variantes")
    else:
        print("Rien de nouveau à générer.")


if __name__ == "__main__":
    main()

```

## Étape 3 — Créer `designs.json` (designs déjà validés, copie exacte)
L'entrée `saucisson-aux-herbes` utilise une illustration qui n'est pas encore là : retire la clé `"illustration"` de cette entrée tant que `illustrations/saucisson-aux-herbes.png` n'existe pas (voir étape 6).
```json
[
  {
    "id": "petanque-apero",
    "tshirt": "noir",
    "icone": "petanque",
    "arc_haut": "Club des tireurs du dimanche",
    "arc_bas": "Fondé à l'heure de l'apéro",
    "lignes": [
      {
        "txt": "Je tire ou je pointe ?",
        "niveau": "petit"
      },
      {
        "txt": "Ni l'un",
        "niveau": "grand"
      },
      {
        "txt": "ni l'autre",
        "niveau": "grand",
        "icone_apres": true
      },
      {
        "txt": "Je sers",
        "niveau": "petit"
      },
      {
        "txt": "L'APÉRO",
        "niveau": "accent"
      }
    ],
    "chute": "Et je compte les points de loin",
    "centre": [
      "Ni l'un ni l'autre",
      "Je sers l'apéro"
    ]
  },
  {
    "id": "camping-car",
    "tshirt": "marine",
    "icone": "caravan",
    "arc_haut": "Ma maison a des roues",
    "arc_bas": "Et mon jardin change tous les jours",
    "lignes": [
      {
        "txt": "Ma maison",
        "niveau": "petit"
      },
      {
        "txt": "a des roues",
        "niveau": "grand",
        "icone_apres": true
      },
      {
        "txt": "et mon jardin",
        "niveau": "petit"
      },
      {
        "txt": "change tous",
        "niveau": "accent"
      },
      {
        "txt": "les jours",
        "niveau": "accent"
      }
    ],
    "chute": "Camping-cariste, pas SDF",
    "centre": [
      "Ma maison",
      "a des roues"
    ]
  },
  {
    "id": "jardin-tomates",
    "tshirt": "kaki",
    "icone": "plant",
    "arc_haut": "Je parle à mes tomates",
    "arc_bas": "Elles au moins elles m'écoutent",
    "lignes": [
      {
        "txt": "Je parle",
        "niveau": "grand"
      },
      {
        "txt": "à mes",
        "niveau": "petit"
      },
      {
        "txt": "TOMATES",
        "niveau": "accent",
        "icone_apres": true
      },
      {
        "txt": "Elles au moins",
        "niveau": "petit"
      },
      {
        "txt": "elles m'écoutent",
        "niveau": "grand"
      }
    ],
    "centre": [
      "Je parle",
      "à mes tomates"
    ]
  },
  {
    "id": "caractere",
    "tshirt": "blanc",
    "icone": "coffee",
    "arc_haut": "Certifiée 100 % caractère",
    "arc_bas": "Approche à vos risques",
    "lignes": [
      {
        "txt": "J'ai pas un",
        "niveau": "petit"
      },
      {
        "txt": "sale caractère",
        "niveau": "grand"
      },
      {
        "txt": "J'ai du caractère",
        "niveau": "petit"
      },
      {
        "txt": "et il est sale",
        "niveau": "accent"
      }
    ],
    "chute": "Merci de me laisser mon café",
    "centre": [
      "Pas un sale caractère",
      "Du caractère. Sale."
    ]
  },
  {
    "id": "retraite",
    "tshirt": "noir",
    "icone": "armchair",
    "arc_haut": "Retraité officiel",
    "arc_bas": "Horaires : quand je veux",
    "lignes": [
      {
        "txt": "Retraité",
        "niveau": "petit"
      },
      {
        "txt": "Je fais ce",
        "niveau": "grand"
      },
      {
        "txt": "que je veux",
        "niveau": "grand"
      },
      {
        "txt": "et surtout rien",
        "niveau": "accent"
      }
    ],
    "chute": "Réveil : supprimé",
    "centre": [
      "Je fais ce que je veux",
      "et surtout rien"
    ]
  },
  {
    "id": "mode-papy",
    "tshirt": "noir",
    "titre": "Mode papy activé",
    "lignes": [
      {
        "txt": "Mode papy activé",
        "niveau": "grand"
      }
    ],
    "liste": [
      {
        "label": "Sieste",
        "etat": "ok",
        "valeur": "faite"
      },
      {
        "label": "Apéro",
        "etat": "ok",
        "valeur": "fait"
      },
      {
        "label": "Jardin",
        "etat": "ok",
        "valeur": "inspecté"
      },
      {
        "label": "Ménage",
        "etat": "non",
        "valeur": "en réflexion"
      },
      {
        "label": "Patience",
        "etat": "jauge",
        "pct": 12,
        "valeur": "critique"
      }
    ],
    "chute": "Merci de ne pas déranger"
  },
  {
    "id": "ne-pour-rien-faire",
    "tshirt": "sable",
    "arc_haut": "Daron certifié",
    "arc_bas": "Râleur depuis toujours",
    "centre": [
      "Je fais rien",
      "et je le fais bien"
    ],
    "lignes": [
      {
        "txt": "Je ne suis pas",
        "niveau": "petit"
      },
      {
        "txt": "fainéant",
        "niveau": "grand"
      },
      {
        "txt": "Je suis",
        "niveau": "petit"
      },
      {
        "txt": "en mode économie",
        "niveau": "accent"
      },
      {
        "txt": "d'énergie",
        "niveau": "petit"
      },
      {
        "txt": "Comme la planète",
        "niveau": "grand",
        "bandeau": true
      }
    ],
    "chute": "Daron, et fier de l'être"
  },
  {
    "id": "saucisson-aux-herbes",
    "tshirt": "noir",
    "illustration": "saucisson-muscle.jpg",
    "icone": "grill",
    "lignes": [
      {
        "txt": "Moi aussi",
        "niveau": "petit"
      },
      {
        "txt": "je mange des plantes",
        "niveau": "grand",
        "illustration_apres": true,
        "icone_apres": true
      },
      {
        "txt": "du saucisson",
        "niveau": "accent"
      },
      {
        "txt": "aux herbes",
        "niveau": "accent"
      }
    ],
    "chute": "Végétarien à ma façon"
  }
]
```

## Étape 4 — Créer `banque-slogans.xlsx`
Avec openpyxl, trois onglets :
- **Slogans** : colonnes `N° | Niche / métier | Slogan | Chute (facultatif) | Couleur t-shirt | Cible | Statut | Note`. Police Arial, en-tête noir texte blanc, colonne Slogan en gras, retour à la ligne automatique, filtre et volet figé en C2. Listes déroulantes : Couleur (`noir,blanc,kaki,marine,sable,gris`), Cible (`H,F,Mixte`), Statut (`Idée,Validé,Design fait,En ligne,Vendu,Abandonné,Test`). Couleur de ligne selon le statut (Validé jaune pâle, Design fait bleu pâle, En ligne vert pâle, Vendu vert, Abandonné gris).
- **Formules** : le second tableau ci-dessous.
- **Mode d'emploi** : 5 lignes qui expliquent les statuts et la commande `/tshirts`.

### Slogans
| N° | Niche / métier | Slogan | Chute | Couleur | Cible | Statut | Note |
|---|---|---|---|---|---|---|---|
| 1 | Pétanque / apéro | Je tire ou je pointe ? Ni l'un ni l'autre, je sers l'apéro | Et je compte les points de loin | noir | H | Test | Design déjà généré |
| 2 | Camping-car | Ma maison a des roues et mon jardin change tous les jours | Camping-cariste, pas SDF | marine | Mixte | Test | Design déjà généré |
| 3 | Jardin | Je parle à mes tomates, elles au moins elles m'écoutent |  | kaki | Mixte | Test | Design déjà généré |
| 4 | Caractère (femme) | J'ai pas un sale caractère, j'ai du caractère et il est sale | Merci de me laisser mon café | blanc | F | Test | Design déjà généré |
| 5 | Retraite | Retraité : je fais ce que je veux et surtout rien | Réveil : supprimé | noir | H | Test | Design déjà généré |
| 6 | Retraite | Mode papy activé : sieste faite, apéro fait, jardin inspecté, ménage en réflexion, patience critique | Merci de ne pas déranger | noir | H | Test | Style fiche |
| 7 | Mécano | Si la vie était une voiture, je serais ton moteur PureTech |  | noir | H | Idée | TON IDÉE. Risque : PureTech est une marque déposée de Stellantis. Préférer la version sans nom ci-dessous. |
| 8 | Mécano | Si la vie était une voiture, je serais ton 1.2 essence : ma courroie baigne dans l'huile | Les vrais savent | noir | H | Idée | Version sans marque : les mécanos comprennent tout de suite |
| 9 | Mécano | Il a rien touché. Il a juste regardé un tuto. | Mécano, je répare aussi les tutos | noir | H | Idée |  |
| 10 | Mécano | Je répare aussi ce que ton beau-frère a réparé | Supplément beau-frère : +50 % | noir | H | Idée |  |
| 11 | Mécano | FAP, EGR, AdBlue : merci l'écologie, je vis de vos pannes |  | noir | H | Idée |  |
| 12 | Mécano | J'ai pas besoin de valise diagnostic. J'ai l'oreille. | Et 30 ans de cambouis | noir | H | Idée |  |
| 13 | Plombier | C'est pas moi qui ai fait ça. C'est le plombier d'avant. |  | noir | H | Idée |  |
| 14 | Plombier | Ça fuyait pas avant que je vienne. Ça fuyait juste pas encore. |  | marine | H | Idée |  |
| 15 | Plombier | Plombier : je vois des choses que tu ne veux pas savoir | Lave-toi les mains | noir | H | Idée |  |
| 16 | Électricien | Le domino, c'est pas un jeu | Électricien, pas croupier | noir | H | Idée |  |
| 17 | Électricien | Je refais l'installation du beau-frère depuis 1998 |  | noir | H | Idée |  |
| 18 | Électricien | Je travaille sous tension. À la maison aussi. |  | noir | H | Idée |  |
| 19 | Maçon / BTP | C'est pas droit ? L'enduit rattrapera. | Maçon, pas magicien… enfin si | noir | H | Idée |  |
| 20 | Plaquiste / BTP | T'inquiète, ça sera caché par le placo |  | noir | H | Idée |  |
| 21 | BTP | Le devis était juste. C'est le chantier qui s'est trompé. |  | kaki | H | Idée |  |
| 22 | BTP | Le chantier finit vendredi. On n'a pas dit lequel. |  | noir | H | Idée |  |
| 23 | Couvreur | J'ai pas le vertige, j'ai juste la flemme de redescendre |  | noir | H | Idée | Ton terrain : idéal pour tester |
| 24 | Couvreur | Mon bureau a la plus belle vue de la ville. Et des fientes de pigeon. |  | noir | H | Idée |  |
| 25 | Routier | Ma maison fait 13,60 m. Mon salon a un volant. |  | noir | H | Idée | 13,60 m = longueur d'une remorque standard |
| 26 | Routier | Les ronds-points ont été inventés pour se moquer de moi |  | noir | H | Idée |  |
| 27 | Agriculteur | Je bosse 70 heures par semaine pour qu'on me dise que je pollue |  | kaki | H | Idée |  |
| 28 | Agriculteur | La météo m'a encore menti | Agriculteur, pas devin | kaki | H | Idée |  |
| 29 | Infirmière | Je trouve une veine dans le noir. Pas mes clés. |  | blanc | F | Idée |  |
| 30 | Infirmière | Infirmière : j'ai pas fait pipi depuis 2014 | Pause ? C'est quoi ? | blanc | F | Idée |  |
| 31 | Soignant | Sous-effectif : c'est moi |  | blanc | Mixte | Idée |  |
| 32 | Prof | Je n'ai pas de vacances. J'ai des pauses entre deux réformes. |  | blanc | Mixte | Idée |  |
| 33 | Prof | J'ai répété trois fois la consigne. On m'a demandé ce qu'il fallait faire. |  | blanc | Mixte | Idée |  |
| 34 | Boulanger | Je me lève quand tu rentres de soirée | Boulanger, pas fêtard | noir | H | Idée |  |
| 35 | Cuisinier | Je crie « chaud devant » même à la maison |  | noir | H | Idée |  |
| 36 | Serveur | Je retiens 12 commandes mais pas ton prénom |  | noir | Mixte | Idée |  |
| 37 | Coiffeuse | « Juste les pointes » — traduction : refais-moi tout |  | blanc | F | Idée |  |
| 38 | Coiffeuse | Coiffeuse : psy à 25 €, brushing offert |  | blanc | F | Idée |  |
| 39 | Informaticien | Avez-vous essayé de l'éteindre et de le rallumer ? |  | noir | H | Idée |  |
| 40 | Informaticien | Ça marche sur ma machine |  | noir | H | Idée |  |
| 41 | Informaticien | Non, je ne répare pas l'imprimante de ta tante |  | noir | H | Idée |  |
| 42 | Comptable | C'est pas un bug, c'est un écart de lettrage |  | marine | Mixte | Idée |  |
| 43 | Commercial | Je ne mens pas. J'arrondis. |  | marine | Mixte | Idée |  |
| 44 | Caissière | Vous avez la carte du magasin ? Moi, j'ai plus de patience. |  | blanc | F | Idée |  |
| 45 | Nounou | 4 enfants le jour, 1 mari le soir. Le plus dur, c'est le mari. |  | blanc | F | Idée |  |
| 46 | Chauffeur de bus | Non, je n'attends pas. Le bus d'après existe. |  | noir | H | Idée |  |
| 47 | Provoc – végans | Un barbecue sans viande, c'est un feu de camp |  | noir | H | Idée | Un peu limite |
| 48 | Provoc – végans | Je mange végétarien : la vache mangeait de l'herbe |  | noir | H | Idée | Un peu limite · blague connue, à tester |
| 49 | Provoc – végans | J'ai sauvé une plante aujourd'hui. J'ai mangé le cochon à la place. |  | noir | H | Idée | Un peu limite |
| 50 | Provoc – végans | Invité chez des végans. Depuis, j'ai un saucisson de secours dans la boîte à gants. |  | noir | H | Idée | Un peu limite |
| 51 | Provoc – végans | Moi aussi je mange des plantes : du saucisson aux herbes |  | noir | H | Idée | Un peu limite |
| 52 | Provoc – régime | J'ai commencé un régime à 9 h. Je l'ai fini à l'apéro. |  | noir | Mixte | Idée |  |
| 53 | Provoc – régime | Ce n'est pas du ventre, c'est un hangar à saucisson |  | noir | H | Idée | Autodérision : OK car il parle de lui |
| 54 | Provoc – régime | J'ai des abdos. Ils sont juste protégés par une couche d'isolation. | Norme RE2020 | noir | H | Idée |  |
| 55 | Provoc – apéro | Mon médecin m'a dit de boire plus d'eau. Le pastis, c'est cinq volumes d'eau. |  | noir | H | Idée | Un peu limite · pub Meta parfois refusée sur l'alcool |
| 56 | Provoc – apéro | Mon sport : le lever de coude. Niveau compétition. |  | noir | H | Idée | Pub Meta parfois refusée sur l'alcool |
| 57 | Provoc – écolo | Je roule au diesel et je dors très bien |  | noir | H | Idée | Un peu limite · fait réagir en commentaires |
| 58 | Provoc – Parisiens | Je ne suis pas de Paris. Je suis poli. |  | noir | Mixte | Idée | Marche très bien en province |
| 59 | Provoc – Parisiens | Parisien en vacances ? Ici, on dit bonjour. |  | blanc | Mixte | Idée | À décliner par région |
| 60 | Provoc – jeunes | À ton âge, j'avais pas de wifi. J'avais des genoux. |  | noir | H | Idée |  |
| 61 | Provoc – jeunes | Je ne suis pas vieux. J'ai de la bouteille. |  | noir | H | Idée |  |
| 62 | Provoc – couple | Marié depuis 30 ans. J'ai jamais gagné un débat. Mais j'ai eu la télécommande. Une fois. |  | noir | H | Idée |  |
| 63 | Provoc – couple | Ma belle-mère vient dimanche. J'ai un concours de pétanque à 300 km. |  | noir | H | Idée |  |
| 64 | Provoc – couple (femme) | Je suis une femme simple : un verre de rosé et personne qui parle |  | blanc | F | Idée |  |
| 65 | Provoc – couple (femme) | Je n'écoute pas, je laisse parler. Nuance. |  | blanc | F | Idée |  |
| 66 | Provoc – sport | Le footing, c'est courir sans raison. Moi j'attends qu'on me poursuive. |  | noir | Mixte | Idée |  |
| 67 | Apéro – jeu de mots | Je ne suis pas raciste : j'adore le jaune et le rouge |  | noir | H | Idée | TON IDÉE. Illustration obligatoire (verre de pastis + verre de rouge) pour que le double sens soit compris en 1 seconde. Risque de signalements si lu au premier degré. |
| 68 | Apéro – jeu de mots | Je ne suis pas raciste : j'aime le jaune, le rouge et le rosé | Et le blanc en été | noir | H | Idée | Variante plus sûre de ton idée : le rosé rend le sens évident |
| 69 | Apéro – jeu de mots | Le vin, c'est du raisin. Le raisin, c'est un fruit. Donc c'est ma salade. |  | noir | Mixte | Idée | Illustration : verre de vin + feuille de salade |
| 70 | Apéro – jeu de mots | Le rosé, c'est de l'eau qui a rougi en me voyant |  | blanc | F | Idée | Cible femme, été |
| 71 | Apéro – jeu de mots | Mon groupe sanguin : rouge, positif |  | noir | H | Idée | Illustration : poche de sang façon bouteille |
| 72 | Apéro – jeu de mots | Je ne suis pas alcoolique. Je suis œnologue amateur. |  | noir | H | Idée |  |
| 73 | Apéro – jeu de mots | Le pastis, c'est mon smoothie provençal |  | noir | H | Idée | Illustration : verre de pastis avec paille et parasol |
| 74 | Apéro – jeu de mots | Je fais du yoga : la position du tire-bouchon |  | blanc | Mixte | Idée | Illustration : bonhomme en tire-bouchon |
| 75 | Apéro – jeu de mots | J'ai arrêté de boire. Entre les verres. |  | noir | H | Idée |  |
| 76 | Apéro – jeu de mots | L'apéro, c'est comme une réunion : on sait quand ça commence, jamais quand ça finit |  | noir | Mixte | Idée |  |
| 77 | Apéro – jeu de mots | Je ne vieillis pas. Je me bonifie. Comme le vin, et avec. |  | noir | H | Idée | Très bon cadeau anniversaire 50/60 ans |
| 78 | Apéro – jeu de mots | Mon médecin m'a dit d'arrêter les apéros en semaine. Maintenant, c'est le week-end tous les jours. |  | noir | H | Idée | Cible retraités |
| 79 | Apéro – pastis | Mon médecin m'a dit de manger des tomates. Il a pas précisé lesquelles. |  | noir | H | Idée | Tomate = pastis grenadine. Illustration : verre de pastis rouge avec une feuille de tomate |
| 80 | Apéro – pastis | Une momie, c'est un petit pastis. Moi, je bois des pharaons. |  | noir | H | Idée | Momie = petite dose. Illustration : verre de pastis avec bandelettes et couronne de pharaon |
| 81 | Apéro – pastis | Tomate, perroquet, mauresque : je ne bois pas, je fais mes cinq fruits et légumes |  | noir | H | Idée | Les initiés comprennent tout de suite |
| 82 | Apéro – pastis | Un jaune, c'est cinq volumes d'eau. Je suis le mec le mieux hydraté du village. |  | noir | H | Idée |  |
| 83 | Apéro – pastis | 18 h 30 : je passe au jaune | Et je ne m'arrête pas au rouge | noir | H | Idée | Illustration : feu tricolore avec un verre de pastis à la place de l'orange |
| 84 | Apéro – pastis | Pas de glaçon dans mon pastaga. On n'est pas des sauvages. |  | noir | H | Idée | Débat de comptoir qui fait commenter |
| 85 | Apéro – whisky | Single malt. Comme moi depuis le divorce. |  | noir | H | Idée |  |
| 86 | Apéro – whisky | On the rocks. Comme mon couple. |  | noir | H | Idée | Illustration : verre de whisky avec deux glaçons qui se tournent le dos |
| 87 | Apéro – whisky | Mon whisky a 18 ans. Il a enfin le droit de sortir avec moi. |  | noir | H | Idée |  |
| 88 | Apéro – whisky | Double. Sec. Sans discussion. |  | noir | H | Idée | Daron vénère, très court = très lisible |
| 89 | Apéro – whisky | Un glaçon dans ton whisky ? Et pourquoi pas une paille ? |  | noir | H | Idée |  |
| 90 | Apéro – vin | Mon sport préféré ? Le ballon. De rouge. |  | noir | H | Idée | Illustration : ballon de foot transformé en verre de vin |
| 91 | Apéro – vin | Mon cubi est à moitié plein. Je suis un optimiste. |  | noir | H | Idée | Illustration : cubi souriant |
| 92 | Apéro – vin | Sommelier du cubi | Diplômé de la fontaine à vin | noir | H | Idée | Court et efficace |
| 93 | Apéro – vin | Le vin rouge, c'est bon pour le cœur. J'ai un cœur d'athlète. |  | noir | H | Idée |  |
| 94 | Apéro – vin | Je ne bois que pour les grandes occasions. Comme mardi. |  | noir | Mixte | Idée |  |
| 95 | Apéro – bière | Chacun son point de vue. Moi, c'est une pinte de vue. |  | noir | H | Idée | Illustration : pinte avec des jumelles |
| 96 | Apéro – bière | J'ai pas de bide. J'ai un fût. |  | noir | H | Idée | Illustration : fût de bière en coupe |
| 97 | Apéro – bière | Sans gluten ? La bière, c'est liquide, ça compte pas. |  | noir | H | Idée |  |
| 98 | Apéro – digestif | Je mange une pomme par jour. En calva. |  | noir | H | Idée | Illustration : pomme avec un bouchon de bouteille |
| 99 | Apéro – digestif | Le trou normand, c'est le seul trou que je creuse | Jardinier du dimanche | noir | H | Idée |  |
| 100 | Apéro – digestif | Le digestif, c'est pas de l'alcool. C'est un médicament. | Sur ordonnance de tonton | noir | H | Idée |  |
| 101 | Apéro – comptoir | Ce soir, Sam, c'est pas moi |  | noir | H | Idée | Référence aux campagnes Sécurité routière : tout le monde comprend. Positif (il ne conduit pas) |
| 102 | Apéro – comptoir | Je paie toujours ma tournée. À crédit. |  | noir | H | Idée |  |
| 103 | Apéro – comptoir | Le dernier pour la route. La route a dit non. |  | noir | H | Idée |  |

### Formules
| Formule | Exemple | Pourquoi ça marche |
|---|---|---|
| Si la vie était un(e) [objet du métier], je serais [le truc pourri que tout le monde connaît] | Si la vie était une voiture, je serais ton 1.2 à courroie humide | Ta formule : la blague d'initié |
| C'est pas moi, c'est [le collègue d'avant / le beau-frère / le stagiaire] | C'est pas moi qui ai fait ça. C'est le plombier d'avant. | Marche dans presque tous les métiers manuels |
| « [Phrase que le client dit toujours] » — traduction : [la vérité] | « Juste les pointes » — traduction : refais-moi tout | Les phrases de clients sont de l'or |
| Je [exploit du métier]. Pas [truc banal]. | Je trouve une veine dans le noir. Pas mes clés. | Contraste héroïque / ridicule |
| [Métier] : je [verbe] [chose] depuis [année] | Je refais l'installation du beau-frère depuis 1998 | L'ancienneté qui fait sourire |
| Je ne suis pas [défaut]. Je suis [métier]. | Je ne suis pas râleur. Je suis routier. | Simple, fonctionne pour tous les métiers |
| Mode [métier] activé : [liste avec cases cochées] | Mode papy activé : sieste faite, apéro fait… | Style « fiche » automatique |
| [Phrase sérieuse]. [Chute absurde]. | Le chantier finit vendredi. On n'a pas dit lequel. | La chute courte après le point |
| Provoc sur un choix de vie (végan, régime, sport, Parisiens, diesel) | Un barbecue sans viande, c'est un feu de camp | Fait réagir : les « contre » commentent, l'algorithme pousse la vidéo |
| Jeu de mots + illustration qui donne la clé | En vieillissant ma vue baisse, j'ai opté pour des verres progressifs (dessin de verres de vin) | Le dessin fait comprendre la blague en 1 seconde : 82 000 likes et 19 000 partages sur leur page |
| Argot de comptoir (jaune, momie, tomate, perroquet, mauresque, cubi, ballon de rouge, trou normand) | Mon médecin m'a dit de manger des tomates. Il a pas précisé lesquelles. | Les vrais connaisseurs se sentent visés : ils partagent. Et ça remplace les noms de marques interdits |

## Étape 5 — Créer la commande `/tshirts`
Écris `.claude/skills/tshirts/SKILL.md` avec ce contenu exact :
````markdown
---
name: tshirts
description: Génère les designs de t-shirts humour à partir des slogans validés de banque-slogans.xlsx, et prépare pour chacun un dossier prêt à mettre sur Printful (fichiers d'impression, aperçus, fiche produit, prompts illustration et vidéo).
argument-hint: "[optionnel : un slogan à ajouter directement]"
---

# /tshirts — de l'idée au dossier prêt à publier

Maxime ne code pas. Tu fais tout, tu lui montres le résultat, il choisit.

## 0. Si un slogan est passé en argument
`$ARGUMENTS` non vide → ajoute-le à la fin de l'onglet Slogans de `banque-slogans.xlsx` (statut « Validé », niche, cible et couleur devinées) avant de continuer.

## 1. Lire les slogans à traiter
- Ouvre `banque-slogans.xlsx`, onglet **Slogans**, avec openpyxl.
- Prends les lignes au statut **Validé** (une fois traitées, elles passent en « Design fait », donc rien n'est fait deux fois).
- S'il n'y en a aucune, dis-le en une phrase et arrête-toi.

## 2. Écrire la fiche design (designs.json)
Pour chaque slogan, ajoute une entrée :
- `id` : slug court (ex. `saucisson-aux-herbes`).
- `tshirt` : `noir`, `blanc`, `kaki`, `marine`, `sable` ou `gris` (colonne Couleur, sinon noir pour les hommes, blanc pour les femmes).
- `lignes` : 3 à 6 lignes courtes. Niveaux : `petit` (mise en place), `grand` (texte principal), `accent` (la chute, en couleur). La chute va toujours en dernier et en `accent`.
- `icone` : un fichier de `icons/` (sans .svg). S'il en manque un, télécharge-le chez tabler-icons (MIT) : `https://raw.githubusercontent.com/tabler/tabler-icons/main/icons/outline/<nom>.svg`. Marque la ligne qui précède l'icône avec `"icone_apres": true`.
- `arc_haut`, `arc_bas` (25 caractères max) et `centre` (1 ou 2 lignes) pour le style écusson.
- `chute` : petite phrase manuscrite en bas, facultative.
- Slogan en forme de liste → `titre` + `liste` (`etat` : `ok`, `non` ou `jauge` avec `pct`).
- **Illustration** : si le slogan gagne à avoir un dessin (un personnage, un objet qui fait la blague), regarde si `illustrations/<id>.png` existe. Si oui, mets `"illustration": "<id>.png"` et `"illustration_apres": true` sur la ligne qui précède le dessin. Sinon, écris le prompt dans le dossier (étape 4) et génère quand même les versions sans illustration.

## 3. Générer
`python3 generate.py` — il ne refait que les nouveaux. Pour refaire un design : `python3 generate.py --only <id>`.
Ouvre `planche-du-jour.jpg` et vérifie toi-même : texte lisible, rien qui déborde, accents corrects. Corrige le découpage et relance si besoin.

## 4. Compléter chaque dossier `sortie/<id>/`
Le script y a déjà mis `impression_<style>.png` (4500 x 5400 px, transparent, 300 dpi), `apercu_<style>.jpg` et `planche.jpg`. Ajoute :

**fiche-produit.md**
- Titre produit (60 caractères max, avec le métier ou la niche : « T-shirt Pétanque Humour – Je sers l'apéro »)
- Description (3 phrases drôles + « Idée cadeau pour… » + matière et entretien standard)
- 13 tags Etsy (20 caractères max chacun)
- Couleur de t-shirt conseillée, et le style d'impression conseillé parmi les variantes
- Prix conseillé : 24,90 € (29,90 € pour un sweat)

**prompt-illustration.txt** (seulement si pas encore d'illustration)
Prompt en anglais, toujours dans le style maison :
« T-shirt print illustration, vintage cartoon mascot style with thick black outlines and flat limited colors (cream, mustard yellow, brick red, dark brown): [le sujet drôle]. Isolated on plain white background, centered, no text, no lettering, clean screen-print look. »
Maxime le génère (Canva, ChatGPT…) et dépose le PNG dans `illustrations/<id>.png`, puis relance `/tshirts`.

**video.md** — 3 idées de vidéo de 6 à 10 secondes, chacune avec :
- Le prompt image (en anglais) : personnage vu de dos ou de trois-quarts dos, qui porte le t-shirt (couleur exacte), dans un décor français sans aucun logo (supermarché, terrain de pétanque, garage, chantier, barbecue, camping, terrasse de café). Look photo smartphone, lumière naturelle.
- Le prompt vidéo (en anglais) : un seul mouvement simple et lent, caméra tenue à la main, « the t-shirt print stays sharp and unchanged ».
- La légende à incruster (une phrase + 1 émoji) qui complète la blague sans la répéter.
- Le texte du post Facebook (2 lignes + appel à l'action vers la boutique).
Personnage récurrent par défaut : **le daron un peu vénère** — 55-65 ans, cheveux gris, lunettes, short cargo, caddie ou verre à la main, l'air de quelqu'un qu'on n'emmerde pas. Variantes : la mamie qui a du caractère, le collègue de chantier.

## 5. Mettre à jour et résumer
- Passe le statut de ces lignes à « Design fait » dans `banque-slogans.xlsx`.
- Résume à Maxime en 3 lignes maximum : combien de designs, lesquels attendent une illustration, et le chemin de `planche-du-jour.jpg`.

## Règles de contenu
- Jamais de marque, constructeur, enseigne, logo, personnage connu, parole de chanson, réplique de film, ni slogan recopié d'une autre boutique.
- Provoc OK sur les choix de vie (végans, régime, diesel, Parisiens, belle-mère). Jamais sur l'origine, la religion, le handicap, l'orientation ou le physique des autres.
- Orthographe et accents parfaits : c'est imprimé.

````
Crée aussi un `CLAUDE.md` court qui décrit le dossier et renvoie vers ce skill.

## Étape 6 — Connecter Canva (pour les illustrations)
1. Ajoute le serveur MCP officiel de Canva : `claude mcp add --transport http canva https://mcp.canva.com/mcp` (si la commande a changé, vérifie sur https://www.canva.dev/docs/mcp/).
2. Demande à Maxime de taper `/mcp` et de se connecter à son compte Canva (une seule fois).
3. Pour chaque design qui a un `prompt-illustration.txt` : génère l'image avec l'outil de génération d'image de Canva, en gardant toujours le style maison (dessin vintage, gros contours noirs, couleurs à plat crème / jaune moutarde / rouge brique / brun, fond blanc uni, sans texte).
4. Récupère-la en **haute définition (2048 px minimum)** : place l'image dans un design Canva carré et exporte-le en PNG grande taille. Enregistre-la sous `illustrations/<id>.png`, ajoute `"illustration": "<id>.png"` dans `designs.json`, puis `python3 generate.py --only <id>`.
5. Le fond blanc est retiré par le script : pas besoin de Canva Pro pour ça. Si un outil Canva demande un abonnement payant, arrête-toi et dis à Maxime lequel et pourquoi, avant de continuer.
6. Commence par l'illustration du saucisson musclé (`saucisson-aux-herbes`) : un saucisson sec en personnage, petits bras qui font les biceps, lunettes de soleil noires, petit béret, sourire satisfait, debout sur une planche à découper.

## Étape 7 — Première mission : tous les designs
1. Lance `python3 generate.py` : il fabrique les designs de `designs.json`.
2. Puis traite **toute la banque** (sauf les lignes « Abandonné » et celles déjà dans designs.json), **par lots de 10**, en suivant le skill `/tshirts` : fiche design → génération → vérification de `planche-du-jour.jpg` → `fiche-produit.md`, `video.md` et, si utile, `prompt-illustration.txt` dans chaque `sortie/<id>/`.
3. Après chaque lot, passe les lignes en « Design fait » et dis à Maxime en une ligne où en est le travail.
4. À la fin : liste des designs qui attendent une illustration, puis génère ces illustrations avec Canva (étape 6).

## Règles qui ne bougent jamais
- **Aucune marque** sur un t-shirt : pas de Ricard, 51, PureTech, constructeur, enseigne, logo, personnage connu, parole de chanson, réplique de film, ni slogan recopié d'une autre boutique. Pour l'alcool, on utilise l'argot de comptoir (jaune, momie, tomate, cubi, ballon de rouge…).
- Le slogan n°7 (« moteur PureTech ») : **ne pas le générer**, utiliser la version sans marque (n°8).
- Provoc OK sur les choix de vie (végans, régime, diesel, Parisiens, belle-mère). Jamais sur l'origine, la religion, le handicap, l'orientation ou le physique des autres.
- Les slogans « je ne suis pas raciste… jaune et rouge » : **toujours avec une illustration** de verres (pastis + vin), sinon la blague peut être mal lue.
- Orthographe et accents parfaits : c'est imprimé.
- Fichiers d'impression : 4500 x 5400 px, fond transparent, 300 dpi (format Printful).
