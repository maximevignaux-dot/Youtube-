#!/usr/bin/env python3
"""Fabrique le site boutique (dossier site/public/) à partir de catalogue.json et boutique.json.

  python3 build_site.py            aperçu : t-shirts visibles + brouillons (marqués « brouillon »)
  python3 build_site.py --prod     mise en ligne : seulement les t-shirts visibles, refuse si une info légale manque
  python3 build_site.py --demo     démo avec tous les designs déjà fabriqués (aperçus maison, rien n'est achetable)

Un t-shirt ajouté à catalogue.json = une page /t-shirt/<id>/ créée automatiquement.
"""
import html, json, os, re, shutil, sys
from PIL import Image

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "site")
OUT = os.path.join(SITE, "public")
E = html.escape

UE = ["FR", "BE", "LU", "DE", "AT", "NL", "IT", "ES", "PT", "IE", "DK", "SE", "FI", "PL", "CZ", "SK", "SI",
      "HR", "HU", "RO", "BG", "GR", "CY", "MT", "EE", "LV", "LT"]


def prix(p):
    return f"{p:.2f}".replace(".", ",") + " €"


# ------------------------------------------------------------------ données
def charger(mode):
    b = json.load(open(os.path.join(ROOT, "boutique.json"), encoding="utf-8"))
    cfg_p = os.path.join(ROOT, "config_printful.json")
    cfg = json.load(open(cfg_p, encoding="utf-8")) if os.path.exists(cfg_p) else {}
    if mode == "demo":
        cat = catalogue_demo()
    else:
        p = os.path.join(ROOT, "catalogue.json")
        cat = json.load(open(p, encoding="utf-8")) if os.path.exists(p) else []
        if mode == "prod":
            cat = [c for c in cat if c.get("visible")]
    return b, cfg, cat


NICHES_MOTS = [("Régions", ["corse"]), ("Pétanque", ["petanque"]), ("Apéro", ["apero", "saucisson", "pastis", "vin", "biere", "whisky"]),
               ("Vacances", ["camping", "caravane"]), ("Femmes", ["caractere", "infirmiere", "coiffeuse"]),
               ("Daron", ["retraite", "papy", "daron", "rien-faire", "jardin"]),
               ("Métiers", ["mecano", "plombier", "electricien", "macon", "plaquiste", "devis", "chantier", "couvreur",
                            "routier", "agriculteur", "beau-frere"])]


def niche_de(i):
    for n, mots in NICHES_MOTS:
        if any(m in i for m in mots):
            return n
    return "Daron"


def catalogue_demo():
    """Tous les designs déjà fabriqués, avec l'aperçu maison comme photo."""
    designs = json.load(open(os.path.join(ROOT, "designs.json"), encoding="utf-8"))
    cat = []
    for d in designs:
        dos = os.path.join(ROOT, "sortie", d["id"])
        styles = d.get("styles") or []
        photos = [f"sortie/{d['id']}/apercu_{s}.jpg" for s in styles if os.path.exists(os.path.join(dos, f"apercu_{s}.jpg"))]
        if not photos:
            photos = sorted(f"sortie/{d['id']}/{f}" for f in os.listdir(dos) if f.startswith("apercu_"))[:1] if os.path.isdir(dos) else []
        if not photos:
            continue
        titre, desc = d["id"].replace("-", " ").capitalize(), ""
        fp = os.path.join(dos, "fiche-produit.md")
        if os.path.exists(fp):
            t = open(fp, encoding="utf-8").read()
            titre = t.splitlines()[0].lstrip("# ").strip()
            m = re.search(r"## Description\n(.*?)\n\n(.*?)\n\n", t, re.S)
            if m:
                desc = m.group(1).strip() + "\n\n" + m.group(2).strip()
        cat.append({"id": d["id"], "titre": titre, "description": desc, "niche": niche_de(d["id"]),
                    "couleur": d.get("tshirt", "noir"), "prix": 24.90, "photos": photos, "visible": True, "demo": True,
                    "tailles": [{"taille": t, "sync_variant_id": None} for t in ["S", "M", "L", "XL", "2XL", "3XL"]]})
    return cat


def manquants(b):
    s = b["societe"]
    champs = {"nom de la boutique": b["nom"], "raison sociale": s["raison_sociale"], "adresse": s["adresse"],
              "SIREN": s["siren"], "ville du RCS": s["rcs_ville"], "capital": s["capital"], "email": s["email"],
              "directeur de publication": s["directeur_publication"], "médiateur de la consommation": s["mediateur_nom"]}
    return [k for k, v in champs.items() if not str(v).strip()]


