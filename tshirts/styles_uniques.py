"""Styles « uniques » : une mise en page pensée pour chaque blague (étiquette, affiche, panneau…).

Chargés par generate.py. Chaque design choisit son style dans designs.json avec "styles": ["etiquette"]
et donne ses textes dans "u": {...} (voir chaque fonction pour les clés attendues).
Illustration : illustrations/<id>.png (haute définition, Canva) sinon illustrations/basse-def/<id>.jpg
(aperçu 200 px, juste pour juger la mise en page : NE PAS imprimer).
"""
import math, os, random
from PIL import Image, ImageChops, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))
NOUVELLES_POLICES = {
    "typo": "SpecialElite-Regular.ttf", "comic": "Bangers-Regular.ttf", "pacifico": "Pacifico-Regular.ttf",
    "courier": "CourierPrime-Regular.ttf", "courierb": "CourierPrime-Bold.ttf", "ultra": "Ultra-Regular.ttf",
    "lobster": "Lobster-Regular.ttf", "bungee": "Bungee-Regular.ttf", "sancreek": "Sancreek-Regular.ttf",
    "gothique": "UnifrakturMaguntia-Book.ttf", "playfair": "PlayfairDisplay.ttf",
    "playfairi": "PlayfairDisplay-Italic.ttf",
}
BASSE_DEF = set()  # designs fabriqués avec une illustration basse définition
g = None           # module generate (injecté par charger)


# ------------------------------------------------------------------ outils
def police(nom, taille, poids=None):
    f = ImageFont.truetype(g.FONTS[nom], max(8, int(taille)))
    if poids:
        try:
            f.set_variation_by_name(poids)
        except Exception:
            pass
    return f


