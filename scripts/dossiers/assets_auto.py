"""Recherche automatique des images / vidéos manquantes, avec licence enregistrée.

Ordre : Wikimedia Commons (photos réelles, licences libres) → Pexels → Pixabay.
- Les portraits de vraies personnes ne viennent QUE de Wikimedia Commons (jamais de banque d'images).
- Les images IA ne sont pas générées ici : elles vont dans la shotlist.
- Ce qui est trouvé va dans assets/auto/<ID>.<ext> ; tes propres fichiers (assets/<ID>.<ext>) passent toujours devant.
- Chaque fichier trouvé est noté dans assets/auto/credits.json (auteur, licence, lien).
"""
import html
import json
import os
import re
import urllib.parse
import urllib.request

EXT_IMAGES = ("jpg", "jpeg", "png", "webp")
EXT_VIDEOS = ("mp4", "mov", "webm")
LICENCES_OK = re.compile(r"^(cc0|cc[ -]by(-sa)?[ -]?[\d.]*|public domain|pd.*|domaine public)", re.I)
UA = "DossiersPipeline/1.0 (chaine YouTube DOSSIERS; contact via GitHub)"


def lire_env(racine):
    env = dict(os.environ)
    chemin = os.path.join(racine, ".env")
    if os.path.exists(chemin):
        for l in open(chemin, encoding="utf-8"):
            if "=" in l and not l.strip().startswith("#"):
                k, v = l.split("=", 1)
                env.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    return env


def fichier_existant(dossier_assets, ident):
    for sous in ("", "auto"):
        for ext in EXT_IMAGES + EXT_VIDEOS:
            p = os.path.join(dossier_assets, sous, f"{ident}.{ext}")
            if os.path.exists(p):
                return p
    return None


def _get(url, headers=None, binaire=False, timeout=25):
    req = urllib.request.Request(url, headers={"User-Agent": UA, **(headers or {})})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read()
    return data if binaire else json.loads(data.decode("utf-8"))


def requetes(asset):
    """« Genève nuit lac / Geneva night lake » → ('Genève nuit lac', 'Geneva night lake')."""
    brut = asset.get("requetes") or ""
    if "/" in brut:
        fr, en = [x.strip() for x in brut.split("/", 1)]
    else:
        fr, en = brut.strip(), ""
    fr = re.sub(r"\(.*?\)", "", fr).replace(",", " ").strip()
    en = re.sub(r"\(.*?\)", "", en).replace(",", " ").strip()
    return fr, en