def info(v, quoi):
    return E(str(v)) if str(v).strip() else f'<b class="manque">[À COMPLÉTER : {E(quoi)}]</b>'


# ------------------------------------------------------------------ images
def images(c):
    """Photos → WebP 900 px et 450 px dans public/img/<id>/ ; renvoie les chemins publics."""
    dest = os.path.join(OUT, "img", c["id"])
    os.makedirs(dest, exist_ok=True)
    out = []
    for k, src in enumerate(c["photos"]):
        im = Image.open(os.path.join(ROOT, src)).convert("RGB")
        for w in (900, 450):
            r = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
            r.save(os.path.join(dest, f"{k}-{w}.webp"), quality=82, method=6)
        if k == 0:  # image de partage Facebook (JPEG, plus compatible)
            im.resize((900, int(im.height * 900 / im.width)), Image.LANCZOS).save(os.path.join(dest, "partage.jpg"), quality=85)
        out.append((f"/img/{c['id']}/{k}-900.webp", f"/img/{c['id']}/{k}-450.webp", im.width / im.height))
    return out


# ------------------------------------------------------------------ gabarit
CSS = """
@font-face{font-family:Anton;src:url(/polices/anton.woff2) format("woff2");font-display:swap}
:root{--fond:#F7F2E8;--encre:#1F1B16;--doux:#6B6157;--carte:#FFFFFF;--brique:#B8452B;--moutarde:#E2A72E;--ligne:#E3DACB}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--fond);color:var(--encre);font:16px/1.55 system-ui,-apple-system,"Segoe UI",Roboto,sans-serif}
a{color:inherit}img{max-width:100%;height:auto;display:block}
.cont{max-width:1100px;margin:0 auto;padding:0 16px}
header.haut{background:var(--encre);color:var(--fond);position:sticky;top:0;z-index:5}
header.haut .cont{display:flex;align-items:center;justify-content:space-between;height:58px}
.logo{font-family:Anton,Impact,sans-serif;font-size:24px;letter-spacing:.5px;text-decoration:none;text-transform:uppercase}
.logo span{color:var(--moutarde)}
.panier-lien{text-decoration:none;font-weight:700;display:flex;gap:6px;align-items:center}
.pastille{background:var(--moutarde);color:var(--encre);border-radius:99px;padding:0 8px;font-size:14px;min-width:24px;text-align:center}
h1,h2,.titre{font-family:Anton,Impact,sans-serif;font-weight:400;line-height:1.08;letter-spacing:.3px}
.accroche{padding:28px 0 8px}.accroche h1{font-size:clamp(30px,8vw,54px);margin:0 0 8px;text-transform:uppercase}
.accroche p{margin:0;color:var(--doux);font-size:18px}
.filtres{display:flex;gap:8px;overflow-x:auto;padding:16px 0;scrollbar-width:none}
.filtres button{flex:none;border:2px solid var(--encre);background:transparent;border-radius:99px;padding:8px 16px;font:600 15px system-ui;color:var(--encre);cursor:pointer}
.filtres button.on{background:var(--encre);color:var(--fond)}
.grille{display:grid;grid-template-columns:repeat(2,1fr);gap:14px;padding-bottom:40px}
@media(min-width:760px){.grille{grid-template-columns:repeat(3,1fr);gap:22px}}
@media(min-width:1000px){.grille{grid-template-columns:repeat(4,1fr)}}
.carte{background:var(--carte);border-radius:14px;overflow:hidden;text-decoration:none;display:flex;flex-direction:column;box-shadow:0 1px 0 var(--ligne)}
.carte img{aspect-ratio:900/1100;object-fit:cover;background:#E9E6E1}
.carte .t{padding:10px 12px 2px;font-weight:650;font-size:15px;line-height:1.3}
.carte .p{padding:0 12px 12px;color:var(--brique);font-weight:800}
.brouillon{background:var(--moutarde);color:var(--encre);font:700 12px system-ui;padding:2px 8px;border-radius:6px;margin:8px 12px 0;align-self:flex-start}
.produit{display:grid;gap:22px;padding:18px 0 40px}
@media(min-width:860px){.produit{grid-template-columns:1.1fr 1fr;align-items:start}}
.galerie .principale{border-radius:16px;overflow:hidden;background:#E9E6E1}
.vignettes{display:flex;gap:8px;margin-top:8px}.vignettes img{width:70px;border-radius:8px;cursor:pointer;border:2px solid transparent}
.vignettes img.on{border-color:var(--encre)}
.produit h1{font-size:clamp(26px,6.5vw,40px);margin:0 0 6px}
.prix{font-size:28px;font-weight:800;color:var(--brique);margin:4px 0}
.cadeau{display:inline-block;background:#FFF1C9;border:1px dashed var(--moutarde);padding:4px 10px;border-radius:8px;font-weight:650;font-size:14px}
.tailles{display:flex;flex-wrap:wrap;gap:8px;margin:14px 0 6px}
.tailles label{position:relative}
.tailles input{position:absolute;opacity:0}
.tailles span{display:block;min-width:56px;text-align:center;padding:11px 10px;border:2px solid var(--ligne);border-radius:10px;background:var(--carte);font-weight:700;cursor:pointer}
.tailles input:checked+span{border-color:var(--encre);background:var(--encre);color:var(--fond)}
.tailles input:focus-visible+span{outline:3px solid var(--moutarde)}
.bouton{display:block;width:100%;border:0;border-radius:14px;padding:17px;font:400 22px Anton,Impact,sans-serif;letter-spacing:.6px;text-transform:uppercase;background:var(--brique);color:#fff;cursor:pointer;text-align:center;text-decoration:none}
.bouton.second{background:transparent;color:var(--encre);border:2px solid var(--encre);font-size:18px;padding:13px;margin-top:10px}
.bouton:disabled{opacity:.5}
.alerte{color:var(--brique);font-weight:650;min-height:1.4em;margin:6px 0}
details{background:var(--carte);border-radius:12px;padding:12px 14px;margin-top:12px}
summary{font-weight:700;cursor:pointer}
table{border-collapse:collapse;width:100%;font-size:14px;margin-top:8px}td,th{border-bottom:1px solid var(--ligne);padding:6px;text-align:center}
.rassure{display:grid;gap:6px;margin:16px 0;padding:0;list-style:none;color:var(--doux);font-size:15px}
.texte{max-width:760px;padding:20px 0 50px}.texte h1{font-size:34px}.texte h2{font-size:22px;margin-top:28px}
.manque{color:#C8102E}
.ligne-panier{display:grid;grid-template-columns:80px 1fr auto;gap:12px;align-items:center;background:var(--carte);border-radius:12px;padding:10px;margin-bottom:10px}
.ligne-panier img{border-radius:8px}
.qte{display:flex;align-items:center;gap:8px;margin-top:4px}.qte button{width:34px;height:34px;border-radius:8px;border:2px solid var(--ligne);background:var(--fond);font-size:18px;cursor:pointer}
.total{display:flex;justify-content:space-between;font-size:20px;font-weight:800;margin:16px 0}
footer{background:var(--encre);color:#CFC6B8;padding:26px 0 40px;font-size:14px}
footer nav{display:flex;flex-wrap:wrap;gap:8px 18px;margin-bottom:10px}footer a{text-decoration:none}
.bandeau-demo{background:var(--moutarde);color:var(--encre);text-align:center;font-weight:700;padding:6px 12px;font-size:14px}
"""