def T(txt, nom, fill, w, h, stroke=0, sfill=None, poids=None, tracking=0.0):
    """Texte qui tient dans w x h (le plus grand possible), recadré au plus près."""
    def rend(size):
        size = max(8, int(size))
        f = police(nom, size, poids)
        tr = size * tracking
        largeurs = [f.getlength(c) for c in txt]
        W = int(sum(largeurs) + tr * max(0, len(txt) - 1) + size + 2 * stroke * size / 100)
        img = Image.new("RGBA", (W + size, int(size * 2.4)), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        x = size // 2
        sw = int(stroke * size / 100)
        for c, lw in zip(txt, largeurs):
            d.text((x, int(size * 0.4)), c, font=f, fill=fill, stroke_width=sw, stroke_fill=sfill or fill)
            x += lw + tr
        return img.crop(img.getbbox()) if img.getbbox() else img
    p = rend(300)
    s = 300 * min(w / p.width, h / p.height)
    img = rend(s)
    if img.width > w or img.height > h:
        r = min(w / img.width, h / img.height)
        img = img.resize((max(1, int(img.width * r)), max(1, int(img.height * r))), Image.LANCZOS)
    return img


def para(txt, nom, fill, largeur, taille, interligne=1.25, centre=True, poids=None):
    """Paragraphe à la taille donnée, retour à la ligne automatique."""
    f = police(nom, taille, poids)
    mots, lignes, cur = txt.split(), [], ""
    for m in mots:
        essai = (cur + " " + m).strip()
        if f.getlength(essai) <= largeur:
            cur = essai
        else:
            lignes.append(cur); cur = m
    lignes.append(cur)
    lh = int(taille * interligne)
    img = Image.new("RGBA", (largeur, lh * len(lignes) + taille), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, l in enumerate(lignes):
        x = (largeur - f.getlength(l)) / 2 if centre else 0
        d.text((x, i * lh), l, font=f, fill=fill)
    return img.crop(img.getbbox())


def illus(d, largeur, hauteur=None):
    """Illustration détourée (fond blanc retiré), à la largeur voulue."""
    hd = os.path.join(ROOT, "illustrations", d.get("illustration") or f"{d['id']}.png")
    bd = os.path.join(ROOT, "illustrations", "basse-def", f"{d['id']}.jpg")
    if os.path.exists(hd):
        im = Image.open(hd).convert("RGB")
    elif os.path.exists(bd):
        im = Image.open(bd).convert("RGB"); BASSE_DEF.add(d["id"])
    else:
        return None
    key = (255, 0, 255)
    work = im.copy()
    for xy in [(0, 0), (work.width - 1, 0), (0, work.height - 1), (work.width - 1, work.height - 1)]:
        ImageDraw.floodfill(work, xy, key, thresh=45)
    diff = ImageChops.difference(work, Image.new("RGB", work.size, key)).convert("L")
    mask = diff.point(lambda v: 0 if v < 8 else 255)
    r = largeur / im.width
    if hauteur and im.height * r > hauteur:
        r = hauteur / im.height
    size = (int(im.width * r), int(im.height * r))
    out = im.resize(size, Image.LANCZOS).convert("RGBA")
    out.putalpha(mask.resize(size, Image.LANCZOS).filter(ImageFilter.GaussianBlur(max(1, r / 3))))
    return out.crop(out.getbbox())


def colle(fond, img, x, y, centre_x=True):
    if img is None:
        return 0
    fond.alpha_composite(img, (int(x - img.width / 2) if centre_x else int(x), int(y)))
    return img.height


def vstack(parts, gap, largeur=None):
    parts = [p for p in parts if p is not None]
    w = largeur or max(p.width for p in parts)
    h = sum(p.height for p in parts) + gap * (len(parts) - 1)
    out = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    y = 0
    for p in parts:
        out.alpha_composite(p, ((w - p.width) // 2, y)); y += p.height + gap
    return out


def papier(w, h, couleur, seed, bords="dechire"):
    """Feuille de papier avec bords déchirés ou dentelés (ticket)."""
    rnd = random.Random(seed)
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    if bords == "dechire":
        pts, pas = [], 60
        for x in range(0, w + 1, pas): pts.append((x, rnd.randint(0, 40)))
        for y in range(0, h + 1, pas): pts.append((w - rnd.randint(0, 40), y))
        for x in range(w, -1, -pas): pts.append((x, h - rnd.randint(0, 40)))
        for y in range(h, -1, -pas): pts.append((rnd.randint(0, 40), y))
        d.polygon(pts, fill=couleur)
    else:  # dents de ticket en haut et en bas
        dent = 70
        pts = [(0, dent)]
        for x in range(0, w + 1, dent * 2): pts += [(x, dent), (x + dent, 0)]
        pts += [(w, dent), (w, h - dent)]
        for x in range(w, -1, -dent * 2): pts += [(x, h - dent), (x - dent, h)]
        pts += [(0, h - dent)]
        d.polygon(pts, fill=couleur)
    return img


def tache(img, seed, force=0.25):
    return g.distress(img, seed, force)


# ------------------------------------------------------------------ 1. ÉTIQUETTE (saucisson, vin…)
def style_etiquette(d, pal):
    """u: haut, nom, sous_nom, mention, bas"""
    u = d["u"]
    CR, BR, RG, MO = "#EFE3C6", "#3B2416", "#A3271F", "#D9A21B"
    W, H = 3700, 4300
    img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    dr = ImageDraw.Draw(img)
    c = 260
    forme = [(c, 0), (W - c, 0), (W, c), (W, H - c), (W - c, H), (c, H), (0, H - c), (0, c)]
    dr.polygon(forme, fill=CR)
    m = 90
    dr.polygon([(c + m * .4, m), (W - c - m * .4, m), (W - m, c + m * .4), (W - m, H - c - m * .4),
                (W - c - m * .4, H - m), (c + m * .4, H - m), (m, H - c - m * .4), (m, c + m * .4)],
               outline=BR, width=34)
    m2 = 150
    dr.rectangle([m2 + 60, m2 + 60, W - m2 - 60, H - m2 - 60], outline=BR, width=12)
    y = 300
    y += colle(img, T(u["haut"].upper(), "playfair", BR, 2800, 190, poids="Bold", tracking=0.08), W / 2, y) + 70
    il = illus(d, 2300, 1900)
    y += colle(img, il, W / 2, y) + 40
    # bandeau ruban rouge
    rb = T(u["nom"].upper(), "ultra", CR, 2900, 520)
    rh = rb.height + 200
    dr.polygon([(250, y), (W - 250, y), (W - 420, y + rh / 2), (W - 250, y + rh), (250, y + rh), (420, y + rh / 2)],
               fill=RG)
    colle(img, rb, W / 2, y + 100); y += rh + 60
    y += colle(img, T(u["sous_nom"], "lobster", RG, 2600, 480), W / 2, y) + 70
    dr.line([(700, y), (W - 700, y)], fill=MO, width=16); y += 70
    y += colle(img, T(u["mention"].upper(), "playfair", BR, 3000, 150, poids="Bold", tracking=0.06), W / 2, y) + 50
    colle(img, T(u["bas"], "playfairi", BR, 2400, 170, poids="Medium"), W / 2, y)
    img = img.crop(img.getbbox())
    return tache(img, d["id"] + "e", 0.14)


# ------------------------------------------------------------------ 2. COUCHER DE SOLEIL 70s
def style_coucher(d, pal):
    """u: haut (script), bas1, bas2"""
    u = d["u"]
    W = 3900
    R = 1500
    soleil = Image.new("RGBA", (2 * R, 2 * R), (0, 0, 0, 0))
    sd = ImageDraw.Draw(soleil)
    cols = ["#F6C445", "#F3A93A", "#EE8A33", "#E5672E", "#D44A2C", "#B8352B"]
    for i, ccol in enumerate(cols):  # bandes horizontales
        y0 = int(2 * R * i / len(cols))
        sd.rectangle([0, y0, 2 * R, int(2 * R * (i + 1) / len(cols))], fill=ccol)
    for k in range(4):  # coupures façon affiche 70s, de plus en plus épaisses
        yy = int(R * 1.15 + k * R * 0.22)
        sd.rectangle([0, yy, 2 * R, yy + 30 + k * 26], fill=(0, 0, 0, 0))
    m = Image.new("L", soleil.size, 0)
    ImageDraw.Draw(m).ellipse([0, 0, 2 * R, 2 * R], fill=255)
    a = ImageChops.multiply(soleil.getchannel("A"), m)
    soleil.putalpha(a)
    scene = Image.new("RGBA", (W, 2 * R + 300), (0, 0, 0, 0))
    scene.alpha_composite(soleil, ((W - 2 * R) // 2, 0))
    il = illus(d, 3000, 2300)
    if il:
        scene.alpha_composite(il, ((W - il.width) // 2, scene.height - il.height))
    haut = T(u["haut"], "pacifico", pal["accent"], 3800, 900, stroke=4, sfill=pal["tee"])
    b1 = T(u["bas1"].upper(), "bebas", pal["ink"], 3300, 420, tracking=0.06)
    b2 = T(u["bas2"].upper(), "bungee", pal["accent"], 3600, 420)
    return vstack([haut, scene.crop(scene.getbbox()), b1, b2], 80)


# ------------------------------------------------------------------ 3. AVIS DE RECHERCHE
def style_recherche(d, pal):
    """u: titre, nom, motif, recompense, bas"""
    u = d["u"]
    PA, EN, RG = "#E8D7B0", "#2B1D12", "#8E2A1B"
    W = 3500
    regle = Image.new("RGBA", (W - 600, 14), EN)
    contenu = vstack([T(u["titre"].upper(), "rye", EN, 3000, 520), regle,
                      illus(d, 2200, 2100),
                      T(u["nom"].upper(), "sancreek", RG, 3000, 520),
                      para(u["motif"], "typo", EN, 2900, 130), regle,
                      T(u["recompense"].upper(), "rye", EN, 2900, 230),
                      T(u["bas"], "typo", RG, 2900, 170)], 60)
    H = contenu.height + 560
    img = papier(W, H, PA, d["id"])
    ImageDraw.Draw(img).rectangle([140, 140, W - 140, H - 140], outline=EN, width=22)
    img.alpha_composite(contenu, ((W - contenu.width) // 2, 280))
    return tache(img, d["id"] + "w", 0.3)


# ------------------------------------------------------------------ 4. PANNEAU ROUTIER
def style_panneau(d, pal):
    """u: panonceau, lignes (liste), accent"""
    u = d["u"]
    W = 3400
    h = int(W * math.sqrt(3) / 2)
    tri = Image.new("RGBA", (W, h), (0, 0, 0, 0))
    td = ImageDraw.Draw(tri)
    td.polygon([(W / 2, 0), (W, h), (0, h)], fill="#C8102E")
    m = 300  # épaisseur du bord rouge
    td.polygon([(W / 2, m * 2), (W - m * 1.73, h - m), (m * 1.73, h - m)], fill="#FFFFFF")
    il = illus(d, int(W * 0.5), int(h * 0.5))
    if il:
        tri.alpha_composite(il, ((W - il.width) // 2, int(h * 0.88) - il.height))
    pan_t = T(u["panonceau"].upper(), "bungee", "#1E1E1E", 1900, 240)
    pan = Image.new("RGBA", (pan_t.width + 260, pan_t.height + 200), (0, 0, 0, 0))
    ImageDraw.Draw(pan).rounded_rectangle([0, 0, pan.width - 1, pan.height - 1], 40, fill="#FFFFFF",
                                          outline="#1E1E1E", width=30)
    pan.alpha_composite(pan_t, (130, 100))
    lignes = [T(l.upper(), "bungee", pal["ink"], 3800, 380) for l in u["lignes"]]
    acc = T(u["accent"].upper(), "bungee", pal["accent"], 3800, 600)
    return vstack([tri, pan, Image.new("RGBA", (10, 60))] + lignes + [acc], 50)


# ------------------------------------------------------------------ 5. CASE DE BD
def style_bd(d, pal):
    """u: cartouche, bulle, bas"""
    u = d["u"]
    W, H = 3800, 3600
    case = Image.new("RGBA", (W, H), "#F5EBD3")
    cd = ImageDraw.Draw(case)
    for yy in range(0, H, 90):  # trame de points
        for xx in range(0, W, 90):
            r = 10 + 22 * (yy / H)
            ox = 45 if (yy // 90) % 2 else 0
            cd.ellipse([xx + ox - r, yy - r, xx + ox + r, yy + r], fill="#F2C14E")
    il = illus(d, 3200, 2700)
    if il:
        case.alpha_composite(il, ((W - il.width) // 2, H - il.height))
    cd.rectangle([0, 0, W - 1, H - 1], outline="#111111", width=50)
    cart = T(u["cartouche"].upper(), "comic", "#111111", 2400, 260)
    cw, ch = cart.width + 160, cart.height + 140
    cd.rectangle([25, 25, 25 + cw, 25 + ch], fill="#FFF3A6", outline="#111111", width=24)
    case.alpha_composite(cart, (105, 95))
    bt = T(u["bulle"].upper(), "comic", "#111111", 1500, 300)
    bw, bh = bt.width + 260, bt.height + 220
    bx, by = W - bw - 120, ch + 150
    cd.ellipse([bx, by, bx + bw, by + bh], fill="#FFFFFF", outline="#111111", width=22)
    cd.polygon([(bx + bw * .3, by + bh - 30), (bx + bw * .15, by + bh + 260), (bx + bw * .5, by + bh - 20)],
               fill="#FFFFFF", outline="#111111")
    cd.line([(bx + bw * .3, by + bh - 12), (bx + bw * .15, by + bh + 260), (bx + bw * .5, by + bh - 5)],
            fill="#111111", width=22)
    case.alpha_composite(bt, (bx + 130, by + 110))
    case = case.rotate(-2, resample=Image.BICUBIC, expand=True)
    bas = T(u["bas"].upper(), "comic", pal["accent"], 3600, 700, stroke=6, sfill="#111111")
    return vstack([case, bas], 120)


# ------------------------------------------------------------------ 6. SACHET DE GRAINES
def style_graines(d, pal):
    """u: marque, variete, slogan, sous, infos (liste de couples)"""
    u = d["u"]
    CR, VE, RG, EN = "#F1E6C8", "#2F5D3A", "#B8352B", "#2A2118"
    W, H = 3300, 4900
    img = Image.new("RGBA", (W, H), CR)
    dr = ImageDraw.Draw(img)
    dr.rectangle([0, 0, W, 600], fill=VE)
    colle(img, T(u["marque"].upper(), "playfair", CR, 2700, 300, poids="Black", tracking=0.1), W / 2, 150)
    dr.polygon([(0, 600), (W, 600), (W, 680), (0, 680)], fill=RG)
    y = 760
    y += colle(img, T(u["variete"].upper(), "typo", EN, 2800, 160), W / 2, y) + 30
    il = illus(d, 2600, 2100)
    y += colle(img, il, W / 2, y) + 40
    y += colle(img, T(u["slogan"], "lobster", RG, 3000, 520), W / 2, y) + 30
    y += colle(img, T(u["sous"].upper(), "playfair", EN, 3000, 260, poids="Black"), W / 2, y) + 60
    dr.line([(200, y), (W - 200, y)], fill=EN, width=10); y += 40
    for k, v in u["infos"]:
        t = T(f"{k} : {v}", "typo", EN, 2900, 120)
        colle(img, t, W / 2, y); y += t.height + 35
    img = img.crop((0, 0, W, min(H, y + 120)))
    ImageDraw.Draw(img).rectangle([0, 0, img.width - 1, img.height - 1], outline=EN, width=24)
    return tache(img, d["id"] + "g", 0.16)


# ------------------------------------------------------------------ 7. TAMPON
def style_tampon(d, pal):
    """u: tape (liste de lignes machine à écrire), tampon (2 lignes), bas"""
    u = d["u"]
    tape = [T(l, "typo", pal["ink"], 3600, 300) for l in u["tape"]]
    il = illus(d, 2000, 2000)
    rouge = "#C8102E" if pal["tee"] != "#1C1C1E" else "#E23A3A"
    t1 = T(u["tampon"][0].upper(), "blackops", rouge, 2900, 520) if "blackops" in g.FONTS else \
        T(u["tampon"][0].upper(), "stencil", rouge, 2900, 520)
    t2 = T(u["tampon"][1].upper(), "stencil", rouge, 2900, 300)
    st = vstack([t1, t2], 50)
    box = Image.new("RGBA", (st.width + 360, st.height + 300), (0, 0, 0, 0))
    bd = ImageDraw.Draw(box)
    bd.rounded_rectangle([0, 0, box.width - 1, box.height - 1], 60, outline=rouge, width=46)
    bd.rounded_rectangle([60, 60, box.width - 61, box.height - 61], 40, outline=rouge, width=16)
    box.alpha_composite(st, (180, 150))
    box = tache(box, d["id"] + "t", 0.45).rotate(9, resample=Image.BICUBIC, expand=True)
    haut = vstack(tape, 40)
    scene = Image.new("RGBA", (3900, (il.height if il else 0) + box.height - 500), (0, 0, 0, 0))
    if il:
        scene.alpha_composite(il, ((3900 - il.width) // 2, 0))
    scene.alpha_composite(box, ((3900 - box.width) // 2, scene.height - box.height))
    bas = T(u["bas"], "marker", pal["accent2"], 2800, 300)
    return vstack([haut, scene, bas], 80)


# ------------------------------------------------------------------ 8. DIPLÔME
def style_diplome(d, pal):
    """u: titre, sous_titre, decerne, specialite (2 lignes), signature"""
    u = d["u"]
    PA, EN, OR, RG = "#F3EAD3", "#2B2B2B", "#B08D3C", "#9E2B25"
    W, H = 3900, 4700
    img = Image.new("RGBA", (W, H), PA)
    dr = ImageDraw.Draw(img)
    dr.rectangle([60, 60, W - 60, H - 60], outline=OR, width=40)
    dr.rectangle([150, 150, W - 150, H - 150], outline=EN, width=10)
    for cx, cy in [(150, 150), (W - 150, 150), (150, H - 150), (W - 150, H - 150)]:
        dr.ellipse([cx - 70, cy - 70, cx + 70, cy + 70], fill=OR)
    y = 300
    y += colle(img, T(u["titre"], "gothique", EN, 3200, 700), W / 2, y) + 30
    y += colle(img, T(u["sous_titre"], "playfairi", RG, 3000, 330, poids="Bold"), W / 2, y) + 40
    y += colle(img, T(u["decerne"].upper(), "playfair", EN, 3000, 120, poids="Medium", tracking=0.12), W / 2, y) + 40
    il = illus(d, 2400, 1700)
    y += colle(img, il, W / 2, y) + 50
    for l in u["specialite"]:
        t = T(l, "playfair", EN, 3300, 300, poids="Black")
        colle(img, t, W / 2, y); y += t.height + 30
    y += 60
    dr.line([(400, y + 160), (1700, y + 160)], fill=EN, width=8)
    colle(img, T(u["signature"], "script", "#24407A", 1400, 260), 1050, y - 20)
    # sceau
    sx, sy, r = W - 900, y + 120, 330
    pts = [(sx + (r if k % 2 == 0 else r * .82) * math.cos(math.pi * k / 18),
            sy + (r if k % 2 == 0 else r * .82) * math.sin(math.pi * k / 18)) for k in range(36)]
    dr.polygon([(sx - 150, sy + 150), (sx - 260, sy + 560), (sx - 110, sy + 470), (sx - 30, sy + 600), (sx, sy)], fill=RG)
    dr.polygon([(sx + 150, sy + 150), (sx + 260, sy + 560), (sx + 110, sy + 470), (sx + 30, sy + 600), (sx, sy)], fill=RG)
    dr.polygon(pts, fill=RG)
    dr.ellipse([sx - 220, sy - 220, sx + 220, sy + 220], outline=PA, width=14)
    colle(img, T("100 %", "anton", PA, 300, 200), sx, sy - 100)
    img = img.crop((0, 0, W, min(H, sy + 700)))
    return tache(img, d["id"] + "d", 0.12)


# ------------------------------------------------------------------ 9. LETTRAGE UNIVERSITÉ (en arc)
def arquer(img, fleche):
    """Courbe un texte en arche (colonnes décalées selon une parabole)."""
    w, h = img.size
    out = Image.new("RGBA", (w, h + fleche), (0, 0, 0, 0))
    for x in range(0, w, 4):
        t = (x / w) * 2 - 1
        dy = int(fleche * t * t)
        out.alpha_composite(img.crop((x, 0, min(w, x + 4), h)), (x, dy))
    return out


def style_college(d, pal):
    """u: arc, sous, bas1, bas2"""
    u = d["u"]
    ar = T(u["arc"].upper(), "bungee", pal["accent"], 3800, 900, stroke=7, sfill=pal["ink"])
    ombre = T(u["arc"].upper(), "bungee", pal["accent2"], 3800, 900, stroke=7, sfill=pal["accent2"])
    bloc = Image.new("RGBA", (ar.width + 60, ar.height + 60), (0, 0, 0, 0))
    bloc.alpha_composite(ombre, (50, 50)); bloc.alpha_composite(ar, (0, 0))
    bloc = arquer(bloc, 420)
    sous = T(u["sous"].upper(), "archivo", pal["ink"], 2400, 230, tracking=0.25)
    il = illus(d, 2700, 2300)
    b1 = T(u["bas1"].upper(), "archivo", pal["ink"], 3600, 330)
    b2 = T(u["bas2"], "script", pal["accent"], 3200, 650)
    return vstack([bloc, sous, il, b1, b2], 70)


# ------------------------------------------------------------------ 10. PLAQUE DE RUE
def style_plaque(d, pal):
    """u: dessus, petit, grand, bas"""
    u = d["u"]
    BL, VE, BC = "#1F3B73", "#2E5E3B", "#FFFFFF"
    dessus = T(u["dessus"], "typo", pal["ink"], 3200, 280)
    il = illus(d, 2700, 2300)
    W = 3900
    pt = T(u["petit"].upper(), "oswald", BC, 2800, 260, tracking=0.1)
    gt = T(u["grand"].upper(), "anton", BC, 3300, 900)
    H = pt.height + gt.height + 520
    pl = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pl)
    pd.rounded_rectangle([0, 0, W - 1, H - 1], 120, fill=VE)
    pd.rounded_rectangle([70, 70, W - 71, H - 71], 80, fill=BL)
    pd.rounded_rectangle([130, 130, W - 131, H - 131], 60, outline=BC, width=18)
    for vx in (210, W - 210):
        pd.ellipse([vx - 40, H / 2 - 40, vx + 40, H / 2 + 40], fill="#C9C9C9")
    pl.alpha_composite(pt, ((W - pt.width) // 2, 220))
    pl.alpha_composite(gt, ((W - gt.width) // 2, 220 + pt.height + 80))
    bas = T(u["bas"], "script2", pal["accent"], 3000, 380)
    return vstack([dessus, il, pl, bas], 70)


# ------------------------------------------------------------------ 11. DICTIONNAIRE
def style_dico(d, pal):
    """u: mot, phonetique, sens (liste ; un sens qui commence par ~ est barré), bas"""
    u = d["u"]
    W = 3700
    il = illus(d, 2600, 1800)
    mot = T(u["mot"], "playfair", pal["ink"], 3400, 800, poids="Black")
    ph = T(u["phonetique"], "playfairi", pal["accent"], 2600, 230, poids="Medium")
    parts = [il, mot, ph]
    for i, s in enumerate(u["sens"], 1):
        barre = s.startswith("~")
        s = s.lstrip("~")
        p = para(f"{i}. {s}", "playfair", pal["ink"], W, 230, poids="Medium")
        if barre:
            pd = ImageDraw.Draw(p)
            pd.line([(0, p.height * .55), (p.width, p.height * .5)], fill=pal["accent2"], width=26)
        parts.append(p)
    parts.append(T(u["bas"], "marker", pal["accent2"], 2800, 300).rotate(2, resample=Image.BICUBIC, expand=True))
    return vstack(parts, 90)


# ------------------------------------------------------------------ 12. FACTURE / TICKET
def style_ticket(d, pal):
    """u: titre (2 lignes), entete, lignes (couples), total, pied"""
    u = d["u"]
    W = 3100
    titre = vstack([T(u["titre"][0].upper(), "anton", pal["ink"], 3800, 600),
                    T(u["titre"][1].upper(), "anton", pal["accent"], 3800, 700)], 40)
    il = illus(d, 2200, 1600)
    corps = []
    f = police("courier", 120)
    corps.append(T(u["entete"][0].upper(), "courierb", "#1E1E1E", 2600, 200))
    for l in u["entete"][1:]:
        corps.append(T(l, "courier", "#1E1E1E", 2600, 110))
    sep = T("-" * 34, "courier", "#1E1E1E", 2700, 110)
    corps.append(sep)
    for lib, prix in u["lignes"]:
        ln = Image.new("RGBA", (2700, 180), (0, 0, 0, 0))
        ld = ImageDraw.Draw(ln)
        ld.text((0, 20), lib, font=f, fill="#1E1E1E")
        ld.text((2700 - f.getlength(prix), 20), prix, font=f, fill="#1E1E1E")
        corps.append(ln)
    corps.append(sep)
    tot = Image.new("RGBA", (2700, 260), (0, 0, 0, 0))
    fb = police("courierb", 170)
    ImageDraw.Draw(tot).text((0, 30), "TOTAL", font=fb, fill="#1E1E1E")
    ImageDraw.Draw(tot).text((2700 - fb.getlength(u["total"]), 30), u["total"], font=fb, fill="#C8102E")
    corps.append(tot)
    corps.append(T(u["pied"], "courier", "#1E1E1E", 2500, 110))
    c = vstack(corps, 40, 2700)
    tk = papier(W, c.height + 500, "#FBFAF5", d["id"], "ticket")
    tk.alpha_composite(c, ((W - c.width) // 2, 250))
    tk = tk.rotate(-3, resample=Image.BICUBIC, expand=True)
    return vstack([titre, il, tk], 60)


# ------------------------------------------------------------------ 13. PANNEAU DE CHANTIER
def style_chantier(d, pal):
    """u: titre, champs (couples), bas"""
    u = d["u"]
    W = 3700
    il = illus(d, 2500, 2100)
    titre = T(u["titre"].upper(), "anton", "#1E1E1E", 3000, 420)
    rows = [titre]
    for k, v in u["champs"]:
        r = Image.new("RGBA", (3100, 300), (0, 0, 0, 0))
        kt = T(k.upper() + " :", "oswald", "#1E1E1E", 1250, 120, tracking=0.04)
        vt = T(v, "marker", "#1F4E9A", 1850, 230)
        r.alpha_composite(kt, (0, (300 - kt.height) // 2))
        r.alpha_composite(vt, (1250 + 40, (300 - vt.height) // 2))
        rows.append(r)
    c = vstack(rows, 40)
    H = c.height + 600
    pn = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    pd = ImageDraw.Draw(pn)
    pd.rectangle([0, 0, W, H], fill="#F2C230")
    for k in range(-H, W, 260):  # rayures danger
        pd.polygon([(k, 0), (k + 130, 0), (k + 130 + H, H), (k + H, H)], fill="#1E1E1E")
    pd.rectangle([170, 170, W - 170, H - 170], fill="#FFFFFF")
    pn.alpha_composite(c, ((W - c.width) // 2, 300))
    bas = T(u["bas"], "marker", pal["accent"], 3000, 330).rotate(3, resample=Image.BICUBIC, expand=True)
    return vstack([il, pn, bas], 60)


NOUVEAUX = {"etiquette": style_etiquette, "coucher": style_coucher, "recherche": style_recherche,
            "panneau": style_panneau, "bd": style_bd, "graines": style_graines, "tampon": style_tampon,
            "diplome": style_diplome, "college": style_college, "plaque": style_plaque, "dico": style_dico,
            "ticket": style_ticket, "chantier": style_chantier}


def charger(module):
    global g
    g = module
    for k, f in NOUVELLES_POLICES.items():
        g.FONTS[k] = os.path.join(ROOT, "fonts", f)
    g.FONTS.setdefault("rye", g.FONTS["western"])
    g.FONTS.setdefault("blackops", g.FONTS["stencil"])
    return NOUVEAUX