# ---------------------------------------------------------------- sources
def wikimedia(q):
    url = "https://commons.wikimedia.org/w/api.php?" + urllib.parse.urlencode({
        "action": "query", "generator": "search", "gsrnamespace": 6, "gsrsearch": f"{q} filetype:bitmap",
        "gsrlimit": 12, "prop": "imageinfo", "iiprop": "url|extmetadata|mime|size", "iiurlwidth": 1920, "format": "json",
    })
    pages = (_get(url).get("query") or {}).get("pages", {})
    for p in sorted(pages.values(), key=lambda x: x.get("index", 99)):
        info = (p.get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata", {})
        licence = (meta.get("LicenseShortName") or {}).get("value", "")
        if not LICENCES_OK.match(licence) or info.get("mime") not in ("image/jpeg", "image/png"):
            continue
        if info.get("width", 0) < 800:
            continue
        auteur = html.unescape(re.sub(r"<[^>]+>", "", (meta.get("Artist") or {}).get("value", "inconnu"))).strip()
        return {"url": info.get("thumburl") or info["url"], "ext": "png" if info["mime"] == "image/png" else "jpg",
                "source": "Wikimedia Commons", "auteur": auteur, "licence": licence, "page": info.get("descriptionurl", "")}
    return None


def pexels(q, cle, video, langue):
    if not cle or not q:
        return None
    base = "https://api.pexels.com/videos/search?" if video else "https://api.pexels.com/v1/search?"
    params = {"query": q, "orientation": "landscape", "per_page": 8}
    if langue == "fr":
        params["locale"] = "fr-FR"
    r = _get(base + urllib.parse.urlencode(params), headers={"Authorization": cle})
    if video:
        for v in r.get("videos", []):
            fichiers = [f for f in v.get("video_files", []) if f.get("file_type") == "video/mp4" and (f.get("width") or 0) >= 1280]
            if not fichiers:
                continue
            f = min(fichiers, key=lambda f: abs((f.get("width") or 0) - 1920))
            return {"url": f["link"], "ext": "mp4", "source": "Pexels", "auteur": v.get("user", {}).get("name", ""),
                    "licence": "Licence Pexels (usage libre)", "page": v.get("url", "")}
    else:
        for p in r.get("photos", []):
            return {"url": p["src"].get("large2x") or p["src"]["original"], "ext": "jpg", "source": "Pexels",
                    "auteur": p.get("photographer", ""), "licence": "Licence Pexels (usage libre)", "page": p.get("url", "")}
    return None


def pixabay(q, cle, video, langue):
    if not cle or not q:
        return None
    base = "https://pixabay.com/api/videos/?" if video else "https://pixabay.com/api/?"
    params = {"key": cle, "q": q[:100], "lang": langue or "en", "per_page": 8, "safesearch": "true"}
    if not video:
        params.update({"image_type": "photo", "orientation": "horizontal", "min_width": 1600})
    r = _get(base + urllib.parse.urlencode(params))
    for h in r.get("hits", []):
        if video:
            v = h.get("videos", {})
            f = v.get("large") if (v.get("large") or {}).get("url") else v.get("medium")
            if not f or not f.get("url"):
                continue
            return {"url": f["url"], "ext": "mp4", "source": "Pixabay", "auteur": h.get("user", ""),
                    "licence": "Licence Pixabay (usage libre)", "page": h.get("pageURL", "")}
        return {"url": h.get("largeImageURL"), "ext": "jpg", "source": "Pixabay", "auteur": h.get("user", ""),
                "licence": "Licence Pixabay (usage libre)", "page": h.get("pageURL", "")}
    return None


# ---------------------------------------------------------------- principal
def chercher_tout(plan, dossier, racine, journal=print):
    env = lire_env(racine)
    cle_pexels, cle_pixabay = env.get("PEXELS_API_KEY"), env.get("PIXABAY_API_KEY")
    assets_dir = os.path.join(dossier, "assets")
    auto_dir = os.path.join(assets_dir, "auto")
    os.makedirs(auto_dir, exist_ok=True)
    credits_path = os.path.join(auto_dir, "credits.json")
    credits = json.load(open(credits_path, encoding="utf-8")) if os.path.exists(credits_path) else {}

    vus, a_chercher = set(), []
    for e in plan["fond"]:
        a = e.get("asset")
        if a and a["id"] not in vus:
            vus.add(a["id"])
            if not fichier_existant(assets_dir, a["id"]):
                a_chercher.append((a, e["composant"]))

    manque_cles = []
    if not cle_pexels:
        manque_cles.append("PEXELS_API_KEY (gratuite : https://www.pexels.com/api/)")
    if not cle_pixabay:
        manque_cles.append("PIXABAY_API_KEY (gratuite : https://pixabay.com/api/docs/)")

    trouves, erreurs_reseau = 0, 0
    for a, composant in a_chercher:
        if a["genre"] == "ia":
            continue  # pas de génération d'image IA automatique : shotlist
        fr, en = requetes(a)
        portrait = composant == "FichePersonnage"
        video = a["genre"] == "video"
        essais = []
        if portrait or a["id"].startswith("P") or "wikimedia" in a.get("ou", "").lower():
            essais.append(lambda: wikimedia(en or fr))
        if not portrait:
            essais += [lambda: pexels(en, cle_pexels, video, "en"), lambda: pexels(fr, cle_pexels, video, "fr"),
                       lambda: pixabay(en, cle_pixabay, video, "en"), lambda: pixabay(fr, cle_pixabay, video, "fr")]
            if video:  # pas de vidéo ? une photo en mouvement fera l'affaire
                essais += [lambda: pexels(en or fr, cle_pexels, False, "en" if en else "fr")]
        res = None
        for essai in essais:
            try:
                res = essai()
            except Exception as err:  # réseau, quota, clé invalide…
                erreurs_reseau += 1
                if erreurs_reseau <= 3:
                    journal(f"   ⚠️  recherche impossible ({type(err).__name__}: {str(err)[:80]})")
                res = None
            if res and res.get("url"):
                break
        if not res:
            continue
        try:
            data = _get(res["url"], binaire=True, timeout=90)
        except Exception as err:
            journal(f"   ⚠️  téléchargement raté pour {a['id']} ({type(err).__name__})")
            continue
        chemin = os.path.join(auto_dir, f"{a['id']}.{res['ext']}")
        with open(chemin, "wb") as f:
            f.write(data)
        credits[a["id"]] = {k: res[k] for k in ("source", "auteur", "licence", "page")}
        trouves += 1
        journal(f"   ✓ {a['id']} ← {res['source']} ({res['licence']})")

    with open(credits_path, "w", encoding="utf-8") as f:
        json.dump(credits, f, ensure_ascii=False, indent=1)
    return {"trouves": trouves, "cherches": len(a_chercher), "manqueCles": manque_cles, "erreursReseau": erreurs_reseau}