JS_COMPTEUR = """<script>try{var n=JSON.parse(localStorage.getItem('panier')||'[]').reduce(function(a,b){return a+b.qte},0);if(n){var e=document.getElementById('nb');e.textContent=n;e.hidden=false}}catch(e){}</script>"""


def page(b, titre, corps, desc="", image="", chemin="/", mode="apercu", indexer=True):
    nom = b["nom"] or "Ma boutique"
    base = f"https://{b['domaine']}" if b["domaine"] else ""
    meta_img = f'<meta property="og:image" content="{E(base + image)}">' if image else ""
    meta_img += f'<link rel="canonical" href="{E(base + chemin)}">' if base else ""
    bandeau = {"demo": '<div class="bandeau-demo">DÉMO — photos provisoires, rien n\'est encore en vente</div>',
               "apercu": '<div class="bandeau-demo">APERÇU — les t-shirts marqués « brouillon » ne sont pas encore en vente</div>',
               "prod": ""}[mode]
    robots = "" if indexer and mode == "prod" else '<meta name="robots" content="noindex">'
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{E(titre)}</title><meta name="description" content="{E(desc[:160])}">{robots}
<meta property="og:title" content="{E(titre)}"><meta property="og:description" content="{E(desc[:200])}">
<meta property="og:type" content="website">{meta_img}
<link rel="preload" href="/polices/anton.woff2" as="font" type="font/woff2" crossorigin>
<link rel="icon" href="/favicon.svg"><style>{CSS}</style></head><body>
{bandeau}<header class="haut"><div class="cont"><a class="logo" href="/">{E(nom)}<span>.</span></a>
<a class="panier-lien" href="/panier/">Panier <span class="pastille" id="nb" hidden>0</span></a></div></header>
<main class="cont">{corps}</main>
<footer><div class="cont"><nav><a href="/">Tous les t-shirts</a><a href="/cgv/">CGV</a><a href="/mentions-legales/">Mentions légales</a>
<a href="/confidentialite/">Confidentialité</a><a href="/contact/">Contact</a></nav>
Paiement sécurisé par Stripe · Impression à la demande en Europe · Retours sous 14 jours<br>© {E(nom)}</div></footer>
{JS_COMPTEUR}</body></html>"""


def ecrire(chemin, contenu):
    p = os.path.join(OUT, chemin.strip("/"), "index.html") if not chemin.endswith(".html") else os.path.join(OUT, chemin.strip("/"))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, "w", encoding="utf-8").write(contenu)


# ------------------------------------------------------------------ pages
def page_accueil(b, cat, imgs, mode):
    niches = [n for n in b["niches"] if any(c["niche"] == n for c in cat)]
    boutons = '<button class="on" data-n="">Tous</button>' + "".join(f'<button data-n="{E(n)}">{E(n)}</button>' for n in niches)
    cartes = ""
    for c in cat:
        g, p, _ = imgs[c["id"]][0]
        badge = '<span class="brouillon">brouillon</span>' if not c.get("visible") else ""
        cartes += (f'<a class="carte" href="/t-shirt/{c["id"]}/" data-n="{E(c["niche"])}">{badge}'
                   f'<img src="{p}" srcset="{p} 450w, {g} 900w" sizes="(min-width:760px) 300px, 50vw" alt="{E(c["titre"])}" '
                   f'width="450" height="550" loading="lazy" decoding="async">'
                   f'<span class="t">{E(c["titre"].replace("T-shirt ", ""))}</span><span class="p">{prix(c["prix"])}</span></a>')
    corps = f"""<section class="accroche"><h1>{E(b['nom'] or 'Ma boutique')}</h1><p>{E(b['accroche'])}</p></section>
