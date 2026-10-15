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

# styles uniques (étiquette, affiche, panneau…) : voir styles_uniques.py
import styles_uniques
STYLES.update(styles_uniques.charger(sys.modules[__name__]))


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
        alerte = os.path.join(folder, "ATTENTION-BASSE-DEF.txt")
        if d["id"] in styles_uniques.BASSE_DEF:
            open(alerte, "w", encoding="utf-8").write(
                "Illustration en basse définition (aperçu Canva 200 px) : NE PAS IMPRIMER.\n"
                f"Télécharger l'image HD depuis Canva (voir illustrations/canva.json) vers illustrations/{d['id']}.png,\n"
                f"puis : python3 generate.py --only {d['id']}\n")
        elif os.path.exists(alerte):
            os.remove(alerte)
        contact_sheet(thumbs, os.path.join(folder, "planche.jpg"))
        day += thumbs
    if day:
        contact_sheet(day, os.path.join(ROOT, "planche-du-jour.jpg"))
        print("planche-du-jour.jpg :", len(day), "variantes")
    else:
        print("Rien de nouveau à générer.")


if __name__ == "__main__":
    main()