<div class="filtres" role="group" aria-label="Filtrer">{boutons}</div><div class="grille" id="grille">{cartes}</div>
<script>document.querySelectorAll('.filtres button').forEach(function(bt){{bt.onclick=function(){{
document.querySelectorAll('.filtres button').forEach(function(x){{x.classList.toggle('on',x===bt)}});
document.querySelectorAll('#grille .carte').forEach(function(c){{c.hidden=bt.dataset.n&&c.dataset.n!==bt.dataset.n}})}}}})</script>"""
    img0 = imgs[cat[0]["id"]][0][0] if cat else ""
    return page(b, f"{b['nom'] or 'Ma boutique'} — t-shirts humour", corps, b["accroche"], img0, "/", mode)


def guide_html(cfg):
    g = cfg.get("guide_tailles")
    if not g:
        return "<p>Coupe unisexe, plutôt droite. Dans le doute, prends ta taille habituelle.</p>"
    th = "".join(f"<th>{E(str(x))}</th>" for x in g["colonnes"])
    tr = "".join("<tr>" + "".join(f"<td>{E(str(x))}</td>" for x in l) + "</tr>" for l in g["lignes"])
    return f"<table><tr>{th}</tr>{tr}</table><p>{E(g.get('note', ''))}</p>"


def page_produit(b, cfg, c, im, mode):
    principale = f'<img id="grande" src="{im[0][0]}" alt="{E(c["titre"])}" width="900" height="{int(900 / im[0][2])}" fetchpriority="high">'
    vign = "".join(f'<img src="{p}" data-g="{g}" alt="" width="70" height="86"{" class=on" if k == 0 else ""}>'
                   for k, (g, p, _) in enumerate(im)) if len(im) > 1 else ""
    tailles = "".join(f'<label><input type="radio" name="taille" value="{E(t["taille"])}"><span>{E(t["taille"])}</span></label>'
                      for t in c["tailles"])
    paras = "".join(f"<p>{E(p)}</p>" for p in c.get("description", "").split("\n\n") if p.strip())
    liv = b["livraison"]
    liv_txt = "Livraison offerte" if liv["mode"] == "offerte" else f"Livraison {prix(liv['forfait'])}"
    achetable = c.get("visible") and not c.get("demo")
    corps = f"""<div class="produit"><div class="galerie"><div class="principale">{principale}</div><div class="vignettes">{vign}</div></div>
<div><h1>{E(c['titre'].replace('T-shirt ', ''))}</h1><div class="prix">{prix(c['prix'])}</div><span class="cadeau">🎁 Idée cadeau</span>
<form id="achat"><div class="tailles" role="radiogroup" aria-label="Taille">{tailles}</div>
<div class="alerte" id="msg" aria-live="polite"></div>
<button class="bouton" {'disabled' if not achetable else ''}>{'Je le veux' if achetable else 'Bientôt disponible'}</button>
<button class="bouton second" type="button" id="ajout" {'disabled' if not achetable else ''}>Ajouter et continuer</button></form>
<ul class="rassure"><li>✔ {liv_txt} · fabriqué en {E(liv['fabrication'])}</li><li>✔ Paiement sécurisé : carte, Apple Pay, Google Pay</li>
<li>✔ Retour possible pendant 14 jours</li></ul>
<details><summary>Guide des tailles</summary>{guide_html(cfg)}</details>
<details open><summary>Le t-shirt</summary>{paras}<p>Impression dans le dos, coton doux, coupe unisexe. Lavage à 30 °C sur l'envers.</p></details>
</div></div>
<script>(function(){{var id={json.dumps(c['id'])};
document.querySelectorAll('.vignettes img').forEach(function(v){{v.onclick=function(){{document.getElementById('grande').src=v.dataset.g;
document.querySelectorAll('.vignettes img').forEach(function(x){{x.classList.toggle('on',x===v)}})}}}});
function ajouter(){{var t=document.querySelector('input[name=taille]:checked');if(!t){{document.getElementById('msg').textContent='Choisis ta taille 👆';return false}}
var p=[];try{{p=JSON.parse(localStorage.getItem('panier')||'[]')}}catch(e){{}}
var l=p.find(function(x){{return x.id===id&&x.taille===t.value}});if(l)l.qte=Math.min(10,l.qte+1);else p.push({{id:id,taille:t.value,qte:1}});
localStorage.setItem('panier',JSON.stringify(p));return true}}
document.getElementById('achat').onsubmit=function(e){{e.preventDefault();if(ajouter())location.href='/panier/'}};
document.getElementById('ajout').onclick=function(){{if(ajouter())location.href='/'}};}})()</script>"""
    return page(b, c["titre"], corps, c.get("description", "").split("\n")[0], f"/img/{c['id']}/partage.jpg",
                f"/t-shirt/{c['id']}/", mode)


def page_panier(b, cat, imgs, mode):
    mini = {c["id"]: {"t": c["titre"].replace("T-shirt ", ""), "p": c["prix"], "i": imgs[c["id"]][0][1],
                      "ok": bool(c.get("visible") and not c.get("demo"))} for c in cat}
    liv = b["livraison"]
    port = 0 if liv["mode"] == "offerte" else liv["forfait"]
    corps = f"""<section class="texte"><h1>Ton panier</h1><div id="lignes"></div>
<div class="total"><span>Livraison</span><span>{'offerte' if not port else prix(port)}</span></div>
<div class="total"><span>Total</span><span id="total">—</span></div>
<div class="alerte" id="msg" aria-live="polite"></div>
<button class="bouton" id="payer">Payer en toute sécurité</button>
<p style="color:var(--doux);font-size:14px;margin-top:10px">Tu seras redirigé vers Stripe (carte, Apple Pay, Google Pay). Ton adresse de livraison est demandée à l'étape suivante.</p></section>
<script>(function(){{var C={json.dumps(mini, ensure_ascii=False)},PORT={port};
function lire(){{try{{return JSON.parse(localStorage.getItem('panier')||'[]').filter(function(x){{return C[x.id]}})}}catch(e){{return[]}}}}
function eur(v){{return v.toFixed(2).replace('.',',')+' €'}}
function rendre(){{var p=lire(),h='',t=0;p.forEach(function(x,k){{var c=C[x.id];t+=c.p*x.qte;
h+='<div class="ligne-panier"><img src="'+c.i+'" alt="" width="80" height="98"><div><b>'+c.t+'</b><br>Taille '+x.taille+
'<div class="qte"><button data-k="'+k+'" data-d="-1" aria-label="Retirer un">−</button><span>'+x.qte+'</span><button data-k="'+k+'" data-d="1" aria-label="Ajouter un">+</button></div></div><b>'+eur(c.p*x.qte)+'</b></div>'}});
document.getElementById('lignes').innerHTML=h||'<p>Ton panier est vide. <a href="/">Voir les t-shirts</a></p>';
document.getElementById('total').textContent=p.length?eur(t+PORT):'—';document.getElementById('payer').disabled=!p.length;
document.querySelectorAll('.qte button').forEach(function(bt){{bt.onclick=function(){{var p=lire(),x=p[+bt.dataset.k];x.qte+=+bt.dataset.d;
if(x.qte<1)p.splice(+bt.dataset.k,1);else x.qte=Math.min(10,x.qte);localStorage.setItem('panier',JSON.stringify(p));rendre()}}}})}}
rendre();document.getElementById('payer').onclick=function(){{var p=lire(),m=document.getElementById('msg');
if(p.some(function(x){{return!C[x.id].ok}})){{m.textContent="Un t-shirt de ton panier n'est pas encore en vente.";return}}
this.disabled=true;m.textContent='Connexion au paiement…';
fetch('/api/checkout',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{items:p}})}})
.then(function(r){{return r.json()}}).then(function(r){{if(r.url)location.href=r.url;else{{m.textContent=r.erreur||'Oups, réessaie dans un instant.';document.getElementById('payer').disabled=false}}}})
.catch(function(){{m.textContent='Oups, réessaie dans un instant.';document.getElementById('payer').disabled=false}})}}}})()</script>"""
    return page(b, "Ton panier", corps, "", "", "/panier/", mode, indexer=False)


def pages_simples(b, mode):
    nom = b["nom"] or "Ma boutique"
    merci = """<section class="texte"><h1>Merci pour ta commande ! 🎉</h1><p>C'est validé. Tu vas recevoir un email de confirmation de paiement.</p>
<p>Ton t-shirt part en fabrication : compte """ + E(b["livraison"]["fabrication"]) + """ pour l'impression, puis """ + E(b["livraison"]["transport"]) + """.
Tu recevras le numéro de suivi par email dès l'expédition.</p><p><a class="bouton" href="/">Voir les autres t-shirts</a></p></section>
<script>localStorage.removeItem('panier')</script>"""
    annule = """<section class="texte"><h1>Paiement annulé</h1><p>Aucun montant n'a été débité. Ton panier est toujours là.</p>
<p><a class="bouton" href="/panier/">Revenir au panier</a></p></section>"""
    introuvable = """<section class="texte"><h1>Page introuvable</h1><p>Ce t-shirt a peut-être changé d'adresse.</p><p><a class="bouton" href="/">Voir tous les t-shirts</a></p></section>"""
    ecrire("/merci/", page(b, "Merci !", merci, "", "", "/merci/", mode, False))
    ecrire("/annule/", page(b, "Paiement annulé", annule, "", "", "/annule/", mode, False))
    ecrire("404.html", page(b, "Page introuvable", introuvable, "", "", "/404", mode, False))
    for chemin, (titre, corps) in pages_legales(b).items():
        ecrire(chemin, page(b, f"{titre} — {nom}", f'<section class="texte"><h1>{E(titre)}</h1>{corps}</section>', "", "", chemin, mode))


def pages_legales(b):
    s, liv = b["societe"], b["livraison"]
    nom = info(b["nom"], "nom de la boutique")
    soc = f'{info(s["raison_sociale"], "raison sociale")}, {E(s["forme"])} au capital de {info(s["capital"], "capital")} €'
    ident = (f'{soc}, immatriculée au RCS de {info(s["rcs_ville"], "ville du RCS")} sous le numéro {info(s["siren"], "SIREN")}, '
             f'dont le siège est situé {info(s["adresse"], "adresse du siège")}.')
    tva = f'TVA intracommunautaire : {info(s["tva_intracom"], "numéro de TVA (ou mention de franchise)")}.'
    contact = f'Email : {info(s["email"], "email de contact")}' + (f' · Téléphone : {E(s["telephone"])}' if s["telephone"] else "")
    port = "offerte" if liv["mode"] == "offerte" else f"facturée {prix(liv['forfait'])} par commande"
    med = (f'{E(s["mediateur_nom"])}' + (f' ({E(s["mediateur_site"])})' if s["mediateur_site"] else "")) if s["mediateur_nom"] \
        else info("", "nom et site du médiateur de la consommation")
    return {
        "/mentions-legales/": ("Mentions légales", f"""
<h2>Éditeur du site</h2><p>Le site {nom} est édité par {ident}</p><p>{tva}</p><p>{contact}</p>
<p>Directeur de la publication : {info(s["directeur_publication"], "nom du directeur de publication")}.</p>
<h2>Hébergement</h2><p>{E(b["hebergeur"])}</p>
<h2>Propriété intellectuelle</h2><p>Les textes, slogans, illustrations et visuels du site sont la propriété de {info(s["raison_sociale"], "raison sociale")}. Toute reproduction sans autorisation est interdite.</p>"""),
        "/cgv/": ("Conditions générales de vente", f"""
<p>Les présentes conditions s'appliquent aux ventes conclues sur le site {nom} entre {ident} (le « Vendeur ») et tout consommateur (le « Client »).</p>
<h2>1. Produits</h2><p>Les t-shirts sont imprimés à la demande, à réception de la commande, par notre partenaire de fabrication en Europe. Les photos sont des représentations aussi fidèles que possible ; de légères différences de teinte peuvent exister.</p>
<h2>2. Prix</h2><p>Les prix sont indiqués en euros, toutes taxes comprises. {E(s["mention_tva"])} La livraison est {port}, montant affiché avant le paiement.</p>
<h2>3. Commande et paiement</h2><p>La commande est validée après paiement par carte bancaire, Apple Pay ou Google Pay via la plateforme sécurisée Stripe. Le Vendeur n'a jamais accès aux numéros de carte. Un email de confirmation est envoyé au Client.</p>
<h2>4. Fabrication et livraison</h2><p>Fabrication : {E(liv["fabrication"])}. Transport : {E(liv["transport"])}. Livraison en France et dans les pays de l'Union européenne, à l'adresse indiquée par le Client. En cas de retard important, le Client peut contacter le Vendeur à l'adresse email ci-dessous.</p>
<h2>5. Droit de rétractation</h2><p>Conformément à l'article L221-18 du Code de la consommation, le Client dispose de 14 jours à compter de la réception de sa commande pour se rétracter, sans avoir à se justifier. Il informe le Vendeur par email ({info(s["email"], "email")}) de sa décision, puis renvoie le ou les articles non portés, non lavés et dans leur état d'origine, dans les 14 jours suivant cette information. Les frais de retour sont à la charge du Client. Le Vendeur rembourse la totalité des sommes versées, frais de livraison initiaux compris (sur la base du tarif standard), dans les 14 jours suivant la réception de la décision, ce remboursement pouvant être différé jusqu'à la réception des articles. Le remboursement se fait sur le moyen de paiement utilisé.</p>
<h2>6. Article défectueux</h2><p>En cas d'erreur d'impression, de taille différente de celle commandée ou d'article abîmé à la livraison, le Client envoie une photo par email dans les 30 jours : le Vendeur remplace l'article ou le rembourse, sans frais pour le Client.</p>
<h2>7. Garanties légales</h2><p>Le Client bénéficie de la garantie légale de conformité (articles L217-3 et suivants du Code de la consommation) pendant deux ans à compter de la livraison, et de la garantie des vices cachés (articles 1641 et suivants du Code civil).</p>
<h2>8. Données personnelles</h2><p>Voir notre <a href="/confidentialite/">politique de confidentialité</a>.</p>
<h2>9. Litiges et médiation</h2><p>En cas de difficulté, le Client contacte d'abord le Vendeur ({info(s["email"], "email")}). À défaut d'accord, il peut recourir gratuitement au médiateur de la consommation : {med}. Les présentes conditions sont soumises au droit français.</p>"""),
        "/confidentialite/": ("Politique de confidentialité", f"""
<h2>Responsable du traitement</h2><p>{ident} {contact}.</p>
<h2>Données collectées</h2><p>Uniquement ce qui est nécessaire pour traiter ta commande : nom, adresse de livraison, email, téléphone (facultatif) et contenu de la commande. Les données de carte bancaire sont traitées exclusivement par Stripe.</p>
<h2>À qui elles sont transmises</h2><p>Stripe (paiement), Printful (fabrication et expédition, qui transmet l'adresse au transporteur), Cloudflare (hébergement du site). Certains de ces prestataires peuvent traiter des données hors de l'Union européenne, dans le cadre des garanties prévues par le RGPD (clauses contractuelles types de la Commission européenne).</p>
<h2>Durée de conservation</h2><p>Les données de commande sont conservées 10 ans (obligation comptable), puis supprimées.</p>
<h2>Cookies</h2><p>Le site n'utilise pas de cookie publicitaire ni de mesure d'audience. Ton panier est simplement enregistré dans ton navigateur (stockage local), le temps de ta visite.</p>
<h2>Tes droits</h2><p>Tu peux demander l'accès, la rectification, l'effacement ou la limitation de tes données, et t'opposer à leur traitement, en écrivant à {info(s["email"], "email")}. Tu peux aussi saisir la CNIL (cnil.fr).</p>"""),
        "/contact/": ("Contact", f"""<p>Une question sur une commande, une taille, un retour ? Écris-nous, on répond vite.</p><p>{contact}</p>
<p>Pense à indiquer ton numéro de commande (dans l'email de confirmation) si tu en as un.</p>"""),
    }


# ------------------------------------------------------------------ côté serveur
def lib_serveur(b, cat):
    """site/lib/catalogue.js : prix et variantes lus par les fonctions de paiement (jamais ceux du navigateur)."""
    data = {c["id"]: {"titre": c["titre"], "prix": c["prix"], "visible": bool(c.get("visible")) and not c.get("demo"),
                      "photo": f"/img/{c['id']}/partage.jpg",
                      "tailles": {t["taille"]: t["sync_variant_id"] for t in c["tailles"]}} for c in cat}
    liv = {"mode": b["livraison"]["mode"], "forfait": b["livraison"]["forfait"]}
    open(os.path.join(SITE, "lib", "catalogue.js"), "w", encoding="utf-8").write(
        "// Fichier généré par build_site.py — ne pas modifier à la main.\n"
        f"export const CATALOGUE = {json.dumps(data, ensure_ascii=False, indent=1)};\n"
        f"export const LIVRAISON = {json.dumps(liv)};\n"
        f"export const PAYS = {json.dumps(UE)};\n")


def main():
    mode = "prod" if "--prod" in sys.argv else "demo" if "--demo" in sys.argv else "apercu"
    b, cfg, cat = charger(mode)
    manque = manquants(b)
    if mode == "prod" and manque:
        sys.exit("Mise en ligne bloquée, il manque dans boutique.json : " + ", ".join(manque))
    if os.path.exists(OUT):
        shutil.rmtree(OUT)
    shutil.copytree(os.path.join(SITE, "static"), OUT)
    open(os.path.join(OUT, "favicon.svg"), "w").write(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#1F1B16"/>'
        '<path d="M20 14l-12 8 5 9 5-3v24h28V28l5 3 5-9-12-8c-2 4-6 6-12 6s-10-2-12-6z" fill="#E2A72E"/></svg>')
    open(os.path.join(OUT, "_headers"), "w").write(
        "/img/*\n  Cache-Control: public, max-age=31536000, immutable\n/polices/*\n  Cache-Control: public, max-age=31536000, immutable\n"
        "/f/*\n  X-Robots-Tag: noindex\n/*\n  X-Content-Type-Options: nosniff\n  Referrer-Policy: strict-origin-when-cross-origin\n")
    imgs = {c["id"]: images(c) for c in cat}
    ecrire("/", page_accueil(b, cat, imgs, mode))
    for c in cat:
        ecrire(f"/t-shirt/{c['id']}/", page_produit(b, cfg, c, imgs[c["id"]], mode))
    ecrire("/panier/", page_panier(b, cat, imgs, mode))
    pages_simples(b, mode)
    lib_serveur(b, cat)
    print(f"Site {mode} : {len(cat)} t-shirts → site/public/")
    if manque:
        print("À compléter dans boutique.json avant la mise en ligne : " + ", ".join(manque))


if __name__ == "__main__":
    main()
